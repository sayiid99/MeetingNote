from __future__ import annotations

from meeting_note.core.contracts import Language, TranscriptDocument, TranscriptSegment
from meeting_note.core.summary_service import SummaryService


class ChinesePromptProvider:
    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        assert "\u4ec5\u4f7f\u7528\u4e2d\u6587\u8f93\u51fa" in prompt
        assert "\u4e0d\u8981\u7f16\u9020\u4fe1\u606f" in prompt
        return "\u6982\u89c8\uff1a\u56e2\u961f\u8ba8\u8bba\u4e86\u4ea7\u54c1\u6f14\u793a\u3002"


def test_summary_service_generates_chinese_summary_for_chinese_transcript():
    service = SummaryService(ChinesePromptProvider())
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.CHINESE,
        segments=[TranscriptSegment(id="1", text="\u6211\u4eec\u8ba8\u8bba\u4e86\u4ea7\u54c1\u6f14\u793a", start_time=0, end_time=3)],
    )

    summary = service.summarize(transcript)

    assert "\u4ea7\u54c1\u6f14\u793a" in summary


class EnglishPromptProvider:
    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        assert "Output in English only." in prompt
        assert "Do not invent information." in prompt
        return "Overview: The team discussed the product demo."


def test_summary_service_generates_english_summary_for_english_transcript():
    service = SummaryService(EnglishPromptProvider())
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.ENGLISH,
        segments=[TranscriptSegment(id="1", text="We discussed the product demo.", start_time=0, end_time=3)],
    )

    summary = service.summarize(transcript)

    assert "product demo" in summary


class RetrySummaryProvider:
    def __init__(self):
        self.calls = 0

    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        self.calls += 1
        if self.calls == 1:
            return "Overview: Wrong language."
        return "\u6982\u89c8\uff1a\u8fd9\u662f\u4e2d\u6587\u6458\u8981\u3002"


def test_summary_service_retries_when_output_language_mismatches_transcript():
    service = SummaryService(RetrySummaryProvider())
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.CHINESE,
        segments=[TranscriptSegment(id="1", text="\u4f1a\u8bae\u8ba8\u8bba\u4e86\u9032\u5ea6", start_time=0, end_time=3)],
    )

    summary = service.summarize(transcript)

    assert "\u4e2d\u6587\u6458\u8981" in summary
