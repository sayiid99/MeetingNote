from __future__ import annotations

import pytest

from meeting_note.core.contracts import Language, TranscriptDocument, TranscriptSegment, TranslationMode
from meeting_note.core.translation_service import TranslationService
from meeting_note.core.translation_workflow import TranslationWorkflow
from meeting_note.data.database import initialize_database
from meeting_note.data.document_store import TranscriptStore, TranslationStore
from meeting_note.data.repositories import RecordRepository
from meeting_note.infra.paths import AppPaths


class StaticLLMProvider:
    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        return "Full English translation."


def test_translation_workflow_saves_translation_and_marks_record(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.CHINESE,
            segments=[TranscriptSegment(id="seg-1", text="完整中文原文", start_time=0, end_time=1)],
        )
    )
    workflow = TranslationWorkflow(
        translation_service=TranslationService(StaticLLMProvider()),
        transcript_store=transcript_store,
        translation_store=translation_store,
        record_repository=repository,
    )

    translation = workflow.translate_record(record.id, Language.ENGLISH, TranslationMode.STANDARD)
    updated_record = repository.get_record(record.id)
    loaded_translation = translation_store.load(record.id)

    assert translation.translated_text == "Full English translation."
    assert loaded_translation == translation
    assert updated_record is not None
    assert updated_record.has_translation is True


def test_translation_workflow_requires_existing_transcript(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    workflow = TranslationWorkflow(
        translation_service=TranslationService(StaticLLMProvider()),
        transcript_store=TranscriptStore(paths),
        translation_store=TranslationStore(paths),
        record_repository=repository,
    )

    with pytest.raises(ValueError, match="Transcript is not available"):
        workflow.translate_record("missing", Language.ENGLISH)
