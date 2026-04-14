from __future__ import annotations

from meeting_note.core.contracts import (
    Language,
    TranscriptDocument,
    TranscriptSegment,
    TranslationDocument,
    TranslationMode,
)
from meeting_note.core.export_service import ExportService


def test_export_text_writes_utf8_file(tmp_path):
    output_path = tmp_path / "out" / "transcript.txt"

    ExportService().export_text("你好", output_path)

    assert output_path.read_text(encoding="utf-8") == "你好"


def test_export_markdown_adds_title(tmp_path):
    output_path = tmp_path / "summary.md"

    ExportService().export_markdown("Meeting Summary", "Content", output_path)

    assert output_path.read_text(encoding="utf-8") == "# Meeting Summary\n\nContent\n"


def test_export_transcript_txt_uses_formatted_segments(tmp_path):
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.CHINESE,
        segments=[TranscriptSegment(id="1", text="开始", start_time=1, end_time=2, speaker_id="S1")],
    )
    output_path = tmp_path / "transcript.txt"

    ExportService().export_transcript_txt(transcript, output_path)

    assert output_path.read_text(encoding="utf-8") == "[00:00:01 - 00:00:02] S1: 开始"


def test_export_translation_txt_writes_full_translation(tmp_path):
    translation = TranslationDocument(
        record_id="rec-1",
        source_language=Language.CHINESE,
        target_language=Language.ENGLISH,
        mode=TranslationMode.STANDARD,
        translated_text="Full translation",
    )
    output_path = tmp_path / "translation.txt"

    ExportService().export_translation_txt(translation, output_path)

    assert output_path.read_text(encoding="utf-8") == "Full translation"


def test_export_srt_formats_subtitles(tmp_path):
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.ENGLISH,
        segments=[
            TranscriptSegment(id="1", text="Hello", start_time=1.234, end_time=2.5, speaker_id="S1"),
            TranscriptSegment(id="2", text="World", start_time=2.5, end_time=4.0),
        ],
    )
    output_path = tmp_path / "subtitle.srt"

    ExportService().export_srt(transcript, output_path)

    assert output_path.read_text(encoding="utf-8") == (
        "1\n"
        "00:00:01,234 --> 00:00:02,500\n"
        "[S1] Hello\n\n"
        "2\n"
        "00:00:02,500 --> 00:00:04,000\n"
        "World"
    )


def test_format_srt_timestamp_clamps_negative_values():
    assert ExportService.format_srt_timestamp(-1) == "00:00:00,000"


def test_export_srt_backfills_missing_segment_timestamps(tmp_path):
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.ENGLISH,
        segments=[
            TranscriptSegment(id="1", text="First line", start_time=0.0, end_time=0.0),
            TranscriptSegment(id="2", text="Second line", start_time=0.0, end_time=0.0),
        ],
    )
    output_path = tmp_path / "missing-times.srt"

    ExportService().export_srt(transcript, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "00:00:00,000 -->" in content
    assert "First line" in content
    assert "Second line" in content
    assert "00:00:00,000 --> 00:00:00,000" not in content
