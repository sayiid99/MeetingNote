from __future__ import annotations

from pathlib import Path

from meeting_note.core.contracts import ASRProvider, Language, TranscriptDocument


class ASRService:
    def __init__(self, provider: ASRProvider):
        self._provider = provider

    def transcribe(self, audio_path: Path, source_language: Language = Language.AUTO) -> TranscriptDocument:
        return self._provider.transcribe(audio_path, source_language)
