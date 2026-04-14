from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow, QStatusBar, QTabWidget

from meeting_note.core.contracts import TranscriptDocument, TranslationDocument
from meeting_note.core.model_preparation import ModelAvailabilitySummary
from meeting_note.core.model_settings import ModelSelection
from meeting_note.data.models import LocalModel, Record, TaskRecord
from meeting_note.infra.paths import AppPaths
from meeting_note.ui.history_page import HistoryPage
from meeting_note.ui.i18n import DEFAULT_UI_LANGUAGE, normalize_language, translate
from meeting_note.ui.models_page import ModelsPage
from meeting_note.ui.results_page import ResultsPage
from meeting_note.ui.settings_page import SettingsPage
from meeting_note.ui.tasks_page import TasksPage
from meeting_note.ui.upload_page import UploadPage

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    media_selected = Signal(str)
    history_refresh_requested = Signal()
    history_clear_requested = Signal()
    models_refresh_requested = Signal()
    models_prepare_requested = Signal()
    models_open_folder_requested = Signal()
    tasks_refresh_requested = Signal()
    tasks_clear_requested = Signal()
    record_open_requested = Signal(str)
    record_transcribe_requested = Signal(str)
    record_translate_to_chinese_requested = Signal(str)
    record_translate_to_english_requested = Signal(str)
    export_transcript_requested = Signal()
    export_translation_requested = Signal()
    export_bilingual_requested = Signal()
    settings_save_requested = Signal(object)
    settings_reset_requested = Signal()

    def __init__(self, paths: AppPaths, language: str = DEFAULT_UI_LANGUAGE):
        super().__init__()
        self._paths = paths
        self._language = normalize_language(language)
        self.resize(1280, 800)
        self.setMinimumSize(1100, 700)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._tabs = QTabWidget()

        self._upload_page = UploadPage(language=self._language)
        self._upload_page.media_selected.connect(self._on_media_selected)

        self._results_page = ResultsPage(language=self._language)
        self._results_page.export_transcript_requested.connect(self.export_transcript_requested.emit)
        self._results_page.export_translation_requested.connect(self.export_translation_requested.emit)
        self._results_page.export_bilingual_requested.connect(self.export_bilingual_requested.emit)

        self._history_page = HistoryPage(language=self._language)
        self._history_page.refresh_button.clicked.connect(self.history_refresh_requested.emit)
        self._history_page.clear_button.clicked.connect(self.history_clear_requested.emit)
        self._history_page.record_open_requested.connect(self.record_open_requested.emit)
        self._history_page.record_transcribe_requested.connect(self.record_transcribe_requested.emit)
        self._history_page.record_translate_to_chinese_requested.connect(
            self.record_translate_to_chinese_requested.emit
        )
        self._history_page.record_translate_to_english_requested.connect(
            self.record_translate_to_english_requested.emit
        )

        self._tasks_page = TasksPage(language=self._language)
        self._tasks_page.clear_button.clicked.connect(self.tasks_clear_requested.emit)
        self._tasks_page.refresh_button.clicked.connect(self.tasks_refresh_requested.emit)

        self._models_page = ModelsPage(language=self._language)
        self._models_page.refresh_button.clicked.connect(self.models_refresh_requested.emit)
        self._models_page.prepare_button.clicked.connect(self.models_prepare_requested.emit)
        self._models_page.open_folder_button.clicked.connect(self.models_open_folder_requested.emit)

        self._settings_page = SettingsPage(language=self._language)
        self._settings_page.save_requested.connect(self.settings_save_requested.emit)
        self._settings_page.reset_requested.connect(self.settings_reset_requested.emit)

        self._tabs.addTab(self._upload_page, "")
        self._tabs.addTab(self._results_page, "")
        self._tabs.addTab(self._history_page, "")
        self._tabs.addTab(self._tasks_page, "")
        self._tabs.addTab(self._models_page, "")
        self._tabs.addTab(self._settings_page, "")
        self.setCentralWidget(self._tabs)
        self.setStatusBar(QStatusBar())
        self._retranslate_ui()
        self.show_status(self.tr("status.ready"))

    @property
    def results_page(self) -> ResultsPage:
        return self._results_page

    @property
    def history_page(self) -> HistoryPage:
        return self._history_page

    @property
    def tasks_page(self) -> TasksPage:
        return self._tasks_page

    @property
    def models_page(self) -> ModelsPage:
        return self._models_page

    @property
    def settings_page(self) -> SettingsPage:
        return self._settings_page

    def set_history_records(self, records: list[Record]) -> None:
        self._history_page.set_records(records)

    def set_tasks(self, tasks: list[TaskRecord]) -> None:
        self._tasks_page.set_tasks(tasks)

    def set_models(self, models: list[LocalModel]) -> None:
        self._models_page.set_models(models)
        self._settings_page.set_available_models(models)

    def set_model_availability(self, summary: ModelAvailabilitySummary) -> None:
        self._models_page.set_model_availability(summary)

    def set_model_selection(self, selection: ModelSelection) -> None:
        self._settings_page.set_model_selection(selection)

    def display_transcript(self, transcript: TranscriptDocument) -> None:
        self._results_page.display_transcript(transcript)
        self._tabs.setCurrentWidget(self._results_page)

    def display_translation(self, translation: TranslationDocument) -> None:
        self._results_page.display_translation(translation)
        self._tabs.setCurrentWidget(self._results_page)

    def display_summary(self, summary_text: str) -> None:
        self._results_page.display_summary(summary_text)
        self._tabs.setCurrentWidget(self._results_page)

    def set_summary_text(self, summary_text: str) -> None:
        self._results_page.set_summary_text(summary_text)

    def set_translation_text(self, translated_text: str, bilingual_text: str) -> None:
        self._results_page.set_translation_text(translated_text, bilingual_text)

    def clear_results(self) -> None:
        self._results_page.clear_results()

    def show_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def tr(self, key: str, **kwargs: object) -> str:
        return translate(self._language, key, **kwargs)

    def set_language(self, language: str) -> None:
        normalized = normalize_language(language)
        if normalized == self._language:
            return
        self._language = normalized
        self._upload_page.set_language(normalized)
        self._results_page.set_language(normalized)
        self._history_page.set_language(normalized)
        self._tasks_page.set_language(normalized)
        self._models_page.set_language(normalized)
        self._settings_page.set_language(normalized)
        self._retranslate_ui()

    def _on_media_selected(self, file_path: str) -> None:
        logger.info("Selected media file: %s", file_path)
        self.show_status(self.tr("upload.selected", name=Path(file_path).name))
        self.media_selected.emit(file_path)

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self.tr("window.title"))
        self._tabs.setTabText(0, self.tr("tab.new"))
        self._tabs.setTabText(1, self.tr("tab.results"))
        self._tabs.setTabText(2, self.tr("tab.history"))
        self._tabs.setTabText(3, self.tr("tab.tasks"))
        self._tabs.setTabText(4, self.tr("tab.models"))
        self._tabs.setTabText(5, self.tr("tab.settings"))
