from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from meeting_note.data.models import ModelType


@dataclass(frozen=True)
class RecommendedModelSpec:
    key: str
    label: str
    model_type: ModelType
    repo_id: str
    target_subdir: str
    target_name: str
    description: str
    download_size_hint: str
    allow_patterns: tuple[str, ...] = ()

    def target_path(self, models_dir: Path) -> Path:
        return models_dir / self.target_subdir / self.target_name

    @property
    def downloads_directory(self) -> bool:
        return not self.allow_patterns

    def is_downloaded(self, models_dir: Path) -> bool:
        return self.target_path(models_dir).exists()


DEFAULT_ASR_MODEL = RecommendedModelSpec(
    key="default_asr",
    label="SenseVoiceSmall",
    model_type=ModelType.ASR,
    repo_id="iic/SenseVoiceSmall",
    target_subdir="asr",
    target_name="SenseVoiceSmall",
    description="Offline multilingual ASR model for meeting transcription.",
    download_size_hint="about 1 GB",
)

DEFAULT_TRANSLATION_MODEL = RecommendedModelSpec(
    key="default_translation",
    label="Qwen2.5-3B-Instruct-Q4_K_M",
    model_type=ModelType.LLM_TRANSLATION,
    repo_id="qwen/Qwen2.5-3B-Instruct-GGUF",
    target_subdir="llm",
    target_name="qwen2.5-3b-instruct-q4_k_m.gguf",
    description="Starter GGUF model for full-document Chinese-English translation and summary.",
    download_size_hint="about 2 GB",
    allow_patterns=("qwen2.5-3b-instruct-q4_k_m.gguf",),
)

RECOMMENDED_MODELS: tuple[RecommendedModelSpec, ...] = (
    DEFAULT_ASR_MODEL,
    DEFAULT_TRANSLATION_MODEL,
)
