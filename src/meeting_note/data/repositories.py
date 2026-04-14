from __future__ import annotations

from collections.abc import Mapping
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from meeting_note.data.models import (
    LocalModel,
    ModelProvider,
    ModelType,
    Record,
    RecordStatus,
    TaskRecord,
    TaskStatus,
    TaskType,
    now_utc,
)


class RecordRepository:
    def __init__(self, database_path: Path):
        self._database_path = database_path

    def create_record(self, title: str, original_file_path: Path | None = None) -> Record:
        created_at = now_utc()
        record = Record(
            id=self._build_record_id(created_at),
            title=title,
            original_file_path=original_file_path,
            status=RecordStatus.NEW,
            created_at=created_at,
            updated_at=created_at,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO records (
                  id, title, original_file_path, processed_audio_path, source_language,
                  duration_seconds, status, has_transcript, has_translation, has_summary,
                  has_speakers, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._record_to_row(record),
            )
        return record

    def get_record(self, record_id: str) -> Record | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, title, original_file_path, processed_audio_path, source_language,
                       duration_seconds, status, has_transcript, has_translation, has_summary,
                       has_speakers, created_at, updated_at
                FROM records
                WHERE id = ?
                """,
                (record_id,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def list_records(self) -> list[Record]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, title, original_file_path, processed_audio_path, source_language,
                       duration_seconds, status, has_transcript, has_translation, has_summary,
                       has_speakers, created_at, updated_at
                FROM records
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def clear_all_records(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id FROM records").fetchall()
            record_ids = [str(row[0]) for row in rows]
            if not record_ids:
                return []
            conn.execute("DELETE FROM records")
        return record_ids

    def update_status(self, record_id: str, status: RecordStatus) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE records SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, now_utc().isoformat(), record_id),
            )

    def mark_preprocessed(self, record_id: str, processed_audio_path: Path) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE records
                SET processed_audio_path = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    str(processed_audio_path),
                    RecordStatus.READY.value,
                    now_utc().isoformat(),
                    record_id,
                ),
            )

    def mark_transcript_ready(
        self,
        record_id: str,
        processed_audio_path: Path,
        source_language: str,
        has_speakers: bool,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE records
                SET processed_audio_path = ?, source_language = ?, status = ?,
                    has_transcript = 1, has_speakers = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    str(processed_audio_path),
                    source_language,
                    RecordStatus.READY.value,
                    int(has_speakers),
                    now_utc().isoformat(),
                    record_id,
                ),
            )

    def mark_translation_ready(self, record_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE records SET has_translation = 1, updated_at = ? WHERE id = ?",
                (now_utc().isoformat(), record_id),
            )

    def mark_summary_ready(self, record_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE records SET has_summary = 1, updated_at = ? WHERE id = ?",
                (now_utc().isoformat(), record_id),
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    @staticmethod
    def _build_record_id(created_at: datetime) -> str:
        timestamp = created_at.strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{uuid4().hex[:8]}"

    @staticmethod
    def _record_to_row(record: Record) -> tuple[object, ...]:
        return (
            record.id,
            record.title,
            str(record.original_file_path) if record.original_file_path else None,
            str(record.processed_audio_path) if record.processed_audio_path else None,
            record.source_language,
            record.duration_seconds,
            record.status.value,
            int(record.has_transcript),
            int(record.has_translation),
            int(record.has_summary),
            int(record.has_speakers),
            record.created_at.isoformat(),
            record.updated_at.isoformat(),
        )

    @staticmethod
    def _row_to_record(row: sqlite3.Row | tuple[object, ...]) -> Record:
        return Record(
            id=str(row[0]),
            title=str(row[1]),
            original_file_path=Path(str(row[2])) if row[2] else None,
            processed_audio_path=Path(str(row[3])) if row[3] else None,
            source_language=str(row[4]) if row[4] else None,
            duration_seconds=float(row[5] or 0),
            status=RecordStatus(str(row[6])),
            has_transcript=bool(row[7]),
            has_translation=bool(row[8]),
            has_summary=bool(row[9]),
            has_speakers=bool(row[10]),
            created_at=now_utc().fromisoformat(str(row[11])),
            updated_at=now_utc().fromisoformat(str(row[12])),
        )


class ModelRepository:
    def __init__(self, database_path: Path):
        self._database_path = database_path

    def replace_all(self, models: list[LocalModel]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM models")
            conn.executemany(
                """
                INSERT INTO models (
                  id, name, path, model_type, provider, file_size, quantization,
                  context_length, status, created_at, last_checked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [self._model_to_row(model) for model in models],
            )

    def upsert_model(self, model: LocalModel) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO models (
                  id, name, path, model_type, provider, file_size, quantization,
                  context_length, status, created_at, last_checked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  name = excluded.name,
                  path = excluded.path,
                  model_type = excluded.model_type,
                  provider = excluded.provider,
                  file_size = excluded.file_size,
                  quantization = excluded.quantization,
                  context_length = excluded.context_length,
                  status = excluded.status,
                  last_checked_at = excluded.last_checked_at
                """,
                self._model_to_row(model),
            )

    def list_models(self, model_type: ModelType | None = None) -> list[LocalModel]:
        query = (
            "SELECT id, name, path, model_type, provider, file_size, quantization, "
            "context_length, status, created_at, last_checked_at FROM models"
        )
        params: tuple[object, ...] = ()
        if model_type:
            query += " WHERE model_type = ?"
            params = (model_type.value,)
        query += " ORDER BY name ASC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_model(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    @staticmethod
    def _model_to_row(model: LocalModel) -> tuple[object, ...]:
        return (
            model.id,
            model.name,
            str(model.path),
            model.model_type.value,
            model.provider.value,
            model.file_size,
            model.quantization,
            model.context_length,
            model.status,
            model.created_at.isoformat(),
            model.last_checked_at.isoformat() if model.last_checked_at else None,
        )

    @staticmethod
    def _row_to_model(row: sqlite3.Row | tuple[object, ...]) -> LocalModel:
        return LocalModel(
            id=str(row[0]),
            name=str(row[1]),
            path=Path(str(row[2])),
            model_type=ModelType(str(row[3])),
            provider=ModelProvider(str(row[4])),
            file_size=int(row[5] or 0),
            quantization=str(row[6]) if row[6] else None,
            context_length=int(row[7]) if row[7] else None,
            status=str(row[8]),
            created_at=now_utc().fromisoformat(str(row[9])),
            last_checked_at=now_utc().fromisoformat(str(row[10])) if row[10] else None,
        )


class TaskRepository:
    ACTIVE_STATUSES = (TaskStatus.QUEUED.value, TaskStatus.RUNNING.value)

    def __init__(self, database_path: Path):
        self._database_path = database_path

    def create_task(self, task_type: TaskType, record_id: str | None = None) -> TaskRecord:
        task = TaskRecord(
            id=str(uuid4()),
            task_type=task_type,
            record_id=record_id,
            status=TaskStatus.QUEUED,
            progress=0,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                  id, record_id, task_type, status, progress, message,
                  started_at, finished_at, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._task_to_row(task),
            )
        return task

    def get_task(self, task_id: str) -> TaskRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, record_id, task_type, status, progress, message,
                       started_at, finished_at, error
                FROM tasks
                WHERE id = ?
                """,
                (task_id,),
            ).fetchone()
        return self._row_to_task(row) if row else None

    def list_tasks(self, record_id: str | None = None) -> list[TaskRecord]:
        query = """
            SELECT id, record_id, task_type, status, progress, message,
                   started_at, finished_at, error
            FROM tasks
        """
        params: tuple[object, ...] = ()
        if record_id is not None:
            query += " WHERE record_id = ?"
            params = (record_id,)
        query += " ORDER BY COALESCE(started_at, finished_at, id) DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_task(row) for row in rows]

    def list_active_tasks(
        self,
        *,
        record_id: str | None = None,
        task_type: TaskType | None = None,
    ) -> list[TaskRecord]:
        query = """
            SELECT id, record_id, task_type, status, progress, message,
                   started_at, finished_at, error
            FROM tasks
            WHERE status IN (?, ?)
        """
        params: list[object] = [*self.ACTIVE_STATUSES]
        if record_id is not None:
            query += " AND record_id = ?"
            params.append(record_id)
        if task_type is not None:
            query += " AND task_type = ?"
            params.append(task_type.value)
        query += " ORDER BY COALESCE(started_at, finished_at, id) DESC"
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_task(row) for row in rows]

    def find_active_task(self, record_id: str, task_type: TaskType) -> TaskRecord | None:
        active_tasks = self.list_active_tasks(record_id=record_id, task_type=task_type)
        return active_tasks[0] if active_tasks else None

    def clear_finished_tasks(self) -> int:
        """删除已结束任务（保留 queued/running 任务）。"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM tasks
                WHERE status NOT IN (?, ?)
                """,
                self.ACTIVE_STATUSES,
            )
            return int(cursor.rowcount or 0)

    def delete_tasks_for_records(self, record_ids: list[str]) -> int:
        if not record_ids:
            return 0
        placeholders = ",".join("?" for _ in record_ids)
        with self._connect() as conn:
            cursor = conn.execute(
                f"""
                DELETE FROM tasks
                WHERE record_id IN ({placeholders})
                """,
                tuple(record_ids),
            )
            return int(cursor.rowcount or 0)

    def mark_running(self, task_id: str, message: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, progress = ?, message = ?, started_at = ?
                WHERE id = ?
                """,
                (TaskStatus.RUNNING.value, 1, message, now_utc().isoformat(), task_id),
            )

    def mark_completed(self, task_id: str, message: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, progress = ?, message = ?, finished_at = ?
                WHERE id = ?
                """,
                (TaskStatus.COMPLETED.value, 100, message, now_utc().isoformat(), task_id),
            )

    def mark_failed(self, task_id: str, error: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, error = ?, finished_at = ?
                WHERE id = ?
                """,
                (TaskStatus.FAILED.value, error, now_utc().isoformat(), task_id),
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    @staticmethod
    def _task_to_row(task: TaskRecord) -> tuple[object, ...]:
        return (
            task.id,
            task.record_id,
            task.task_type.value,
            task.status.value,
            task.progress,
            task.message,
            task.started_at.isoformat() if task.started_at else None,
            task.finished_at.isoformat() if task.finished_at else None,
            task.error,
        )

    @staticmethod
    def _row_to_task(row: sqlite3.Row | tuple[object, ...]) -> TaskRecord:
        return TaskRecord(
            id=str(row[0]),
            record_id=str(row[1]) if row[1] else None,
            task_type=TaskType(str(row[2])),
            status=TaskStatus(str(row[3])),
            progress=int(row[4] or 0),
            message=str(row[5]) if row[5] else None,
            started_at=now_utc().fromisoformat(str(row[6])) if row[6] else None,
            finished_at=now_utc().fromisoformat(str(row[7])) if row[7] else None,
            error=str(row[8]) if row[8] else None,
        )


class SettingsRepository:
    def __init__(self, database_path: Path):
        self._database_path = database_path

    def get(self, key: str, default: str | None = None) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return str(row[0]) if row[0] is not None else default

    def get_int(self, key: str, default: int) -> int:
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def get_bool(self, key: str, default: bool) -> bool:
        value = self.get(key)
        if value is None:
            return default
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return default

    def set(self, key: str, value: str | int | float | bool | None) -> None:
        if value is None:
            self.delete(key)
            return
        stored_value = self._serialize_value(value)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, stored_value),
            )

    def set_many(self, settings: Mapping[str, str | int | float | bool | None]) -> None:
        for key, value in settings.items():
            self.set(key, value)

    def delete(self, key: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))

    def all(self) -> dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM app_settings ORDER BY key ASC").fetchall()
        return {str(row[0]): str(row[1]) for row in rows if row[1] is not None}

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    @staticmethod
    def _serialize_value(value: str | int | float | bool) -> str:
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)
