from __future__ import annotations

from meeting_note.core.contracts import Language, TranscriptDocument, TranscriptSegment
from meeting_note.core.formatting import format_seconds, format_transcript_document


def test_format_seconds_returns_hh_mm_ss():
    assert format_seconds(3661.8) == "01:01:01"
    assert format_seconds(-1) == "00:00:00"


def test_format_transcript_document_includes_timestamps_and_speakers():
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.CHINESE,
        segments=[TranscriptSegment(id="1", text="开始", start_time=1, end_time=3, speaker_id="S1")],
    )

    assert format_transcript_document(transcript) == "[00:00:01 - 00:00:03] S1: 开始"
