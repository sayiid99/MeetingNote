from __future__ import annotations

from meeting_note.data.database import initialize_database
from meeting_note.data.models import TaskStatus, TaskType
from meeting_note.data.repositories import TaskRepository


def test_task_repository_tracks_task_lifecycle(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    repo = TaskRepository(database_path)

    task = repo.create_task(TaskType.PREPROCESS_AUDIO, record_id="rec-1")
    repo.mark_running(task.id, "Working")
    running = repo.get_task(task.id)
    assert running is not None
    assert running.status == TaskStatus.RUNNING
    assert running.progress == 1
    assert running.message == "Working"
    assert running.started_at is not None

    repo.mark_completed(task.id, "Done")
    completed = repo.get_task(task.id)
    assert completed is not None
    assert completed.status == TaskStatus.COMPLETED
    assert completed.progress == 100
    assert completed.finished_at is not None


def test_task_repository_marks_failure(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    repo = TaskRepository(database_path)

    task = repo.create_task(TaskType.TRANSLATE)
    repo.mark_failed(task.id, "broken")

    failed = repo.get_task(task.id)
    assert failed is not None
    assert failed.status == TaskStatus.FAILED
    assert failed.error == "broken"
    assert failed.finished_at is not None


def test_task_repository_lists_tasks_and_filters_by_record(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    repo = TaskRepository(database_path)
    first = repo.create_task(TaskType.TRANSCRIBE, record_id="rec-1")
    second = repo.create_task(TaskType.TRANSLATE, record_id="rec-2")
    repo.mark_running(first.id, "Transcribing")
    repo.mark_completed(second.id, "Translated")

    all_tasks = repo.list_tasks()
    record_tasks = repo.list_tasks("rec-1")

    assert {task.id for task in all_tasks} == {first.id, second.id}
    assert [task.id for task in record_tasks] == [first.id]


def test_task_repository_lists_active_tasks_and_finds_active_task(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    repo = TaskRepository(database_path)
    first = repo.create_task(TaskType.TRANSCRIBE, record_id="rec-1")
    second = repo.create_task(TaskType.TRANSLATE, record_id="rec-1")
    third = repo.create_task(TaskType.TRANSLATE, record_id="rec-2")
    repo.mark_running(first.id, "Transcribing")
    repo.mark_completed(second.id, "Done")
    repo.mark_running(third.id, "Translating")

    active_tasks = repo.list_active_tasks(record_id="rec-1")
    active_translate = repo.find_active_task("rec-2", TaskType.TRANSLATE)

    assert [task.id for task in active_tasks] == [first.id]
    assert active_translate is not None
    assert active_translate.id == third.id


def test_task_repository_clears_finished_tasks_only(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    repo = TaskRepository(database_path)

    running = repo.create_task(TaskType.TRANSCRIBE, record_id="rec-1")
    completed = repo.create_task(TaskType.TRANSLATE, record_id="rec-1")
    failed = repo.create_task(TaskType.PREPROCESS_AUDIO, record_id="rec-2")
    repo.mark_running(running.id, "Running")
    repo.mark_completed(completed.id, "Done")
    repo.mark_failed(failed.id, "Failed")

    cleared = repo.clear_finished_tasks()
    remaining = repo.list_tasks()

    assert cleared == 2
    assert [task.id for task in remaining] == [running.id]


def test_task_repository_deletes_tasks_for_selected_records(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    repo = TaskRepository(database_path)

    keep = repo.create_task(TaskType.TRANSCRIBE, record_id="rec-keep")
    repo.create_task(TaskType.TRANSLATE, record_id="rec-1")
    repo.create_task(TaskType.PREPROCESS_AUDIO, record_id="rec-2")

    deleted = repo.delete_tasks_for_records(["rec-1", "rec-2"])
    remaining = repo.list_tasks()

    assert deleted == 2
    assert [task.id for task in remaining] == [keep.id]
