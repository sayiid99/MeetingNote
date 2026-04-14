from __future__ import annotations

import pytest

from meeting_note.core.contracts import Language, TranscriptDocument, TranscriptSegment
from meeting_note.core.summary_service import SummaryService
from meeting_note.core.summary_workflow import SummaryWorkflow
from meeting_note.data.database import initialize_database
from meeting_note.data.document_store import SummaryStore, TranscriptStore
from meeting_note.data.repositories import RecordRepository
from meeting_note.infra.paths import AppPaths


class StaticLLMProvider:
    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        return "## Overview\nThe meeting discussed delivery."


def test_summary_workflow_saves_summary_and_marks_record(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    summary_store = SummaryStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.ENGLISH,
            segments=[TranscriptSegment(id="seg-1", text="We discussed delivery.", start_time=0, end_time=1)],
        )
    )
    workflow = SummaryWorkflow(
        summary_service=SummaryService(StaticLLMProvider()),
        transcript_store=transcript_store,
        summary_store=summary_store,
        record_repository=repository,
    )

    summary = workflow.summarize_record(record.id)
    updated_record = repository.get_record(record.id)

    assert summary_store.load(record.id) == summary
    assert updated_record is not None
    assert updated_record.has_summary is True


def test_summary_workflow_requires_existing_transcript(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    workflow = SummaryWorkflow(
        summary_service=SummaryService(StaticLLMProvider()),
        transcript_store=TranscriptStore(paths),
        summary_store=SummaryStore(paths),
        record_repository=RecordRepository(paths.database_path),
    )

    with pytest.raises(ValueError, match="Transcript is not available"):
        workflow.summarize_record("missing")
