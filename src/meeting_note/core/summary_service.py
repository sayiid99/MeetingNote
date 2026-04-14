from __future__ import annotations

from dataclasses import dataclass, field

from meeting_note.core.contracts import LLMProvider, Language, TranscriptDocument
from meeting_note.core.language_detection import detect_primary_language, is_text_in_language


@dataclass
class MeetingSummary:
    overview: str
    key_decisions: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


class SummaryService:
    def __init__(self, llm_provider: LLMProvider):
        self._llm_provider = llm_provider

    def summarize(self, transcript: TranscriptDocument) -> str:
        target_language = self._resolve_target_language(transcript)
        prompt = self._build_prompt(transcript.full_text, target_language)
        summary_text = self._llm_provider.generate(prompt).strip()
        if is_text_in_language(summary_text, target_language):
            return summary_text

        retry_prompt = self._build_language_rewrite_prompt(summary_text, target_language)
        retried_summary = self._llm_provider.generate(retry_prompt).strip()
        if is_text_in_language(retried_summary, target_language):
            return retried_summary

        target_name = "Chinese" if target_language == Language.CHINESE else "English"
        raise ValueError(f"Summary output language mismatch. The selected model could not produce {target_name}.")

    @staticmethod
    def _resolve_target_language(transcript: TranscriptDocument) -> Language:
        if transcript.language in {Language.CHINESE, Language.ENGLISH}:
            return transcript.language
        return detect_primary_language(transcript.full_text)

    @staticmethod
    def _build_prompt(transcript_text: str, target_language: Language) -> str:
        if target_language == Language.CHINESE:
            return (
                "请仅基于转写内容生成事实性会议摘要。\n"
                "仅使用中文输出。\n"
                "使用以下小节：概览、关键决策、行动项、风险与问题、下一步。\n"
                "不要编造信息。\n\n"
                f"转写内容：\n{transcript_text}\n"
            )
        return (
            "Create a factual meeting summary from the transcript only.\n"
            "Output in English only.\n"
            "Use these sections: Overview, Key Decisions, Action Items, Risks and Issues, Next Steps.\n"
            "Do not invent information.\n\n"
            f"Transcript:\n{transcript_text}\n"
        )

    @staticmethod
    def _build_language_rewrite_prompt(summary_text: str, target_language: Language) -> str:
        target_name = "Chinese" if target_language == Language.CHINESE else "English"
        return (
            f"Rewrite the following meeting summary strictly in {target_name}.\n"
            "Keep all facts unchanged. Do not add information.\n"
            "Return only the rewritten summary.\n\n"
            f"Summary:\n{summary_text}\n"
        )
