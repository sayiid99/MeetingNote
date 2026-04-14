from __future__ import annotations

from pathlib import Path

from meeting_note.core.app_controller import AppController
from meeting_note.core.audio_processor import AudioProcessingResult
from meeting_note.core.contracts import Language, TranscriptDocument, TranscriptSegment, TranslationDocument, TranslationMode
from meeting_note.core.export_service import ExportService
from meeting_note.core.export_workflow import ExportWorkflow
from meeting_note.core.model_scanner import ModelScanner
from meeting_note.core.model_settings import ModelSelection, ModelSettingsService
from meeting_note.core.preprocessing_service import PreprocessingService
from meeting_note.data.database import initialize_database
from meeting_note.data.document_store import SummaryStore, TranscriptStore, TranslationStore
from meeting_note.data.models import ModelType, RecordStatus, TaskStatus, TaskType
from meeting_note.data.repositories import ModelRepository, RecordRepository, SettingsRepository, TaskRepository
from meeting_note.infra.paths import AppPaths
from meeting_note.ui.main_window import MainWindow

class FakeSignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args):
        for callback in self._callbacks:
            callback(*args)


class FakeTaskRunner:
    def __init__(self):
        self.task_succeeded = FakeSignal()
        self.task_failed = FakeSignal()
        self.submitted: dict[str, object] = {}

    def submit(self, task_id: str, callback):
        self.submitted[task_id] = callback

class FakeAudioPreprocessor:
    def preprocess(self, input_path: Path, output_path: Path) -> AudioProcessingResult:
        output_path.write_bytes(b"processed audio content")
        return AudioProcessingResult(source_path=input_path, output_path=output_path)


class FakeASRProvider:
    def transcribe(self, audio_path: Path, source_language: Language) -> TranscriptDocument:
        return TranscriptDocument(
            record_id=audio_path.stem,
            language=source_language,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )


class FakeASRProviderFactory:
    def create_provider(self) -> FakeASRProvider:
        return FakeASRProvider()


class FakeLLMProvider:
    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        if "Target language: Chinese" in prompt or "strictly in Chinese" in prompt:
            return "\u5b8c\u6574\u4e2d\u6587\u7ffb\u8bd1\u3002"
        return "Full translation."


class FakeSummaryProvider:
    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        return "Overview\nThe meeting discussed delivery."


class FakeLLMProviderFactory:
    def create_translation_provider(self) -> FakeLLMProvider:
        return FakeLLMProvider()

    def create_summary_provider(self) -> FakeSummaryProvider:
        return FakeSummaryProvider()


