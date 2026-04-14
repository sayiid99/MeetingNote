from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from meeting_note.data.models import Record, TaskRecord, TaskStatus, TaskType
from meeting_note.ui.i18n import DEFAULT_UI_LANGUAGE, normalize_language, translate


class HistoryPage(QWidget):
    history_clear_requested = Signal()
    record_open_requested = Signal(str)
    record_transcribe_requested = Signal(str)
    record_translate_to_chinese_requested = Signal(str)
    record_translate_to_english_requested = Signal(str)

    def __init__(self, language: str = DEFAULT_UI_LANGUAGE):
        super().__init__()
        self._language = normalize_language(language)
        self._records_by_id: dict[str, Record] = {}
        self._active_task_types_by_record: dict[str, set[TaskType]] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._title_label = QLabel()
        self._title_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(self._title_label)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._emit_record_open_requested)
        self._list.currentItemChanged.connect(lambda *_: self._update_action_states())
        layout.addWidget(self._list)

        action_row = QHBoxLayout()
        self._open_button = QPushButton()
        self._transcribe_button = QPushButton()
        self._translate_to_chinese_button = QPushButton()
        self._translate_to_english_button = QPushButton()
        self._clear_button = QPushButton()
        self._refresh_button = QPushButton()

        self._open_button.clicked.connect(self._emit_selected_record_open_requested)
        self._transcribe_button.clicked.connect(self._emit_selected_record_transcribe_requested)
        self._translate_to_chinese_button.clicked.connect(self._emit_selected_translate_to_chinese_requested)
        self._translate_to_english_button.clicked.connect(self._emit_selected_translate_to_english_requested)

        action_row.addWidget(self._open_button)
        action_row.addWidget(self._transcribe_button)
        action_row.addWidget(self._translate_to_chinese_button)
        action_row.addWidget(self._translate_to_english_button)
        action_row.addStretch(1)
        self._clear_button.clicked.connect(self.history_clear_requested.emit)
        action_row.addWidget(self._clear_button)
        action_row.addWidget(self._refresh_button)
        layout.addLayout(action_row)

        self._status_hint = QLabel()
        self._status_hint.setWordWrap(True)
        layout.addWidget(self._status_hint)
        self._retranslate_ui()
        self._update_action_states()

    @property
    def refresh_button(self) -> QPushButton:
        return self._refresh_button

    @property
    def clear_button(self) -> QPushButton:
        return self._clear_button

    @property
    def open_button(self) -> QPushButton:
        return self._open_button

    @property
    def transcribe_button(self) -> QPushButton:
        return self._transcribe_button

    @property
    def translate_to_chinese_button(self) -> QPushButton:
        return self._translate_to_chinese_button

    @property
    def translate_to_english_button(self) -> QPushButton:
        return self._translate_to_english_button

    def status_hint_text(self) -> str:
        return self._status_hint.text()

    def set_language(self, language: str) -> None:
        self._language = normalize_language(language)
        self._retranslate_ui()
        self.set_records(list(self._records_by_id.values()))

    def set_records(self, records: list[Record]) -> None:
        current_record_id = self.selected_record_id()
        self._records_by_id = {record.id: record for record in records}
        self._list.clear()
        for record in records:
            item = QListWidgetItem(self._format_record(record))
            item.setData(Qt.ItemDataRole.UserRole, record.id)
            self._list.addItem(item)
        if current_record_id:
            self.select_record(current_record_id)
        elif self._list.count() > 0:
            self._list.setCurrentRow(0)
        self._clear_button.setEnabled(bool(records))
        self._update_action_states()

    def set_active_tasks(self, tasks: list[TaskRecord]) -> None:
        self._active_task_types_by_record = {}
        for task in tasks:
            if task.record_id is None or task.status not in {TaskStatus.QUEUED, TaskStatus.RUNNING}:
                continue
            self._active_task_types_by_record.setdefault(task.record_id, set()).add(task.task_type)
        self._update_action_states()

    def count(self) -> int:
        return self._list.count()

    def selected_record_id(self) -> str | None:
        item = self._list.currentItem()
        if item is None:
            return None
        record_id = item.data(Qt.ItemDataRole.UserRole)
        return str(record_id) if record_id else None

    def select_record(self, record_id: str) -> bool:
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item and item.data(Qt.ItemDataRole.UserRole) == record_id:
                self._list.setCurrentItem(item)
                return True
        return False

    def open_record_at(self, row: int) -> None:
        item = self._list.item(row)
        if item is not None:
            self._emit_record_open_requested(item)

    def _emit_selected_record_open_requested(self) -> None:
        self._emit_for_selected_record(self.record_open_requested)

    def _emit_selected_record_transcribe_requested(self) -> None:
        self._emit_for_selected_record(self.record_transcribe_requested)

    def _emit_selected_translate_to_chinese_requested(self) -> None:
        self._emit_for_selected_record(self.record_translate_to_chinese_requested)

    def _emit_selected_translate_to_english_requested(self) -> None:
        self._emit_for_selected_record(self.record_translate_to_english_requested)

    def _emit_record_open_requested(self, item: QListWidgetItem) -> None:
        record_id = item.data(Qt.ItemDataRole.UserRole)
        if record_id:
            self.record_open_requested.emit(str(record_id))

    def _emit_for_selected_record(self, signal: Signal) -> None:
        record_id = self.selected_record_id()
        if record_id:
            signal.emit(record_id)

    def _update_action_states(self) -> None:
        record_id = self.selected_record_id()
        record = self._records_by_id.get(record_id) if record_id else None
        active_task_types = self._active_task_types_by_record.get(record_id or "", set())

        can_open = record is not None
        can_transcribe = bool(
            record
            and record.processed_audio_path is not None
            and TaskType.PREPROCESS_AUDIO not in active_task_types
            and TaskType.TRANSCRIBE not in active_task_types
        )
        can_translate = bool(record and record.has_transcript and TaskType.TRANSLATE not in active_task_types)
        source_language = (record.source_language or "").strip().lower() if record else ""
        can_translate_to_chinese = can_translate and source_language != "zh"
        can_translate_to_english = can_translate and source_language != "en"

        self._clear_button.setEnabled(bool(self._records_by_id))
        self._open_button.setEnabled(can_open)
        self._transcribe_button.setEnabled(can_transcribe)
        self._translate_to_chinese_button.setEnabled(can_translate_to_chinese)
        self._translate_to_english_button.setEnabled(can_translate_to_english)

        self._open_button.setText(self._tr("history.open"))
        self._transcribe_button.setText(
            self._tr("history.preparing_audio")
            if TaskType.PREPROCESS_AUDIO in active_task_types
            else self._tr("history.transcribing")
            if TaskType.TRANSCRIBE in active_task_types
            else self._tr("history.transcribe")
        )
        translate_label = self._tr("history.translating") if TaskType.TRANSLATE in active_task_types else None
        self._translate_to_chinese_button.setText(translate_label or self._tr("history.translate_to_chinese"))
        self._translate_to_english_button.setText(translate_label or self._tr("history.translate_to_english"))
        self._status_hint.setText(self._build_status_hint(record, active_task_types))

    def _build_status_hint(self, record: Record | None, active_task_types: set[TaskType]) -> str:
        if record is None:
            return self._tr("history.hint.select_record")
        if TaskType.PREPROCESS_AUDIO in active_task_types:
            return self._tr("history.hint.preprocessing_running")
        if TaskType.TRANSCRIBE in active_task_types:
            return self._tr("history.hint.transcription_running")
        if TaskType.TRANSLATE in active_task_types:
            return self._tr("history.hint.translation_running")
        if record.processed_audio_path is None:
            return self._tr("history.hint.preprocess_required")
        if not record.has_transcript:
            return self._tr("history.hint.transcription_required")
        return self._tr("history.hint.ready")

    def _format_record(self, record: Record) -> str:
        flags = []
        if record.has_transcript:
            flags.append(self._tr("history.flag.transcript"))
        if record.has_translation:
            flags.append(self._tr("history.flag.translation"))
        if record.has_summary:
            flags.append(self._tr("history.flag.summary"))
        status = ", ".join(flags) if flags else self._record_status_label(record.status.value)
        created_at = record.created_at.strftime("%Y-%m-%d %H:%M")
        return f"{record.title}\n{created_at} | {status}"

    def _retranslate_ui(self) -> None:
        self._title_label.setText(self._tr("history.title"))
        self._clear_button.setText(self._tr("history.clear"))
        self._refresh_button.setText(self._tr("history.refresh"))

    def _tr(self, key: str, **kwargs: object) -> str:
        return translate(self._language, key, **kwargs)

    def _record_status_label(self, status: str) -> str:
        key = f"record.status.{status}"
        return self._tr(key) if key in self._known_status_keys() else status

    @staticmethod
    def _known_status_keys() -> set[str]:
        return {
            "record.status.new",
            "record.status.preprocessing",
            "record.status.transcribing",
            "record.status.ready",
            "record.status.failed",
        }
