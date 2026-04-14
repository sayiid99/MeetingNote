from __future__ import annotations

from meeting_note.core.contracts import Language, TranslationDocument, TranslationMode
from meeting_note.core.translation_service import TranslationService
from meeting_note.data.document_store import TranscriptStore, TranslationStore
from meeting_note.data.repositories import RecordRepository


class TranslationWorkflow:
    def __init__(
        self,
        translation_service: TranslationService,
        transcript_store: TranscriptStore,
        translation_store: TranslationStore,
        record_repository: RecordRepository,
    ):
        self._translation_service = translation_service
        self._transcript_store = transcript_store
        self._translation_store = translation_store
        self._record_repository = record_repository

    def translate_record(
        self,
        record_id: str,
        target_language: Language,
        mode: TranslationMode = TranslationMode.STANDARD,
    ) -> TranslationDocument:
        transcript = self._transcript_store.load(record_id)
        if transcript is None:
            raise ValueError(f"Transcript is not available for record: {record_id}")

        translation = self._translation_service.translate_document(transcript, target_language, mode)
        self._translation_store.save(translation)
        self._record_repository.mark_translation_ready(record_id)
        return translation
