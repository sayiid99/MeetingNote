from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from meeting_note.data.models import TaskRecord
from meeting_note.ui.i18n import DEFAULT_UI_LANGUAGE, normalize_language, translate


class TasksPage(QWidget):
    def __init__(self, language: str = DEFAULT_UI_LANGUAGE):
        super().__init__()
        self._language = normalize_language(language)
        self._tasks: list[TaskRecord] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._title_label = QLabel()
        self._title_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(self._title_label)

        self._hint_label = QLabel()
        layout.addWidget(self._hint_label)

        self._list = QListWidget()
        layout.addWidget(self._list)

        action_row = QHBoxLayout()
        self._clear_button = QPushButton()
        self._refresh_button = QPushButton()
        action_row.addWidget(self._clear_button)
        action_row.addStretch(1)
        action_row.addWidget(self._refresh_button)
        layout.addLayout(action_row)
        self._retranslate_ui()

    @property
    def refresh_button(self) -> QPushButton:
        return self._refresh_button

    @property
    def clear_button(self) -> QPushButton:
        return self._clear_button

    def set_tasks(self, tasks: list[TaskRecord]) -> None:
        self._tasks = list(tasks)
        self._list.clear()
        for task in tasks:
            self._list.addItem(QListWidgetItem(self._format_task(task)))
        self._clear_button.setEnabled(bool(tasks))

    def count(self) -> int:
        return self._list.count()

    def task_text(self, row: int) -> str:
        item = self._list.item(row)
        return item.text() if item else ""

    def _format_task(self, task: TaskRecord) -> str:
        record_part = (
            self._tr("task.record_part", record_id=task.record_id) if task.record_id else self._tr("task.no_record")
        )
        message = task.message or task.error or ""
        task_type = self._task_type_label(task.task_type.value)
        status = self._task_status_label(task.status.value)
        return f"{task_type} | {status} | {task.progress}% | {record_part}\n{message}"

    def set_language(self, language: str) -> None:
        self._language = normalize_language(language)
        self._retranslate_ui()
        self.set_tasks(self._tasks)

    def _retranslate_ui(self) -> None:
        self._title_label.setText(self._tr("tasks.title"))
        self._hint_label.setText(self._tr("tasks.hint"))
        self._clear_button.setText(self._tr("tasks.clear"))
        self._refresh_button.setText(self._tr("tasks.refresh"))

    def _tr(self, key: str, **kwargs: object) -> str:
        return translate(self._language, key, **kwargs)

    def _task_type_label(self, task_type: str) -> str:
        return self._tr(f"tasks.type.{task_type}") if f"tasks.type.{task_type}" in self._known_keys() else task_type

    def _task_status_label(self, status: str) -> str:
        return self._tr(f"tasks.status.{status}") if f"tasks.status.{status}" in self._known_keys() else status

    @staticmethod
    def _known_keys() -> set[str]:
        return {
            "tasks.type.preprocess_audio",
            "tasks.type.transcribe",
            "tasks.type.translate",
            "tasks.type.summarize",
            "tasks.status.queued",
            "tasks.status.running",
            "tasks.status.completed",
            "tasks.status.failed",
            "tasks.status.cancelled",
        }
