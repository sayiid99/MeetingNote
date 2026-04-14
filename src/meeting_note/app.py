from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PySide6.QtWidgets import QApplication

from meeting_note.core.app_controller import AppController
from meeting_note.core.asr_provider_factory import ASRProviderFactory
from meeting_note.core.audio_processor import AudioProcessor
from meeting_note.core.export_service import ExportService
from meeting_note.core.export_workflow import ExportWorkflow
from meeting_note.core.llm_provider_factory import LLMProviderFactory
from meeting_note.core.model_scanner import ModelScanner
from meeting_note.core.model_settings import ModelSettingsService
from meeting_note.core.preprocessing_service import PreprocessingService
from meeting_note.core.task_runner import TaskRunner
from meeting_note.data.database import initialize_database
from meeting_note.data.document_store import SummaryStore, TranscriptStore, TranslationStore
from meeting_note.data.repositories import ModelRepository, RecordRepository, SettingsRepository, TaskRepository
from meeting_note.infra.logging_config import configure_logging
from meeting_note.infra.paths import AppPaths
from meeting_note.ui.main_window import MainWindow


def run_app(argv: Sequence[str] | None = None) -> int:
    paths = AppPaths.from_project_root(Path.cwd())
    paths.ensure_runtime_dirs()
    configure_logging(paths.logs_dir)
    initialize_database(paths.database_path)

    app = QApplication(list(argv or []))
    app.setApplicationName("MeetingNote")
    app.setApplicationDisplayName("MeetingNote")

    record_repository = RecordRepository(paths.database_path)
    model_repository = ModelRepository(paths.database_path)
    task_repository = TaskRepository(paths.database_path)
    settings_repository = SettingsRepository(paths.database_path)
    model_settings_service = ModelSettingsService(settings_repository)
    model_selection = model_settings_service.load()
    window = MainWindow(paths=paths, language=model_selection.ui_language)
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    summary_store = SummaryStore(paths)
    preprocessing_service = PreprocessingService(
        paths=paths,
        record_repository=record_repository,
        audio_preprocessor=AudioProcessor(),
    )
    export_workflow = ExportWorkflow(
        paths=paths,
        export_service=ExportService(),
        transcript_store=transcript_store,
        translation_store=translation_store,
        summary_store=summary_store,
    )
    controller = AppController(
        window=window,
        record_repository=record_repository,
        preprocessing_service=preprocessing_service,
        model_repository=model_repository,
        model_scanner=ModelScanner(paths.models_dir),
        model_settings_service=model_settings_service,
        asr_provider_factory=ASRProviderFactory(
            model_repository=model_repository,
            model_settings_service=model_settings_service,
        ),
        llm_provider_factory=LLMProviderFactory(
            model_repository=model_repository,
            model_settings_service=model_settings_service,
        ),
        export_workflow=export_workflow,
        task_repository=task_repository,
        task_runner=TaskRunner(),
        transcript_store=transcript_store,
        translation_store=translation_store,
        summary_store=summary_store,
        paths=paths,
    )
    window._controller = controller
    window.show()
    return app.exec()
