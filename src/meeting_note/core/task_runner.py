from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class _TaskSignals(QObject):
    succeeded = Signal(str, object)
    failed = Signal(str, str)


class _FunctionTask(QRunnable):
    def __init__(self, task_id: str, callback: Callable[[], Any]):
        super().__init__()
        self._task_id = task_id
        self._callback = callback
        self.signals = _TaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self._callback()
        except Exception:
            self.signals.failed.emit(self._task_id, traceback.format_exc())
            return
        self.signals.succeeded.emit(self._task_id, result)


class TaskRunner(QObject):
    task_succeeded = Signal(str, object)
    task_failed = Signal(str, str)

    def __init__(self, thread_pool: QThreadPool | None = None):
        super().__init__()
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._active_tasks: dict[str, _FunctionTask] = {}

    def submit(self, task_id: str, callback: Callable[[], Any]) -> None:
        task = _FunctionTask(task_id, callback)
        task.setAutoDelete(False)
        task.signals.succeeded.connect(self._on_task_succeeded)
        task.signals.failed.connect(self._on_task_failed)
        self._active_tasks[task_id] = task
        self._thread_pool.start(task)

    def active_task_count(self) -> int:
        return len(self._active_tasks)

    def _on_task_succeeded(self, task_id: str, result: object) -> None:
        self._active_tasks.pop(task_id, None)
        self.task_succeeded.emit(task_id, result)

    def _on_task_failed(self, task_id: str, error: str) -> None:
        self._active_tasks.pop(task_id, None)
        self.task_failed.emit(task_id, error)
