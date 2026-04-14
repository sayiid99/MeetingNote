from __future__ import annotations

from meeting_note.core.contracts import (
    Language,
    LLMProvider,
    TranscriptDocument,
    TranslationDocument,
    TranslationMode,
)
from meeting_note.core.language_detection import detect_primary_language, is_text_in_language


class TranslationService:
    def __init__(self, llm_provider: LLMProvider):
        self._llm_provider = llm_provider

    def translate_document(
        self,
        transcript: TranscriptDocument,
        target_language: Language,
        mode: TranslationMode = TranslationMode.STANDARD,
    ) -> TranslationDocument:
        source_language = self._resolve_source_language(transcript)
        if source_language == target_language:
            raise ValueError("Source language and target language are the same. Choose the other target language.")

        prompt = self._build_document_translation_prompt(
            source_text=transcript.full_text,
            source_language=source_language,
            target_language=target_language,
            mode=mode,
        )
        translated_text = self._generate_translation_with_guard(
            source_text=transcript.full_text,
            target_language=target_language,
            prompt=prompt,
        )
        bilingual_text = self._build_bilingual_document(transcript.full_text, translated_text)
        return TranslationDocument(
            record_id=transcript.record_id,
            source_language=source_language,
            target_language=target_language,
            mode=mode,
            translated_text=translated_text,
            bilingual_text=bilingual_text,
        )

    @staticmethod
    def _build_document_translation_prompt(
        source_text: str,
        source_language: Language,
        target_language: Language,
        mode: TranslationMode,
    ) -> str:
        source_name = "Chinese" if source_language == Language.CHINESE else "English"
        target_name = "Chinese" if target_language == Language.CHINESE else "English"
        return (
            "You are a professional meeting transcript translator.\n"
            f"Source language: {source_name}.\n"
            f"Target language: {target_name}.\n"
            f"Translate the complete transcript into {target_name}.\n"
            f"Translation mode: {mode.value}.\n"
            "Use full-document context. Do not translate sentence by sentence mechanically.\n"
            "Preserve names, numbers, dates, and domain terms.\n"
            "Do not summarize. Do not add information.\n"
            f"Output must be only in {target_name}. Do not include source text.\n\n"
            "Transcript:\n"
            f"{source_text}\n"
        )

    @staticmethod
    def _build_language_rewrite_prompt(
        translation_draft: str,
        target_language: Language,
    ) -> str:
        target_name = "Chinese" if target_language == Language.CHINESE else "English"
        return (
            f"Rewrite the following text strictly in {target_name}.\n"
            "Keep meaning unchanged. Do not add or remove information.\n"
            "Return only the rewritten text.\n\n"
            "Text:\n"
            f"{translation_draft}\n"
        )

    def _generate_translation_with_guard(
        self,
        source_text: str,
        target_language: Language,
        prompt: str,
    ) -> str:
        translated_text = self._clean_output(self._llm_provider.generate(prompt))
        if is_text_in_language(translated_text, target_language):
            return translated_text

        retry_prompt = self._build_language_rewrite_prompt(translated_text or source_text, target_language)
        retried_text = self._clean_output(self._llm_provider.generate(retry_prompt))
        if is_text_in_language(retried_text, target_language):
            return retried_text

        target_name = "Chinese" if target_language == Language.CHINESE else "English"
        raise ValueError(
            f"Translation output language mismatch. The selected model could not produce {target_name} output."
        )

    @staticmethod
    def _resolve_source_language(transcript: TranscriptDocument) -> Language:
        if transcript.language in {Language.CHINESE, Language.ENGLISH}:
            return transcript.language
        return detect_primary_language(transcript.full_text)

    @staticmethod
    def _build_bilingual_document(source_text: str, translated_text: str) -> str:
        return (
            "# Bilingual Document\n\n"
            "## Source Transcript\n\n"
            f"{source_text.strip()}\n\n"
            "## Full Translation\n\n"
            f"{translated_text.strip()}"
        )

    @staticmethod
    def _clean_output(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3:
                return "\n".join(lines[1:-1]).strip()
        return stripped
