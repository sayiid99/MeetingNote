from __future__ import annotations

from meeting_note.core.contracts import Language, TranscriptDocument, TranscriptSegment, TranslationMode
from meeting_note.core.translation_service import TranslationService


class RecordingLLMProvider:
    def __init__(self):
        self.prompts: list[str] = []

    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        self.prompts.append(prompt)
        return "translated document"


def test_translate_document_uses_full_document_prompt():
    llm = RecordingLLMProvider()
    service = TranslationService(llm)
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.CHINESE,
        segments=[
            TranscriptSegment(id="1", text="\u7b2c\u4e00\u6bb5", start_time=0, end_time=1),
            TranscriptSegment(id="2", text="\u7b2c\u4e8c\u6bb5", start_time=1, end_time=2),
        ],
    )

    result = service.translate_document(
        transcript,
        target_language=Language.ENGLISH,
        mode=TranslationMode.FAITHFUL,
    )

    assert result.translated_text == "translated document"
    assert len(llm.prompts) == 1
    assert "Target language: English" in llm.prompts[0]
    assert "Use full-document context" in llm.prompts[0]
    assert "\u7b2c\u4e00\u6bb5\n\u7b2c\u4e8c\u6bb5" in llm.prompts[0]


def test_translate_document_builds_document_level_bilingual_text():
    llm = RecordingLLMProvider()
    service = TranslationService(llm)
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.CHINESE,
        segments=[TranscriptSegment(id="1", text="\u5b8c\u6574\u4e2d\u6587\u539f\u6587", start_time=0, end_time=1)],
    )

    result = service.translate_document(transcript, target_language=Language.ENGLISH)

    assert result.bilingual_text is not None
    assert "## Source Transcript" in result.bilingual_text
    assert "\u5b8c\u6574\u4e2d\u6587\u539f\u6587" in result.bilingual_text
    assert "## Full Translation" in result.bilingual_text
    assert "translated document" in result.bilingual_text


class RetryLLMProvider:
    def __init__(self):
        self.calls = 0

    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        self.calls += 1
        if self.calls == 1:
            return "\u8fd9\u662f\u9519\u8bef\u8bed\u8a00\u8f93\u51fa"
        return "This is corrected English output."


def test_translate_document_retries_when_output_language_mismatches_target():
    llm = RetryLLMProvider()
    service = TranslationService(llm)
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.CHINESE,
        segments=[TranscriptSegment(id="1", text="\u8fd9\u662f\u4e2d\u6587\u539f\u6587", start_time=0, end_time=1)],
    )

    result = service.translate_document(transcript, target_language=Language.ENGLISH)

    assert llm.calls == 2
    assert result.translated_text == "This is corrected English output."
