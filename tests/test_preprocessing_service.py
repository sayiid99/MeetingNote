from __future__ import annotations

from pathlib import Path

import pytest

from meeting_note.core.audio_processor import AudioProcessingResult
from meeting_note.core.preprocessing_service import PreprocessingService
from meeting_note.data.database import initialize_database
from meeting_note.data.models import RecordStatus
from meeting_note.data.repositories import RecordRepository
from meeting_note.infra.paths import AppPaths


class FakeAudioPreprocessor:
    def preprocess(self, input_path: Path, output_path: Path) -> AudioProcessingResult:
        output_path.write_bytes(b"processed audio content")
        return AudioProcessingResult(source_path=input_path, output_path=output_path)


class FailingAudioPreprocessor:
    def preprocess(self, input_path: Path, output_path: Path) -> AudioProcessingResult:
        raise RuntimeError("ffmpeg failed")


def test_preprocessing_service_writes_to_record_directory_and_marks_ready(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    source_file = tmp_path / "meeting.mp4"
    source_file.write_bytes(b"fake")
    record = repository.create_record("meeting", source_file)
    service = PreprocessingService(paths, repository, FakeAudioPreprocessor())

    output_path = service.preprocess_record(record)
    updated_record = repository.get_record(record.id)

    assert output_path == paths.processed_audio_path(record.id)
    assert output_path.exists()
    assert updated_record is not None
    assert updated_record.status == RecordStatus.READY
    assert updated_record.processed_audio_path == output_path


def test_preprocessing_service_marks_record_failed_when_preprocessor_fails(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    source_file = tmp_path / "meeting.wav"
    source_file.write_bytes(b"fake")
    record = repository.create_record("meeting", source_file)
    service = PreprocessingService(paths, repository, FailingAudioPreprocessor())

    with pytest.raises(RuntimeError, match="ffmpeg failed"):
        service.preprocess_record(record)

    updated_record = repository.get_record(record.id)
    assert updated_record is not None
    assert updated_record.status == RecordStatus.FAILED
