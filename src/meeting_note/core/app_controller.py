from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import subprocess

from meeting_note.core.asr_provider_factory import ASRProviderFactory
from meeting_note.core.asr_service import ASRService
from meeting_note.core.contracts import Language, TranscriptDocument, TranslationDocument, TranslationMode
from meeting_note.core.export_workflow import ExportWorkflow
from meeting_note.core.llm_provider_factory import LLMProviderFactory
from meeting_note.core.media import validate_media_file
from meeting_note.core.model_preparation import LocalModelPreparationService
from meeting_note.core.model_scanner import ModelScanner
from meeting_note.core.model_settings import ModelSelection, ModelSettingsService
from meeting_note.core.preprocessing_service import PreprocessingService
from meeting_note.core.summary_service import SummaryService
from meeting_note.core.summary_workflow import SummaryWorkflow
from meeting_note.core.task_runner import TaskRunner
from meeting_note.core.transcription_service import TranscriptionService
from meeting_note.core.translation_service import TranslationService
from meeting_note.core.translation_workflow import TranslationWorkflow
from meeting_note.data.document_store import SummaryStore, TranscriptStore, TranslationStore
from meeting_note.data.models import ModelType, Record, RecordStatus, TaskRecord, TaskType
from meeting_note.data.repositories import ModelRepository, RecordRepository, TaskRepository
from meeting_note.infra.paths import AppPaths
from meeting_note.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class AppController:
    def __init__(
        self,
        window: MainWindow,
        record_repository: RecordRepository,
        preprocessing_service: PreprocessingService | None = None,
        model_repository: ModelRepository | None = None,
        model_scanner: ModelScanner | None = None,
        model_settings_service: ModelSettingsService | None = None,
        asr_provider_factory: ASRProviderFactory | None = None,
        llm_provider_factory: LLMProviderFactory | None = None,
        export_workflow: ExportWorkflow | None = None,
        task_repository: TaskRepository | None = None,
        task_runner: TaskRunner | None = None,
        transcript_store: TranscriptStore | None = None,
        translation_store: TranslationStore | None = None,
        summary_store: SummaryStore | None = None,
        paths: AppPaths | None = None,
        run_preprocessing_in_background: bool = True,
        run_model_tasks_in_background: bool = True,
    ):
        self._window = window
        self._record_repository = record_repository
        self._preprocessing_service = preprocessing_service
        self._model_repository = model_repository
        self._model_scanner = model_scanner
        self._model_settings_service = model_settings_service
        self._asr_provider_factory = asr_provider_factory
        self._llm_provider_factory = llm_provider_factory
        self._export_workflow = export_workflow
        self._task_repository = task_repository
        self._task_runner = task_runner
        self._transcript_store = transcript_store
        self._translation_store = translation_store
        self._summary_store = summary_store
        self._paths = paths
        self._run_preprocessing_in_background = run_preprocessing_in_background
        self._run_model_tasks_in_background = run_model_tasks_in_background
        self._current_record: Record | None = None
        self._active_record_id: str | None = None
        self._window.media_selected.connect(self.handle_media_selected)
        self._window.history_refresh_requested.connect(self.refresh_history)
        self._window.history_clear_requested.connect(self.clear_history)
        self._window.tasks_refresh_requested.connect(self.refresh_tasks)
        self._window.tasks_clear_requested.connect(self.clear_finished_tasks)
        self._window.record_open_requested.connect(self.display_transcript_for_record)
        self._window.record_transcribe_requested.connect(self.transcribe_record)
        self._window.record_translate_to_chinese_requested.connect(self.translate_record_to_chinese)
        self._window.record_translate_to_english_requested.connect(self.translate_record_to_english)
        self._window.export_transcript_requested.connect(self.export_current_transcript)
        self._window.export_translation_requested.connect(self.export_current_translation)
        self._window.export_bilingual_requested.connect(self.export_current_bilingual)
        self._window.models_refresh_requested.connect(self.refresh_models)
        self._window.models_prepare_requested.connect(self.prepare_models)
        self._window.models_open_folder_requested.connect(self.open_models_folder)
        self._window.settings_save_requested.connect(self.save_model_selection)
        self._window.settings_reset_requested.connect(self.load_model_selection)
        if self._task_runner:
            self._task_runner.task_succeeded.connect(self._on_background_task_succeeded)
            self._task_runner.task_failed.connect(self._on_background_task_failed)
            self._recover_stale_background_tasks()
        self.refresh_history()
        self.refresh_tasks()
        self.refresh_models()
        self.load_model_selection()

    @property
    def current_record(self) -> Record | None:
        return self._current_record

    def handle_media_selected(self, file_path: str) -> Record:
        media_file = validate_media_file(Path(file_path))
        record = self._record_repository.create_record(
            title=media_file.path.stem,
            original_file_path=media_file.path,
        )
        self._current_record = record
        self._active_record_id = record.id
        self._window.clear_results()
        logger.info("Created record %s for %s", record.id, media_file.path)
        self._window.show_status(self._t("status.record_created", title=record.title))

        if self._preprocessing_service:
            if self._run_preprocessing_in_background and self._task_repository and self._task_runner:
                self._start_background_preprocessing(record)
            else:
                self._window.show_status(self._t("status.preprocessing_audio"))
                processed_audio_path = self._preprocessing_service.preprocess_record(record)
                self._window.show_status(self._t("status.audio_ready", path=processed_audio_path))

        self.refresh_history()
        self._window.history_page.select_record(record.id)
        self.refresh_tasks()
        return record

    def refresh_history(self) -> None:
        self._window.set_history_records(self._record_repository.list_records())
        if self._active_record_id:
            self._window.history_page.select_record(self._active_record_id)

    def _recover_stale_background_tasks(self) -> None:
        if not self._task_repository:
            return
        stale_tasks = self._task_repository.list_active_tasks()
        if not stale_tasks:
            return
        for task in stale_tasks:
            self._task_repository.mark_failed(task.id, "Recovered stale task from previous session.")
            if task.record_id and task.task_type in {TaskType.PREPROCESS_AUDIO, TaskType.TRANSCRIBE}:
                self._record_repository.update_status(task.record_id, RecordStatus.FAILED)
        logger.warning("Recovered %d stale background task(s) from previous session.", len(stale_tasks))

    def clear_history(self) -> None:
        active_task_count = len(self._task_repository.list_active_tasks()) if self._task_repository else 0
        if active_task_count > 0:
            self._window.show_status(self._t("status.history_clear_blocked_running_tasks", count=active_task_count))
            return

        record_ids = self._record_repository.clear_all_records()
        if not record_ids:
            self._window.show_status(self._t("status.history_clear_none"))
            return

        if self._task_repository:
            self._task_repository.delete_tasks_for_records(record_ids)

        if self._paths:
            for record_id in record_ids:
                shutil.rmtree(self._paths.record_dir(record_id), ignore_errors=True)

        self._current_record = None
        self._active_record_id = None
        self._window.clear_results()
        self.refresh_history()
        self.refresh_tasks()
        self._window.show_status(self._t("status.history_cleared", count=len(record_ids)))

    def refresh_tasks(self) -> None:
        if not self._task_repository:
            self._window.set_tasks([])
            return
        self._window.set_tasks(self._task_repository.list_tasks())

    def clear_finished_tasks(self) -> None:
        if not self._task_repository:
            self._window.show_status(self._t("status.tasks_service_unavailable"))
            return
        cleared = self._task_repository.clear_finished_tasks()
        self.refresh_tasks()
        if cleared <= 0:
            self._window.show_status(self._t("status.tasks_clear_none"))
            return
        self._window.show_status(self._t("status.tasks_cleared", count=cleared))

    def refresh_models(self) -> None:
        if not self._model_repository or not self._model_scanner:
            self._window.set_models([])
            return

        detected_models = self._model_scanner.scan_all_models()
        self._model_repository.replace_all(detected_models)
        self._window.set_models(detected_models)
        self._window.set_model_availability(self._model_preparation_service().inspect())

    def prepare_models(self) -> bool:
        project_root = self._project_root()
        if project_root is None:
            self._window.show_status(self._t("status.model_directory_not_configured"))
            return False

        script_path = project_root / "prepare_models.bat"
        if not script_path.exists():
            self._window.show_status(self._t("status.prepare_script_missing"))
            return False

        try:
            creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            subprocess.Popen(
                ["cmd.exe", "/k", str(script_path)],
                cwd=str(project_root),
                creationflags=creationflags,
            )
        except OSError as exc:
            self._window.show_status(self._t("status.prepare_start_failed", error=exc))
            return False

        self._window.show_status(self._t("status.prepare_started"))
        return True

    def open_models_folder(self) -> bool:
        project_root = self._project_root()
        if project_root is None or not self._model_scanner:
            self._window.show_status(self._t("status.model_directory_not_configured"))
            return False

        models_dir = self._model_scanner.models_dir
        models_dir.mkdir(parents=True, exist_ok=True)
        (models_dir / "asr").mkdir(parents=True, exist_ok=True)
        (models_dir / "llm").mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(models_dir))
        except AttributeError:
            self._window.show_status(self._t("status.open_models_manual", path=models_dir))
            return False
        self._window.show_status(self._t("status.opened_models_folder", path=models_dir))
        return True

    def load_model_selection(self) -> bool:
        if not self._model_settings_service:
            return False
        selection = self._model_settings_service.load()
        self._window.set_language(selection.ui_language)
        self._window.set_model_selection(selection)
        return True

    def save_model_selection(self, selection: ModelSelection) -> bool:
        if not self._model_settings_service:
            self._window.show_status(self._t("status.settings_storage_unavailable"))
            return False
        self._model_settings_service.save(selection)
        self._window.set_language(selection.ui_language)
        self._window.show_status(self._t("status.settings_saved"))
        return True

    def transcribe_record(
        self,
        record_id: str,
        source_language: Language = Language.AUTO,
    ) -> TranscriptDocument | None:
        if not self._asr_provider_factory or not self._transcript_store:
            self._window.show_status(self._t("status.transcription_service_unavailable"))
            return None
        if not self._ensure_model_type_ready(ModelType.ASR):
            return None
        record = self._record_repository.get_record(record_id)
        if record is None:
            self._window.show_status(self._t("status.record_not_available"))
            return None

        if self._should_run_model_tasks_in_background():
            self._start_background_transcription(record, source_language)
            return None

        self._window.show_status(self._t("status.transcribing_audio"))
        try:
            transcript = self._run_transcription(record, source_language)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            self._window.show_status(self._t("status.transcription_failed_help", error=exc))
            return None
        self._active_record_id = transcript.record_id
        self._window.display_transcript(transcript)
        self._window.set_translation_text("", "")
        self._load_summary_preview(transcript.record_id)
        self._generate_summary(transcript.record_id, switch_to_summary=True)
        self._window.show_status(self._t("status.transcription_completed"))
        self.refresh_history()
        return transcript

    def translate_record(
        self,
        record_id: str,
        target_language: Language,
        mode: TranslationMode = TranslationMode.STANDARD,
    ) -> TranslationDocument | None:
        if not self._llm_provider_factory or not self._transcript_store or not self._translation_store:
            self._window.show_status(self._t("status.translation_service_unavailable"))
            return None
        transcript = self._transcript_store.load(record_id)
        if transcript is None:
            self._window.show_status(self._t("status.transcript_not_available_yet"))
            return None
        source_language = TranscriptionService.resolve_transcript_language(transcript, requested_language=Language.AUTO)
        if source_language == target_language:
            self._window.show_status(
                self._t(
                    "status.translation_target_matches_source",
                    lang_name=self._language_label(source_language),
                )
            )
            return None
        if not self._ensure_model_type_ready(ModelType.LLM_TRANSLATION):
            return None

        if self._should_run_model_tasks_in_background():
            self._start_background_translation(record_id, target_language, mode)
            return None

        self._window.show_status(self._t("status.translating_full_transcript"))
        try:
            translation = self._run_translation(record_id, target_language, mode)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            self._window.show_status(self._t("status.translation_failed_help", error=exc))
            return None
        self._active_record_id = translation.record_id
        self._window.display_translation(translation)
        self._load_summary_preview(record_id)
        self._window.show_status(self._t("status.translation_completed"))
        self.refresh_history()
        return translation

    def translate_record_to_chinese(self, record_id: str) -> TranslationDocument | None:
        return self.translate_record(record_id, Language.CHINESE)

    def translate_record_to_english(self, record_id: str) -> TranslationDocument | None:
        return self.translate_record(record_id, Language.ENGLISH)

    def export_current_transcript(self) -> Path | None:
        return self._export_current(lambda workflow, record_id: workflow.export_transcript(record_id, "txt"))

    def export_current_translation(self) -> Path | None:
        return self._export_current(lambda workflow, record_id: workflow.export_translation(record_id, "md"))

    def export_current_bilingual(self) -> Path | None:
        return self._export_current(lambda workflow, record_id: workflow.export_bilingual(record_id, "md"))

    def export_current_srt(self) -> Path | None:
        return self._export_current(lambda workflow, record_id: workflow.export_srt(record_id))

    def display_transcript_for_record(self, record_id: str) -> bool:
        if not self._transcript_store:
            return False
        transcript = self._transcript_store.load(record_id)
        if transcript is None:
            self._window.show_status(self._t("status.transcript_not_available_yet"))
            return False
        self._active_record_id = record_id
        self._window.display_transcript(transcript)
        self._load_translation_preview(record_id)
        self._load_summary_preview(record_id)
        return True

    def summarize_record(self, record_id: str) -> str | None:
        return self._generate_summary(record_id, switch_to_summary=True)

    def _export_current(self, export_action) -> Path | None:
        if not self._export_workflow:
            self._window.show_status(self._t("status.export_service_unavailable"))
            return None
        if not self._active_record_id:
            self._window.show_status(self._t("status.open_record_before_exporting"))
            return None
        try:
            output_path = export_action(self._export_workflow, self._active_record_id)
        except ValueError as exc:
            self._window.show_status(str(exc))
            return None
        self._window.show_status(self._t("status.exported", path=output_path))
        return output_path

    def _should_run_model_tasks_in_background(self) -> bool:
        return bool(self._run_model_tasks_in_background and self._task_repository and self._task_runner)

    def _ensure_model_type_ready(self, model_type: ModelType) -> bool:
        if not self._model_scanner:
            return True

        self.refresh_models()
        summary = self._model_preparation_service().inspect()
        if model_type == ModelType.ASR and summary.asr_ready:
            return True
        if model_type == ModelType.LLM_TRANSLATION and summary.translation_ready:
            return True
        if model_type == ModelType.LLM_SUMMARY and summary.summary_ready:
            return True

        if model_type == ModelType.ASR:
            self._window.show_status(self._t("status.no_asr_model"))
            return False
        if model_type == ModelType.LLM_SUMMARY:
            self._window.show_status(self._t("status.no_summary_model"))
            return False

        self._window.show_status(self._t("status.no_gguf_translation_model"))
        return False

    def _run_transcription(self, record: Record, source_language: Language) -> TranscriptDocument:
        if not self._asr_provider_factory or not self._transcript_store:
            raise RuntimeError("Transcription service is not available.")
        provider = self._asr_provider_factory.create_provider()
        service = TranscriptionService(
            asr_service=ASRService(provider),
            transcript_store=self._transcript_store,
            record_repository=self._record_repository,
        )
        return service.transcribe_record(record, source_language)

    def _run_translation(
        self,
        record_id: str,
        target_language: Language,
        mode: TranslationMode,
    ) -> TranslationDocument:
        if not self._llm_provider_factory or not self._transcript_store or not self._translation_store:
            raise RuntimeError("Translation service is not available.")
        provider = self._llm_provider_factory.create_translation_provider()
        workflow = TranslationWorkflow(
            translation_service=TranslationService(provider),
            transcript_store=self._transcript_store,
            translation_store=self._translation_store,
            record_repository=self._record_repository,
        )
        return workflow.translate_record(record_id, target_language, mode)

    def _run_summary(self, record_id: str) -> str:
        if not self._llm_provider_factory or not self._transcript_store or not self._summary_store:
            raise RuntimeError("Summary service is not available.")
        provider = self._llm_provider_factory.create_summary_provider()
        workflow = SummaryWorkflow(
            summary_service=SummaryService(provider),
            transcript_store=self._transcript_store,
            summary_store=self._summary_store,
            record_repository=self._record_repository,
        )
        return workflow.summarize_record(record_id)

    def _start_background_preprocessing(self, record: Record) -> None:
        if not self._preprocessing_service or not self._task_repository or not self._task_runner:
            return

        output_path = self._preprocessing_service.prepare_record(record)
        task = self._task_repository.create_task(TaskType.PREPROCESS_AUDIO, record_id=record.id)
        self._task_repository.mark_running(task.id, self._t("status.preprocessing_audio"))
        self._window.show_status(self._t("status.background_preprocessing"))
        self.refresh_history()
        self.refresh_tasks()

        def run_preprocessing() -> Path:
            return self._preprocessing_service.execute_preprocessing(record, output_path)

        self._task_runner.submit(task.id, run_preprocessing)

    def _start_background_transcription(self, record: Record, source_language: Language) -> None:
        if not self._task_repository or not self._task_runner:
            return
        if self._task_repository.find_active_task(record.id, TaskType.TRANSCRIBE):
            self._window.show_status(self._t("status.transcription_already_running"))
            self.refresh_tasks()
            return
        task = self._task_repository.create_task(TaskType.TRANSCRIBE, record_id=record.id)
        self._task_repository.mark_running(task.id, self._t("status.transcribing_audio"))
        self._window.show_status(self._t("status.background_transcribing"))
        self.refresh_history()
        self.refresh_tasks()
        self._task_runner.submit(task.id, lambda: self._run_transcription(record, source_language))

    def _start_background_translation(
        self,
        record_id: str,
        target_language: Language,
        mode: TranslationMode,
    ) -> None:
        if not self._task_repository or not self._task_runner:
            return
        if self._task_repository.find_active_task(record_id, TaskType.TRANSLATE):
            self._window.show_status(self._t("status.translation_already_running"))
            self.refresh_tasks()
            return
        task = self._task_repository.create_task(TaskType.TRANSLATE, record_id=record_id)
        self._task_repository.mark_running(
            task.id,
            self._t("status.translation_task_message", target_language=target_language.value),
        )
        self._window.show_status(self._t("status.background_translating"))
        self.refresh_history()
        self.refresh_tasks()
        self._task_runner.submit(task.id, lambda: self._run_translation(record_id, target_language, mode))

    def _on_background_task_succeeded(self, task_id: str, result: object) -> None:
        if not self._task_repository:
            return
        task = self._task_repository.get_task(task_id)
        if task is None:
            return

        match task.task_type:
            case TaskType.PREPROCESS_AUDIO:
                self._handle_preprocessing_succeeded(task, result)
            case TaskType.TRANSCRIBE:
                self._handle_transcription_succeeded(task, result)
            case TaskType.TRANSLATE:
                self._handle_translation_succeeded(task, result)
            case _:
                self._task_repository.mark_completed(task_id, self._t("status.ready"))
                self.refresh_history()
                self.refresh_tasks()

    def _handle_preprocessing_succeeded(self, task: TaskRecord, result: object) -> None:
        if not self._task_repository or not self._preprocessing_service or not task.record_id:
            return
        output_path = Path(result)
        self._preprocessing_service.mark_preprocessed(task.record_id, output_path)
        self._task_repository.mark_completed(task.id, self._t("status.audio_ready", path=output_path))
        self._window.show_status(self._t("status.audio_ready", path=output_path))
        self.refresh_history()
        self.refresh_tasks()

    def _handle_transcription_succeeded(self, task: TaskRecord, result: object) -> None:
        if not self._task_repository:
            return
        self._task_repository.mark_completed(task.id, self._t("status.transcription_completed"))
        if isinstance(result, TranscriptDocument):
            self._active_record_id = result.record_id
            self._window.display_transcript(result)
            self._window.set_translation_text("", "")
            self._load_summary_preview(result.record_id)
            self._generate_summary(result.record_id, switch_to_summary=True)
        self._window.show_status(self._t("status.transcription_completed"))
        self.refresh_history()
        self.refresh_tasks()

    def _handle_translation_succeeded(self, task: TaskRecord, result: object) -> None:
        if not self._task_repository:
            return
        self._task_repository.mark_completed(task.id, self._t("status.translation_completed"))
        if isinstance(result, TranslationDocument):
            self._active_record_id = result.record_id
            self._window.display_translation(result)
            self._load_summary_preview(result.record_id)
        self._window.show_status(self._t("status.translation_completed"))
        self.refresh_history()
        self.refresh_tasks()

    def _on_background_task_failed(self, task_id: str, error: str) -> None:
        if not self._task_repository:
            return
        task = self._task_repository.get_task(task_id)
        self._task_repository.mark_failed(task_id, error)
        if task and task.task_type in {TaskType.PREPROCESS_AUDIO, TaskType.TRANSCRIBE} and task.record_id:
            self._record_repository.update_status(task.record_id, RecordStatus.FAILED)
        logger.error("Background task failed: %s\n%s", task_id, error)
        self._window.show_status(self._t("status.background_failed"))
        self.refresh_history()
        self.refresh_tasks()

    def _model_preparation_service(self) -> LocalModelPreparationService:
        if not self._model_scanner:
            raise RuntimeError("Model scanner is not configured.")
        return LocalModelPreparationService(self._model_scanner.models_dir)

    def _generate_summary(self, record_id: str, *, switch_to_summary: bool) -> str | None:
        if not self._summary_store or not self._llm_provider_factory or not self._transcript_store:
            return None
        if not self._ensure_model_type_ready(ModelType.LLM_SUMMARY):
            return None

        self._window.show_status(self._t("status.summarizing_transcript"))
        try:
            summary_text = self._run_summary(record_id)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            self._window.show_status(self._t("status.summary_failed_help", error=exc))
            return None

        if switch_to_summary:
            self._window.display_summary(summary_text)
        else:
            self._window.set_summary_text(summary_text)
        self._window.show_status(self._t("status.summary_completed"))
        return summary_text

    def _load_summary_preview(self, record_id: str) -> None:
        if not self._summary_store:
            return
        summary_text = self._summary_store.load(record_id) or ""
        self._window.set_summary_text(summary_text)

    def _load_translation_preview(self, record_id: str) -> None:
        if not self._translation_store:
            self._window.set_translation_text("", "")
            return
        translation = self._translation_store.load(record_id)
        if translation is None:
            self._window.set_translation_text("", "")
            return
        self._window.set_translation_text(
            translation.translated_text,
            translation.bilingual_text or "",
        )

    def _project_root(self) -> Path | None:
        if not self._model_scanner:
            return None
        return self._model_scanner.models_dir.parent

    def _t(self, key: str, **kwargs: object) -> str:
        return self._window.tr(key, **kwargs)

    @staticmethod
    def _language_label(language: Language) -> str:
        return "Chinese" if language == Language.CHINESE else "English"
