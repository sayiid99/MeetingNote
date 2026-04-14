from __future__ import annotations

from meeting_note.core.summary_service import SummaryService
from meeting_note.data.document_store import SummaryStore, TranscriptStore
from meeting_note.data.repositories import RecordRepository


class SummaryWorkflow:
    def __init__(
        self,
        summary_service: SummaryService,
        transcript_store: TranscriptStore,
        summary_store: SummaryStore,
        record_repository: RecordRepository,
    ):
        self._summary_service = summary_service
        self._transcript_store = transcript_store
        self._summary_store = summary_store
        self._record_repository = record_repository

    def summarize_record(self, record_id: str) -> str:
        transcript = self._transcript_store.load(record_id)
        if transcript is None:
            raise ValueError(f"Transcript is not available for record: {record_id}")

        summary_text = self._summary_service.summarize(transcript)
        self._summary_store.save(record_id, summary_text)
        self._record_repository.mark_summary_ready(record_id)
        return summary_text