def test_app_controller_creates_record_for_selected_media(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    window = MainWindow(paths)
    repository = RecordRepository(paths.database_path)
    controller = AppController(window=window, record_repository=repository)
    media_file = tmp_path / "demo.mp3"
    media_file.write_bytes(b"fake")

    record = controller.handle_media_selected(str(media_file))

    records = repository.list_records()
    assert record.title == "demo"
    assert controller.current_record == record
    assert len(records) == 1
    assert records[0].original_file_path == media_file
    assert window.history_page.count() == 1


def test_app_controller_clears_results_when_new_media_is_selected(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    window = MainWindow(paths)
    repository = RecordRepository(paths.database_path)
    controller = AppController(window=window, record_repository=repository)
    first_media = tmp_path / "first.mp3"
    first_media.write_bytes(b"first")
    second_media = tmp_path / "second.mp3"
    second_media.write_bytes(b"second")

    controller.handle_media_selected(str(first_media))
    window.results_page.display_transcript(
        TranscriptDocument(
            record_id="rec-1",
            language=Language.ENGLISH,
            segments=[TranscriptSegment(id="seg-1", text="Old transcript", start_time=0, end_time=1)],
        )
    )
    window.results_page.set_translation_text("Old translation", "Old bilingual")
    window.results_page.set_summary_text("Old summary")

    controller.handle_media_selected(str(second_media))

    assert window.results_page.transcript_text() == ""
    assert window.results_page.translation_text() == ""
    assert window.results_page.bilingual_text() == ""
    assert window.results_page.summary_text() == ""


def test_app_controller_selects_new_record_in_history_after_media_selection(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    window = MainWindow(paths)
    repository = RecordRepository(paths.database_path)
    controller = AppController(window=window, record_repository=repository)
    first_media = tmp_path / "first.mp3"
    first_media.write_bytes(b"first")
    second_media = tmp_path / "second.mp3"
    second_media.write_bytes(b"second")

    first_record = controller.handle_media_selected(str(first_media))
    assert window.history_page.selected_record_id() == first_record.id

    second_record = controller.handle_media_selected(str(second_media))

    assert window.history_page.selected_record_id() == second_record.id


def test_app_controller_refresh_history_keeps_active_record_selected(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    window = MainWindow(paths)
    repository = RecordRepository(paths.database_path)
    controller = AppController(window=window, record_repository=repository)
    first_media = tmp_path / "first.mp3"
    first_media.write_bytes(b"first")
    second_media = tmp_path / "second.mp3"
    second_media.write_bytes(b"second")

    first_record = controller.handle_media_selected(str(first_media))
    second_record = controller.handle_media_selected(str(second_media))
    assert window.history_page.selected_record_id() == second_record.id

    assert window.history_page.select_record(first_record.id) is True
    assert window.history_page.selected_record_id() == first_record.id

    controller.refresh_history()

    assert window.history_page.selected_record_id() == second_record.id


def test_app_controller_can_preprocess_selected_media(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    window = MainWindow(paths)
    repository = RecordRepository(paths.database_path)
    preprocessing_service = PreprocessingService(paths, repository, FakeAudioPreprocessor())
    controller = AppController(
        window=window,
        record_repository=repository,
        preprocessing_service=preprocessing_service,
    )
    media_file = tmp_path / "demo.wav"
    media_file.write_bytes(b"fake")

    record = controller.handle_media_selected(str(media_file))
    updated_record = repository.get_record(record.id)

    assert updated_record is not None
    assert updated_record.status == RecordStatus.READY
    assert updated_record.processed_audio_path == paths.processed_audio_path(record.id)
    assert paths.processed_audio_path(record.id).exists()


def test_app_controller_scans_models_into_models_page(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    llm_dir = paths.models_dir / "llm"
    llm_dir.mkdir(parents=True)
    (llm_dir / "Qwen3-4B-Q4_K_M.gguf").write_bytes(b"fake model")

    window = MainWindow(paths)
    AppController(
        window=window,
        record_repository=RecordRepository(paths.database_path),
        model_repository=ModelRepository(paths.database_path),
        model_scanner=ModelScanner(paths.models_dir),
    )

    assert window.models_page.count() == 2
    assert window.settings_page.model_option_count(ModelType.LLM_TRANSLATION) == 1
    assert window.settings_page.model_option_count(ModelType.LLM_SUMMARY) == 1


def test_app_controller_loads_and_saves_model_settings(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    settings_repository = SettingsRepository(paths.database_path)
    settings_service = ModelSettingsService(settings_repository)
    settings_service.save(ModelSelection(selected_translation_model_id="qwen3-4b"))
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=RecordRepository(paths.database_path),
        model_settings_service=settings_service,
    )

    assert window.settings_page.model_selection().selected_translation_model_id == "qwen3-4b"

    new_selection = ModelSelection(selected_summary_model_id="gemma-4", llm_context_length=16384)
    assert controller.save_model_selection(new_selection) is True

    assert settings_service.load() == new_selection


def test_app_controller_transcribes_record_with_selected_provider(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    processed_audio_path = paths.processed_audio_path(record.id)
    processed_audio_path.parent.mkdir(parents=True)
    processed_audio_path.write_bytes(b"processed")
    repository.mark_preprocessed(record.id, processed_audio_path)
    window = MainWindow(paths)
    transcript_store = TranscriptStore(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        asr_provider_factory=FakeASRProviderFactory(),
        transcript_store=transcript_store,
    )

    transcript = controller.transcribe_record(record.id, Language.ENGLISH)

    assert transcript is not None
    assert transcript_store.load(record.id) == transcript
    assert "Hello" in window.results_page.transcript_text()
    assert repository.get_record(record.id).has_transcript is True


def test_app_controller_generates_summary_after_transcription(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    processed_audio_path = paths.processed_audio_path(record.id)
    processed_audio_path.parent.mkdir(parents=True)
    processed_audio_path.write_bytes(b"processed")
    repository.mark_preprocessed(record.id, processed_audio_path)
    window = MainWindow(paths)
    transcript_store = TranscriptStore(paths)
    summary_store = SummaryStore(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        asr_provider_factory=FakeASRProviderFactory(),
        llm_provider_factory=FakeLLMProviderFactory(),
        transcript_store=transcript_store,
        summary_store=summary_store,
    )

    transcript = controller.transcribe_record(record.id, Language.ENGLISH)

    assert transcript is not None
    assert summary_store.load(record.id) == "Overview\nThe meeting discussed delivery."
    assert "Overview" in window.results_page.summary_text()


def test_app_controller_translates_record_with_full_document_provider(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.CHINESE,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )
    )
    repository.mark_transcript_ready(record.id, Path("processed.wav"), "zh", has_speakers=False)
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        llm_provider_factory=FakeLLMProviderFactory(),
        transcript_store=transcript_store,
        translation_store=translation_store,
    )

    translation = controller.translate_record(record.id, Language.ENGLISH)

    assert translation is not None
    assert translation.translated_text == "Full translation."
    assert translation_store.load(record.id) == translation
    assert "Full translation." in window.results_page.translation_text()
    assert repository.get_record(record.id).has_translation is True


def test_app_controller_skips_translation_when_target_matches_source_language(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.ENGLISH,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )
    )
    repository.mark_transcript_ready(record.id, Path("processed.wav"), "en", has_speakers=False)
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        llm_provider_factory=FakeLLMProviderFactory(),
        transcript_store=transcript_store,
        translation_store=translation_store,
    )

    translation = controller.translate_record(record.id, Language.ENGLISH)

    assert translation is None
    assert translation_store.load(record.id) is None
    assert window.statusBar().currentMessage() == "Transcript language is already English. Choose the other target language."


def test_app_controller_displays_stored_transcript(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.ENGLISH,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )
    )
    repository.mark_transcript_ready(record.id, Path("processed.wav"), "en", has_speakers=False)
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        transcript_store=transcript_store,
    )

    assert controller.display_transcript_for_record(record.id) is True
    assert "Hello" in window.results_page.transcript_text()


def test_app_controller_loads_existing_summary_preview(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    summary_store = SummaryStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.ENGLISH,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )
    )
    summary_store.save(record.id, "Stored summary")
    repository.mark_transcript_ready(record.id, Path("processed.wav"), "en", has_speakers=False)
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        transcript_store=transcript_store,
        summary_store=summary_store,
    )

    assert controller.display_transcript_for_record(record.id) is True
    assert window.results_page.summary_text() == "Stored summary"


