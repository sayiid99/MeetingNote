from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from meeting_note.core.model_catalog import (
    DEFAULT_ASR_MODEL,
    DEFAULT_TRANSLATION_MODEL,
    RECOMMENDED_MODELS,
    RecommendedModelSpec,
)
from meeting_note.core.model_scanner import ModelScanner


@dataclass(frozen=True)
class RecommendedModelStatus:
    spec: RecommendedModelSpec
    is_present: bool
    target_path: Path


@dataclass(frozen=True)
class ModelAvailabilitySummary:
    asr_count: int
    translation_count: int
    summary_count: int
    recommended: tuple[RecommendedModelStatus, ...]

    @property
    def asr_ready(self) -> bool:
        return self.asr_count > 0

    @property
    def translation_ready(self) -> bool:
        return self.translation_count > 0

    @property
    def summary_ready(self) -> bool:
        return self.summary_count > 0

    def missing_required(self) -> tuple[RecommendedModelSpec, ...]:
        missing: list[RecommendedModelSpec] = []
        if not self.asr_ready:
            missing.append(DEFAULT_ASR_MODEL)
        if not self.translation_ready:
            missing.append(DEFAULT_TRANSLATION_MODEL)
        return tuple(missing)


class LocalModelPreparationService:
    def __init__(self, models_dir: Path):
        self._models_dir = models_dir

    @property
    def models_dir(self) -> Path:
        return self._models_dir

    def inspect(self) -> ModelAvailabilitySummary:
        scanner = ModelScanner(self._models_dir)
        asr_models = scanner.scan_asr_models()
        translation_models = scanner.scan_llm_models()
        summary_models = scanner.scan_summary_models()
        recommended = tuple(
            RecommendedModelStatus(
                spec=spec,
                is_present=spec.is_downloaded(self._models_dir),
                target_path=spec.target_path(self._models_dir),
            )
            for spec in RECOMMENDED_MODELS
        )
        return ModelAvailabilitySummary(
            asr_count=len(asr_models),
            translation_count=len(translation_models),
            summary_count=len(summary_models),
            recommended=recommended,
        )

    def prepare_defaults(self) -> list[Path]:
        summary = self.inspect()
        downloaded: list[Path] = []
        for spec in summary.missing_required():
            downloaded.append(self.download(spec))
        return downloaded

    def download(self, spec: RecommendedModelSpec) -> Path:
        target_path = spec.target_path(self._models_dir)
        if target_path.exists():
            return target_path

        self._models_dir.mkdir(parents=True, exist_ok=True)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_download = self._load_snapshot_download()
        kwargs = {
            "model_id": spec.repo_id,
            "local_dir": str(target_path if spec.downloads_directory else target_path.parent),
            "max_workers": 4,
        }
        if spec.allow_patterns:
            kwargs["allow_patterns"] = list(spec.allow_patterns)

        snapshot_download(**kwargs)
        if not target_path.exists():
            raise FileNotFoundError(f"Downloaded model is not present at expected path: {target_path}")
        return target_path

    @staticmethod
    def _load_snapshot_download():
        try:
            from modelscope.hub.snapshot_download import snapshot_download
        except ImportError as exc:
            raise RuntimeError(
                "ModelScope is not installed. Install the local ASR runtime before downloading models."
            ) from exc
        return snapshot_download


def format_model_availability(summary: ModelAvailabilitySummary) -> list[str]:
    lines = [
        f"ASR: {'ready' if summary.asr_ready else 'missing'} ({summary.asr_count} detected)",
        f"Translation: {'ready' if summary.translation_ready else 'missing'} ({summary.translation_count} detected)",
        f"Summary: {'ready' if summary.summary_ready else 'missing'} ({summary.summary_count} detected)",
    ]
    missing = summary.missing_required()
    if missing:
        lines.append("Missing defaults:")
        for spec in missing:
            target = Path("models") / spec.target_subdir / spec.target_name
            lines.append(f"- {spec.label} -> {target} ({spec.download_size_hint})")
    else:
        lines.append("Core model categories are ready.")
    return lines
