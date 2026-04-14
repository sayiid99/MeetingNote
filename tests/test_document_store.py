from __future__ import annotations

from meeting_note.core.contracts import (
    Language,
    TranscriptDocument,
    TranscriptSegment,
    TranslationDocument,
    TranslationMode,
)
from meeting_note.data.document_store import SummaryStore, TranscriptStore, TranslationStore
from meeting_note.infra.paths import AppPaths


def test_transcript_store_saves_and_loads_transcript(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    store = TranscriptStore(paths)
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.CHINESE,
        segments=[
            TranscriptSegment(
                id="seg-1",
                text="大家好",
                start_time=0.0,
                end_time=1.5,
                speaker_id="S1",
                is_edited=True,
            )
        ],
    )

    path = store.save(transcript)
    loaded = store.load("rec-1")

    assert path.exists()
    assert loaded == transcript


def test_transcript_store_returns_none_for_missing_transcript(tmp_path):
    store = TranscriptStore(AppPaths.from_project_root(tmp_path))

    assert store.load("missing") is None


def test_translation_store_saves_and_loads_translation(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    store = TranslationStore(paths)
    translation = TranslationDocument(
        record_id="rec-1",
        source_language=Language.CHINESE,
        target_language=Language.ENGLISH,
        mode=TranslationMode.BUSINESS,
        translated_text="Hello everyone.",
        bilingual_text="source and translation",
    )

    path = store.save(translation)
    loaded = store.load("rec-1")

    assert path.exists()
    assert loaded == translation


def test_translation_store_returns_none_for_missing_translation(tmp_path):
    store = TranslationStore(AppPaths.from_project_root(tmp_path))

    assert store.load("missing") is None


def test_summary_store_saves_and_loads_summary(tmp_path):
    store = SummaryStore(AppPaths.from_project_root(tmp_path))

    path = store.save("rec-1", "## Overview\nSummary")

    assert path.exists()
    assert store.load("rec-1") == "## Overview\nSummary"


def test_summary_store_returns_none_for_missing_summary(tmp_path):
    store = SummaryStore(AppPaths.from_project_root(tmp_path))

    assert store.load("missing") is None