def test_app_controller_loads_existing_translation_preview(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.ENGLISH,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )
    )
    translation_store.save(
        TranslationDocument(
            record_id=record.id,
            source_language=Language.ENGLISH,
            target_language=Language.CHINESE,
            mode=TranslationMode.STANDARD,
            translated_text="你好",
            bilingual_text="Hello\n\n你好",
        )
    )
    repository.mark_transcript_ready(record.id, Path("processed.wav"), "en", has_speakers=False)
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        transcript_store=transcript_store,
        translation_store=translation_store,
    )

    assert controller.display_transcript_for_record(record.id) is True
    assert window.results_page.translation_text() == "你好"
    assert window.results_page.bilingual_text() == "Hello\n\n你好"


def test_app_controller_clears_translation_preview_when_record_has_no_translation(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record_with_translation = repository.create_record("with-translation")
    record_without_translation = repository.create_record("without-translation")
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record_with_translation.id,
            language=Language.ENGLISH,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )
    )
    transcript_store.save(
        TranscriptDocument(
            record_id=record_without_translation.id,
            language=Language.ENGLISH,
            segments=[TranscriptSegment(id="seg-1", text="World", start_time=0, end_time=1)],
        )
    )
    translation_store.save(
        TranslationDocument(
            record_id=record_with_translation.id,
            source_language=Language.ENGLISH,
            target_language=Language.CHINESE,
            mode=TranslationMode.STANDARD,
            translated_text="你好",
            bilingual_text="Hello\n\n你好",
        )
    )
    repository.mark_transcript_ready(record_with_translation.id, Path("processed.wav"), "en", has_speakers=False)
    repository.mark_transcript_ready(record_without_translation.id, Path("processed.wav"), "en", has_speakers=False)
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        transcript_store=transcript_store,
        translation_store=translation_store,
    )

    assert controller.display_transcript_for_record(record_with_translation.id) is True
    assert window.results_page.translation_text() == "你好"
    assert controller.display_transcript_for_record(record_without_translation.id) is True
    assert window.results_page.translation_text() == ""
    assert window.results_page.bilingual_text() == ""


