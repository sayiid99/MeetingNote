from __future__ import annotations

from meeting_note.core.contracts import TranscriptDocument, TranscriptSegment


def format_seconds(seconds: float) -> str:
    safe_seconds = max(0, int(seconds))
    hours = safe_seconds // 3600
    minutes = (safe_seconds % 3600) // 60
    remaining_seconds = safe_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


def format_transcript_segment(
    segment: TranscriptSegment,
    show_timestamps: bool = True,
    show_speakers: bool = True,
) -> str:
    parts: list[str] = []
    if show_timestamps:
        parts.append(f"[{format_seconds(segment.start_time)} - {format_seconds(segment.end_time)}]")
    if show_speakers and segment.speaker_id:
        parts.append(f"{segment.speaker_id}:")
    parts.append(segment.text)
    return " ".join(parts)


def format_transcript_document(
    transcript: TranscriptDocument,
    show_timestamps: bool = True,
    show_speakers: bool = True,
) -> str:
    return "\n".join(
        format_transcript_segment(segment, show_timestamps, show_speakers)
        for segment in transcript.segments
    )
