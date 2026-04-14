from __future__ import annotations

from PySide6.QtCore import QEventLoop, QTimer

from meeting_note.core.task_runner import TaskRunner


def wait_until(condition, timeout_ms: int = 2000):
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: loop.quit() if condition() else None)
    timer.start()
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    timer.stop()


def test_task_runner_emits_success(qt_app):
    runner = TaskRunner()
    results = []
    runner.task_succeeded.connect(lambda task_id, result: results.append((task_id, result)))

    runner.submit("task-1", lambda: "done")
    wait_until(lambda: bool(results))

    assert results == [("task-1", "done")]
    assert runner.active_task_count() == 0


def test_task_runner_emits_failure(qt_app):
    runner = TaskRunner()
    failures = []
    runner.task_failed.connect(lambda task_id, error: failures.append((task_id, error)))

    def fail():
        raise RuntimeError("boom")

    runner.submit("task-1", fail)
    wait_until(lambda: bool(failures))

    assert failures[0][0] == "task-1"
    assert "RuntimeError: boom" in failures[0][1]
    assert runner.active_task_count() == 0