def test_app_controller_opens_transcript_from_history_signal(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.ENGLISH,
            segments=[TranscriptSegment(id="seg-1", text="Opened from history", start_time=0, end_time=1)],
        )
    )
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        transcript_store=transcript_store,
    )

    window._controller = controller
    window.history_page.open_record_at(0)

    assert "Opened from history" in window.results_page.transcript_text()





def test_app_controller_translates_to_english_from_history_signal(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.CHINESE,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )
    )
    repository.mark_transcript_ready(record.id, Path("processed.wav"), "zh", has_speakers=False)
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        llm_provider_factory=FakeLLMProviderFactory(),
        transcript_store=transcript_store,
        translation_store=translation_store,
    )
    window._controller = controller

    window.history_page.translate_to_english_button.click()

    translation = translation_store.load(record.id)
    assert translation is not None
    assert translation.target_language == Language.ENGLISH


def test_app_controller_translates_to_chinese_from_history_signal(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.ENGLISH,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )
    )
    repository.mark_transcript_ready(record.id, Path("processed.wav"), "en", has_speakers=False)
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        llm_provider_factory=FakeLLMProviderFactory(),
        transcript_store=transcript_store,
        translation_store=translation_store,
    )
    window._controller = controller

    window.history_page.translate_to_chinese_button.click()

    translation = translation_store.load(record.id)
    assert translation is not None
    assert translation.target_language == Language.CHINESE



def test_app_controller_runs_transcription_in_background_when_task_runner_available(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    task_repository = TaskRepository(paths.database_path)
    record = repository.create_record("demo")
    processed_audio_path = paths.processed_audio_path(record.id)
    processed_audio_path.parent.mkdir(parents=True)
    processed_audio_path.write_bytes(b"processed")
    repository.mark_preprocessed(record.id, processed_audio_path)
    transcript_store = TranscriptStore(paths)
    window = MainWindow(paths)
    task_runner = FakeTaskRunner()
    controller = AppController(
        window=window,
        record_repository=repository,
        asr_provider_factory=FakeASRProviderFactory(),
        task_repository=task_repository,
        task_runner=task_runner,
        transcript_store=transcript_store,
    )

    assert controller.transcribe_record(record.id, Language.ENGLISH) is None
    assert len(task_runner.submitted) == 1
    task_id, callback = next(iter(task_runner.submitted.items()))
    task = task_repository.get_task(task_id)
    assert task is not None
    assert task.task_type == TaskType.TRANSCRIBE
    assert task.status == TaskStatus.RUNNING

    result = callback()
    controller._on_background_task_succeeded(task_id, result)

    completed_task = task_repository.get_task(task_id)
    assert completed_task is not None
    assert completed_task.status == TaskStatus.COMPLETED
    assert transcript_store.load(record.id) == result
    assert "Hello" in window.results_page.transcript_text()


def test_app_controller_runs_translation_in_background_when_task_runner_available(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    task_repository = TaskRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.CHINESE,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )
    )
    repository.mark_transcript_ready(record.id, Path("processed.wav"), "zh", has_speakers=False)
    window = MainWindow(paths)
    task_runner = FakeTaskRunner()
    controller = AppController(
        window=window,
        record_repository=repository,
        llm_provider_factory=FakeLLMProviderFactory(),
        task_repository=task_repository,
        task_runner=task_runner,
        transcript_store=transcript_store,
        translation_store=translation_store,
    )

    assert controller.translate_record(record.id, Language.ENGLISH) is None
    assert len(task_runner.submitted) == 1
    task_id, callback = next(iter(task_runner.submitted.items()))
    task = task_repository.get_task(task_id)
    assert task is not None
    assert task.task_type == TaskType.TRANSLATE
    assert task.status == TaskStatus.RUNNING

    result = callback()
    controller._on_background_task_succeeded(task_id, result)

    completed_task = task_repository.get_task(task_id)
    assert completed_task is not None
    assert completed_task.status == TaskStatus.COMPLETED
    assert translation_store.load(record.id) == result
    assert "Full translation." in window.results_page.translation_text()


