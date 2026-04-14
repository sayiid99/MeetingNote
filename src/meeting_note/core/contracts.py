from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol


class Language(str, Enum):
    AUTO = "auto"
    CHINESE = "zh"
    ENGLISH = "en"


class TranslationMode(str, Enum):
    STANDARD = "standard"
    FAITHFUL = "faithful"
    BUSINESS = "business"


@dataclass
class TranscriptSegment:
    id: str
    text: str
    start_time: float
    end_time: float
    speaker_id: str | None = None
    is_edited: bool = False


@dataclass
class TranscriptDocument:
    record_id: str
    language: Language
    segments: list[TranscriptSegment] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(segment.text for segment in self.segments if segment.text.strip())


@dataclass
class TranslationDocument:
    record_id: str
    source_language: Language
    target_language: Language
    mode: TranslationMode
    translated_text: str
    bilingual_text: str | None = None


class ASRProvider(Protocol):
    def transcribe(self, audio_path: Path, source_language: Language) -> TranscriptDocument:
        ...


class LLMProvider(Protocol):
    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        ...
