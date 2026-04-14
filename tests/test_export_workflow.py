from __future__ import annotations

import pytest

from meeting_note.core.contracts import (
    Language,
    TranscriptDocument,
    TranscriptSegment,
    TranslationDocument,
    TranslationMode,
)
from meeting_note.core.export_service import ExportService
from meeting_note.core.export_workflow import ExportWorkflow
from meeting_note.data.document_store import SummaryStore, TranscriptStore, TranslationStore
from meeting_note.infra.paths import AppPaths


def build_workflow(paths: AppPaths) -> ExportWorkflow:
    return ExportWorkflow(
        paths=paths,
        export_service=ExportService(),
        transcript_store=TranscriptStore(paths),
        translation_store=TranslationStore(paths),
        summary_store=SummaryStore(paths),
    )


def save_sample_transcript(paths: AppPaths, record_id: str = "rec-1") -> None:
    TranscriptStore(paths).save(
        TranscriptDocument(
            record_id=record_id,
            language=Language.ENGLISH,
            segments=[TranscriptSegment(id="seg-1", text="Hello team", start_time=1, end_time=2, speaker_id="S1")],
        )
    )


def save_sample_translation(paths: AppPaths, record_id: str = "rec-1") -> None:
    TranslationStore(paths).save(
        TranslationDocument(
            record_id=record_id,
            source_language=Language.ENGLISH,
            target_language=Language.CHINESE,
            mode=TranslationMode.STANDARD,
            translated_text="Full translated text.",
            bilingual_text="Source text\n\nTranslation text",
        )
    )


def test_export_transcript_writes_to_record_exports_dir(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    save_sample_transcript(paths)

    output_path = build_workflow(paths).export_transcript("rec-1")

    assert output_path == paths.exports_dir("rec-1") / "transcript.txt"
    assert output_path.read_text(encoding="utf-8") == "[00:00:01 - 00:00:02] S1: Hello team"


def test_export_translation_markdown_uses_full_translation(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    save_sample_translation(paths)

    output_path = build_workflow(paths).export_translation("rec-1", "markdown")

    assert output_path == paths.exports_dir("rec-1") / "translation.md"
    assert output_path.read_text(encoding="utf-8") == "# Translation\n\nFull translated text.\n"


def test_export_bilingual_defaults_to_markdown(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    save_sample_translation(paths)

    output_path = build_workflow(paths).export_bilingual("rec-1")

    assert output_path == paths.exports_dir("rec-1") / "bilingual.md"
    assert output_path.read_text(encoding="utf-8") == "# Bilingual Transcript\n\nSource text\n\nTranslation text\n"


def test_export_summary_markdown(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    SummaryStore(paths).save("rec-1", "Meeting summary")

    output_path = build_workflow(paths).export_summary("rec-1")

    assert output_path == paths.exports_dir("rec-1") / "summary.md"
    assert output_path.read_text(encoding="utf-8") == "# Summary\n\nMeeting summary\n"


def test_export_srt_uses_transcript_segments(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    save_sample_transcript(paths)

    output_path = build_workflow(paths).export_srt("rec-1")

    assert output_path == paths.exports_dir("rec-1") / "subtitles.srt"
    assert "00:00:01,000 --> 00:00:02,000" in output_path.read_text(encoding="utf-8")


def test_export_transcript_requires_existing_transcript(tmp_path):
    workflow = build_workflow(AppPaths.from_project_root(tmp_path))

    with pytest.raises(ValueError, match="Transcript is not available"):
        workflow.export_transcript("missing")


def test_export_translation_requires_existing_translation(tmp_path):
    workflow = build_workflow(AppPaths.from_project_root(tmp_path))

    with pytest.raises(ValueError, match="Translation is not available"):
        workflow.export_translation("missing")


def test_export_summary_requires_existing_summary(tmp_path):
    workflow = build_workflow(AppPaths.from_project_root(tmp_path))

    with pytest.raises(ValueError, match="Summary is not available"):
        workflow.export_summary("missing")


def test_export_rejects_unsupported_format(tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    save_sample_transcript(paths)

    with pytest.raises(ValueError, match="Unsupported export format"):
        build_workflow(paths).export_transcript("rec-1", "html")