def test_app_controller_marks_transcription_background_failure(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    task_repository = TaskRepository(paths.database_path)
    record = repository.create_record("demo")
    task = task_repository.create_task(TaskType.TRANSCRIBE, record_id=record.id)
    task_repository.mark_running(task.id, "Transcribing audio")
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        task_repository=task_repository,
        task_runner=FakeTaskRunner(),
    )

    controller._on_background_task_failed(task.id, "boom")

    failed_task = task_repository.get_task(task.id)
    failed_record = repository.get_record(record.id)
    assert failed_task is not None
    assert failed_task.status == TaskStatus.FAILED
    assert failed_record is not None
    assert failed_record.status == RecordStatus.FAILED



def test_app_controller_recovers_stale_active_tasks_on_startup(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    task_repository = TaskRepository(paths.database_path)
    record = repository.create_record("demo")
    repository.update_status(record.id, RecordStatus.TRANSCRIBING)
    stale_running = task_repository.create_task(TaskType.TRANSCRIBE, record_id=record.id)
    stale_queued = task_repository.create_task(TaskType.TRANSLATE, record_id=record.id)
    task_repository.mark_running(stale_running.id, "running")
    window = MainWindow(paths)

    AppController(
        window=window,
        record_repository=repository,
        task_repository=task_repository,
        task_runner=FakeTaskRunner(),
    )

    running_task = task_repository.get_task(stale_running.id)
    queued_task = task_repository.get_task(stale_queued.id)
    assert running_task is not None
    assert queued_task is not None
    assert running_task.status == TaskStatus.FAILED
    assert queued_task.status == TaskStatus.FAILED
    assert task_repository.list_active_tasks() == []
    refreshed_record = repository.get_record(record.id)
    assert refreshed_record is not None
    assert refreshed_record.status == RecordStatus.FAILED


def test_app_controller_refreshes_tasks_page(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    task_repository = TaskRepository(paths.database_path)
    task = task_repository.create_task(TaskType.TRANSLATE, record_id="rec-1")
    task_repository.mark_running(task.id, "Translating full transcript")
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        task_repository=task_repository,
    )

    controller.refresh_tasks()

    assert window.tasks_page.count() == 1
    assert "translate | running" in window.tasks_page.task_text(0)
    assert "Translating full transcript" in window.tasks_page.task_text(0)


def test_app_controller_clears_finished_tasks_from_tasks_page(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    task_repository = TaskRepository(paths.database_path)
    running = task_repository.create_task(TaskType.TRANSCRIBE, record_id="rec-1")
    completed = task_repository.create_task(TaskType.TRANSLATE, record_id="rec-1")
    task_repository.mark_running(running.id, "Running")
    task_repository.mark_completed(completed.id, "Done")
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        task_repository=task_repository,
    )

    controller.clear_finished_tasks()

    assert window.tasks_page.count() == 1
    assert "transcribe | running" in window.tasks_page.task_text(0)
    assert window.statusBar().currentMessage() == "Cleared 1 finished tasks."


def test_app_controller_clears_history_records_tasks_and_artifacts(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    task_repository = TaskRepository(paths.database_path)
    first = repository.create_record("first")
    second = repository.create_record("second")
    artifact = paths.record_dir(first.id) / "artifact.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("cached", encoding="utf-8")
    first_task = task_repository.create_task(TaskType.TRANSLATE, record_id=first.id)
    second_task = task_repository.create_task(TaskType.PREPROCESS_AUDIO, record_id=second.id)
    task_repository.mark_completed(first_task.id, "done")
    task_repository.mark_completed(second_task.id, "done")

    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        task_repository=task_repository,
        paths=paths,
    )
    window.results_page.set_summary_text("stale summary")

    controller.clear_history()

    assert repository.list_records() == []
    assert task_repository.list_tasks() == []
    assert paths.record_dir(first.id).exists() is False
    assert paths.record_dir(second.id).exists() is False
    assert window.history_page.count() == 0
    assert window.results_page.summary_text() == ""
    assert window.statusBar().currentMessage() == "Cleared 2 history records."


def test_app_controller_blocks_history_clear_when_active_tasks_exist(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    task_repository = TaskRepository(paths.database_path)
    record = repository.create_record("demo")
    running = task_repository.create_task(TaskType.TRANSCRIBE, record_id=record.id)
    task_repository.mark_running(running.id, "running")
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        task_repository=task_repository,
        paths=paths,
    )

    controller.clear_history()

    assert len(repository.list_records()) == 1
    assert len(task_repository.list_tasks()) == 1
    assert window.statusBar().currentMessage() == "Cannot clear history while 1 background task(s) are running."




def build_export_workflow(paths: AppPaths) -> ExportWorkflow:
    return ExportWorkflow(
        paths=paths,
        export_service=ExportService(),
        transcript_store=TranscriptStore(paths),
        translation_store=TranslationStore(paths),
        summary_store=SummaryStore(paths),
    )


def test_app_controller_exports_current_transcript(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.ENGLISH,
            segments=[TranscriptSegment(id="seg-1", text="Export me", start_time=0, end_time=1)],
        )
    )
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        transcript_store=transcript_store,
        export_workflow=build_export_workflow(paths),
    )
    controller.display_transcript_for_record(record.id)

    output_path = controller.export_current_transcript()

    assert output_path == paths.exports_dir(record.id) / "transcript.txt"
    assert output_path is not None
    assert "Export me" in output_path.read_text(encoding="utf-8")


