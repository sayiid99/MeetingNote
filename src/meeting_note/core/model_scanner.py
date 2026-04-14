from __future__ import annotations

from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from meeting_note.data.models import LocalModel, ModelProvider, ModelType, now_utc


class ModelScanner:
    def __init__(self, models_dir: Path):
        self._models_dir = models_dir

    @property
    def models_dir(self) -> Path:
        return self._models_dir

    def scan_all_models(self) -> list[LocalModel]:
        return self.scan_asr_models() + self.scan_llm_models() + self.scan_summary_models()

    def scan_asr_models(self) -> list[LocalModel]:
        asr_dir = self._models_dir / "asr"
        if not asr_dir.exists():
            return []

        models: list[LocalModel] = []
        for path in sorted(asr_dir.iterdir()):
            if not path.is_dir():
                continue
            models.append(
                LocalModel(
                    id=self._model_id(path),
                    name=path.name,
                    path=path,
                    model_type=ModelType.ASR,
                    provider=ModelProvider.FUNASR,
                    file_size=self._folder_size(path),
                    created_at=now_utc(),
                    status="detected",
                )
            )
        return models

    def scan_llm_models(self) -> list[LocalModel]:
        llm_dir = self._models_dir / "llm"
        if not llm_dir.exists():
            return []

        models: list[LocalModel] = []
        for path in sorted(llm_dir.glob("*.gguf")):
            models.append(
                LocalModel(
                    id=self._model_id(path),
                    name=path.stem,
                    path=path,
                    model_type=ModelType.LLM_TRANSLATION,
                    provider=ModelProvider.LLAMA_CPP,
                    file_size=path.stat().st_size,
                    quantization=self._guess_quantization(path.name),
                    created_at=now_utc(),
                    status="detected",
                )
            )
        return models

    def scan_summary_models(self) -> list[LocalModel]:
        return [
            LocalModel(
                id=f"{model.id}:summary",
                name=model.name,
                path=model.path,
                model_type=ModelType.LLM_SUMMARY,
                provider=model.provider,
                file_size=model.file_size,
                quantization=model.quantization,
                context_length=model.context_length,
                created_at=model.created_at,
                status=model.status,
            )
            for model in self.scan_llm_models()
        ]

    @staticmethod
    def _model_id(path: Path) -> str:
        return str(uuid5(NAMESPACE_URL, str(path.resolve()).lower()))

    @staticmethod
    def _folder_size(path: Path) -> int:
        total = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total += file_path.stat().st_size
        return total

    @staticmethod
    def _guess_quantization(filename: str) -> str | None:
        lowered = filename.lower()
        known_quantizations = [
            "q2_k",
            "q3_k_s",
            "q3_k_m",
            "q3_k_l",
            "q4_0",
            "q4_1",
            "q4_k_s",
            "q4_k_m",
            "q5_0",
            "q5_1",
            "q5_k_s",
            "q5_k_m",
            "q6_k",
            "q8_0",
        ]
        for quantization in known_quantizations:
            if quantization in lowered:
                return quantization.upper()
        return None
