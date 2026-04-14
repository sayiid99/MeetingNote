from __future__ import annotations

from meeting_note.core.asr_service import ASRService
from meeting_note.core.contracts import Language, TranscriptDocument
from meeting_note.core.language_detection import detect_primary_language
from meeting_note.data.document_store import TranscriptStore
from meeting_note.data.models import Record, RecordStatus
from meeting_note.data.repositories import RecordRepository


class TranscriptionService:
    def __init__(
        self,
        asr_service: ASRService,
        transcript_store: TranscriptStore,
        record_repository: RecordRepository,
    ):
        self._asr_service = asr_service
        self._transcript_store = transcript_store
        self._record_repository = record_repository

    def transcribe_record(self, record: Record, source_language: Language = Language.AUTO) -> TranscriptDocument:
        if record.processed_audio_path is None:
            raise ValueError(f"Record has no processed audio file: {record.id}")

        self._record_repository.update_status(record.id, RecordStatus.TRANSCRIBING)
        try:
            transcript = self._asr_service.transcribe(record.processed_audio_path, source_language)
        except Exception:
            self._record_repository.update_status(record.id, RecordStatus.FAILED)
            raise

        detected_language = self.resolve_transcript_language(transcript, requested_language=source_language)
        transcript = TranscriptDocument(
            record_id=record.id,
            language=detected_language,
            segments=transcript.segments,
        )
        self._transcript_store.save(transcript)
        self._record_repository.mark_transcript_ready(
            record_id=record.id,
            processed_audio_path=record.processed_audio_path,
            source_language=transcript.language.value,
            has_speakers=any(segment.speaker_id for segment in transcript.segments),
        )
        return transcript

    @classmethod
    def resolve_transcript_language(
        cls,
        transcript: TranscriptDocument,
        requested_language: Language = Language.AUTO,
    ) -> Language:
        if requested_language in {Language.CHINESE, Language.ENGLISH}:
            return requested_language
        if transcript.language in {Language.CHINESE, Language.ENGLISH}:
            return transcript.language
        return detect_primary_language(transcript.full_text)
