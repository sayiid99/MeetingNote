from __future__ import annotations

from pathlib import Path
from typing import Protocol

from meeting_note.core.audio_processor import AudioProcessingResult
from meeting_note.data.models import Record, RecordStatus
from meeting_note.data.repositories import RecordRepository
from meeting_note.infra.paths import AppPaths


class AudioPreprocessor(Protocol):
    def preprocess(self, input_path: Path, output_path: Path) -> AudioProcessingResult:
        ...


class PreprocessingService:
    def __init__(
        self,
        paths: AppPaths,
        record_repository: RecordRepository,
        audio_preprocessor: AudioPreprocessor,
    ):
        self._paths = paths
        self._record_repository = record_repository
        self._audio_preprocessor = audio_preprocessor

    def prepare_record(self, record: Record) -> Path:
        if record.original_file_path is None:
            raise ValueError(f"Record has no source media file: {record.id}")

        record_dir = self._paths.record_dir(record.id)
        record_dir.mkdir(parents=True, exist_ok=True)
        self._record_repository.update_status(record.id, RecordStatus.PREPROCESSING)
        return self._paths.processed_audio_path(record.id)

    def execute_preprocessing(self, record: Record, output_path: Path) -> Path:
        if record.original_file_path is None:
            raise ValueError(f"Record has no source media file: {record.id}")
        result = self._audio_preprocessor.preprocess(record.original_file_path, output_path)
        return result.output_path

    def preprocess_record(self, record: Record) -> Path:
        output_path = self.prepare_record(record)
        try:
            processed_path = self.execute_preprocessing(record, output_path)
        except Exception:
            self._record_repository.update_status(record.id, RecordStatus.FAILED)
            raise

        self.mark_preprocessed(record.id, processed_path)
        return processed_path

    def mark_preprocessed(self, record_id: str, output_path: Path) -> None:
        self._record_repository.mark_preprocessed(record_id, output_path)

    def mark_failed(self, record_id: str) -> None:
        self._record_repository.update_status(record_id, RecordStatus.FAILED)
