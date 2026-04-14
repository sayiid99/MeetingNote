from __future__ import annotations

from pathlib import Path

import pytest

from meeting_note.core.contracts import Language, TranscriptDocument, TranscriptSegment
from meeting_note.core.transcription_service import TranscriptionService
from meeting_note.data.database import initialize_database
from meeting_note.data.document_store import TranscriptStore
from meeting_note.data.models import RecordStatus
from meeting_note.data.repositories import RecordRepository
from meeting_note.infra.paths import AppPaths


class FakeASRService:
    def transcribe(self, audio_path: Path, source_language: Language) -> TranscriptDocument:
        return TranscriptDocument(
            record_id=audio_path.stem,
            language=Language.CHINESE,
            segments=[
                TranscriptSegment(
                    id="seg-1",
                    text="你好",
                    start_time=0,
                    end_time=1,
                    speaker_id="S1",
                )
            ],
        )


class FailingASRService:
    def transcribe(self, audio_path: Path, source_language: Language) -> TranscriptDocument:
        raise RuntimeError("asr failed")


class AutoLanguageChineseASRService:
    def transcribe(self, audio_path: Path, source_language: Language) -> TranscriptDocument:
        return TranscriptDocument(
            record_id=audio_path.stem,
            language=Language.AUTO,
            segments=[TranscriptSegment(id="seg-1", text="你好世界", start_time=0, end_time=1)],
        )


class AutoLanguageEnglishASRService:
    def transcribe(self, audio_path: Path, source_language: Language) -> TranscriptDocument:
        return TranscriptDocument(
            record_id=audio_path.stem,
            language=Language.AUTO,
            segments=[TranscriptSegment(id="seg-1", text="hello world", start_time=0, end_time=1)],
        )


def test_transcription_service_saves_transcript_and_marks_record_ready(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    processed_audio = paths.processed_audio_path(record.id)
    processed_audio.parent.mkdir(parents=True)
    processed_audio.write_bytes(b"audio")
    repository.mark_preprocessed(record.id, processed_audio)
    ready_record = repository.get_record(record.id)
    assert ready_record is not None
    service = TranscriptionService(FakeASRService(), TranscriptStore(paths), repository)

    transcript = service.transcribe_record(ready_record)
    updated_record = repository.get_record(record.id)

    assert transcript.record_id == record.id
    assert TranscriptStore(paths).load(record.id) == transcript
    assert updated_record is not None
    assert updated_record.status == RecordStatus.READY
    assert updated_record.has_transcript is True
    assert updated_record.has_speakers is True
    assert updated_record.source_language == "zh"


def test_transcription_service_marks_record_failed_on_asr_error(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    processed_audio = paths.processed_audio_path(record.id)
    processed_audio.parent.mkdir(parents=True)
    processed_audio.write_bytes(b"audio")
    repository.mark_preprocessed(record.id, processed_audio)
    ready_record = repository.get_record(record.id)
    assert ready_record is not None
    service = TranscriptionService(FailingASRService(), TranscriptStore(paths), repository)

    with pytest.raises(RuntimeError, match="asr failed"):
        service.transcribe_record(ready_record)

    failed_record = repository.get_record(record.id)
    assert failed_record is not None
    assert failed_record.status == RecordStatus.FAILED


def test_transcription_service_detects_chinese_when_asr_returns_auto_language(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    processed_audio = paths.processed_audio_path(record.id)
    processed_audio.parent.mkdir(parents=True)
    processed_audio.write_bytes(b"audio")
    repository.mark_preprocessed(record.id, processed_audio)
    ready_record = repository.get_record(record.id)
    assert ready_record is not None
    service = TranscriptionService(AutoLanguageChineseASRService(), TranscriptStore(paths), repository)

    transcript = service.transcribe_record(ready_record)
    updated_record = repository.get_record(record.id)

    assert transcript.language == Language.CHINESE
    assert updated_record is not None
    assert updated_record.source_language == "zh"


def test_transcription_service_detects_english_when_asr_returns_auto_language(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    processed_audio = paths.processed_audio_path(record.id)
    processed_audio.parent.mkdir(parents=True)
    processed_audio.write_bytes(b"audio")
    repository.mark_preprocessed(record.id, processed_audio)
    ready_record = repository.get_record(record.id)
    assert ready_record is not None
    service = TranscriptionService(AutoLanguageEnglishASRService(), TranscriptStore(paths), repository)

    transcript = service.transcribe_record(ready_record)
    updated_record = repository.get_record(record.id)

    assert transcript.language == Language.ENGLISH
    assert updated_record is not None
    assert updated_record.source_language == "en"