def test_app_controller_exports_translation_and_bilingual_from_results_button(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.CHINESE,
            segments=[TranscriptSegment(id="seg-1", text="Source", start_time=0, end_time=1)],
        )
    )
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        llm_provider_factory=FakeLLMProviderFactory(),
        transcript_store=transcript_store,
        translation_store=translation_store,
        export_workflow=build_export_workflow(paths),
        run_model_tasks_in_background=False,
    )
    window._controller = controller
    controller.translate_record(record.id, Language.ENGLISH)

    window.results_page.export_translation_button.click()
    bilingual_path = controller.export_current_bilingual()

    translation_path = paths.exports_dir(record.id) / "translation.md"
    assert translation_path.exists()
    assert "Full translation." in translation_path.read_text(encoding="utf-8")
    assert bilingual_path == paths.exports_dir(record.id) / "bilingual.md"
    assert bilingual_path is not None
    assert "Full translation." in bilingual_path.read_text(encoding="utf-8")


def test_app_controller_export_requires_active_record(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=RecordRepository(paths.database_path),
        export_workflow=build_export_workflow(paths),
    )

    assert controller.export_current_transcript() is None
    assert window.statusBar().currentMessage() == "Open a record before exporting."


def test_app_controller_avoids_duplicate_background_translation_tasks(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    task_repository = TaskRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.CHINESE,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )
    )
    repository.mark_transcript_ready(record.id, Path("processed.wav"), "zh", has_speakers=False)
    window = MainWindow(paths)
    task_runner = FakeTaskRunner()
    controller = AppController(
        window=window,
        record_repository=repository,
        llm_provider_factory=FakeLLMProviderFactory(),
        task_repository=task_repository,
        task_runner=task_runner,
        transcript_store=transcript_store,
        translation_store=translation_store,
    )

    controller.translate_record(record.id, Language.ENGLISH)
    assert len(task_runner.submitted) == 1

    controller.translate_record(record.id, Language.ENGLISH)

    assert len(task_runner.submitted) == 1
    assert window.statusBar().currentMessage() == "Translation is already running for this record."


def test_app_controller_avoids_duplicate_background_transcription_tasks(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    task_repository = TaskRepository(paths.database_path)
    record = repository.create_record("demo")
    processed_audio_path = paths.processed_audio_path(record.id)
    processed_audio_path.parent.mkdir(parents=True)
    processed_audio_path.write_bytes(b"processed")
    repository.mark_preprocessed(record.id, processed_audio_path)
    transcript_store = TranscriptStore(paths)
    window = MainWindow(paths)
    task_runner = FakeTaskRunner()
    controller = AppController(
        window=window,
        record_repository=repository,
        asr_provider_factory=FakeASRProviderFactory(),
        task_repository=task_repository,
        task_runner=task_runner,
        transcript_store=transcript_store,
    )

    controller.transcribe_record(record.id, Language.ENGLISH)
    assert len(task_runner.submitted) == 1

    controller.transcribe_record(record.id, Language.ENGLISH)

    assert len(task_runner.submitted) == 1
    assert window.statusBar().currentMessage() == "Transcription is already running for this record."


