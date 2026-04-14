from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget

from meeting_note.core.contracts import TranscriptDocument, TranslationDocument
from meeting_note.core.formatting import format_transcript_document
from meeting_note.ui.i18n import DEFAULT_UI_LANGUAGE, normalize_language, translate


class ResultsPage(QWidget):
    export_transcript_requested = Signal()
    export_translation_requested = Signal()
    export_bilingual_requested = Signal()

    def __init__(self, language: str = DEFAULT_UI_LANGUAGE):
        super().__init__()
        self._language = normalize_language(language)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._title_label = QLabel()
        self._title_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(self._title_label)

        self._tabs = QTabWidget()
        self._transcript_text = QTextEdit()
        self._transcript_text.setReadOnly(True)
        self._translation_text = QTextEdit()
        self._translation_text.setReadOnly(True)
        self._bilingual_text = QTextEdit()
        self._bilingual_text.setReadOnly(True)
        self._summary_text = QTextEdit()
        self._summary_text.setReadOnly(True)

        self._tabs.addTab(self._transcript_text, "")
        self._tabs.addTab(self._translation_text, "")
        self._tabs.addTab(self._bilingual_text, "")
        self._tabs.addTab(self._summary_text, "")
        layout.addWidget(self._tabs)

        export_row = QHBoxLayout()
        self._export_transcript_button = QPushButton()
        self._export_translation_button = QPushButton()
        self._export_bilingual_button = QPushButton()
        self._export_transcript_button.clicked.connect(self.export_transcript_requested.emit)
        self._export_translation_button.clicked.connect(self.export_translation_requested.emit)
        self._export_bilingual_button.clicked.connect(self.export_bilingual_requested.emit)
        export_row.addWidget(self._export_transcript_button)
        export_row.addWidget(self._export_translation_button)
        export_row.addWidget(self._export_bilingual_button)
        export_row.addStretch(1)
        layout.addLayout(export_row)
        self._retranslate_ui()

    @property
    def export_transcript_button(self) -> QPushButton:
        return self._export_transcript_button

    @property
    def export_translation_button(self) -> QPushButton:
        return self._export_translation_button

    @property
    def export_bilingual_button(self) -> QPushButton:
        return self._export_bilingual_button

    def display_transcript(self, transcript: TranscriptDocument) -> None:
        self._transcript_text.setPlainText(format_transcript_document(transcript))
        self._tabs.setCurrentWidget(self._transcript_text)

    def display_translation(self, translation: TranslationDocument) -> None:
        self.set_translation_text(translation.translated_text, translation.bilingual_text or "")
        self._tabs.setCurrentWidget(self._translation_text)

    def set_translation_text(self, translated_text: str, bilingual_text: str) -> None:
        self._translation_text.setPlainText(translated_text)
        self._bilingual_text.setPlainText(bilingual_text)

    def display_summary(self, summary_text: str) -> None:
        self._summary_text.setPlainText(summary_text)
        self._tabs.setCurrentWidget(self._summary_text)

    def set_summary_text(self, summary_text: str) -> None:
        self._summary_text.setPlainText(summary_text)

    def clear_results(self) -> None:
        self._transcript_text.clear()
        self._translation_text.clear()
        self._bilingual_text.clear()
        self._summary_text.clear()
        self._tabs.setCurrentWidget(self._transcript_text)

    def transcript_text(self) -> str:
        return self._transcript_text.toPlainText()

    def translation_text(self) -> str:
        return self._translation_text.toPlainText()

    def bilingual_text(self) -> str:
        return self._bilingual_text.toPlainText()

    def summary_text(self) -> str:
        return self._summary_text.toPlainText()

    def set_language(self, language: str) -> None:
        self._language = normalize_language(language)
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self._title_label.setText(self._tr("results.title"))
        self._tabs.setTabText(0, self._tr("results.tab.transcript"))
        self._tabs.setTabText(1, self._tr("results.tab.translation"))
        self._tabs.setTabText(2, self._tr("results.tab.bilingual"))
        self._tabs.setTabText(3, self._tr("results.tab.summary"))
        self._export_transcript_button.setText(self._tr("results.export_transcript"))
        self._export_translation_button.setText(self._tr("results.export_translation"))
        self._export_bilingual_button.setText(self._tr("results.export_bilingual"))

    def _tr(self, key: str, **kwargs: object) -> str:
        return translate(self._language, key, **kwargs)
