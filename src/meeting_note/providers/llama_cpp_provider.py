from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LlamaCppConfig:
    n_ctx: int = 8192
    n_gpu_layers: int = -1
    n_threads: int | None = None
    chat_format: str | None = None
    default_max_tokens: int = 2048
    temperature: float = 0.2
    top_p: float = 0.9
    repeat_penalty: float = 1.1
    system_prompt: str = "You are a precise offline meeting assistant."
    use_chat_completion: bool = True
    verbose: bool = False


class LlamaCppProvider:
    def __init__(
        self,
        model_path: Path,
        config: LlamaCppConfig | None = None,
        llama_factory: Callable[..., Any] | None = None,
    ):
        self._model_path = model_path
        self._config = config or LlamaCppConfig()
        self._llama_factory = llama_factory
        self._model: Any | None = None

    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        model = self._get_model()
        token_limit = max_tokens or self._config.default_max_tokens

        if self._config.use_chat_completion and hasattr(model, "create_chat_completion"):
            text = self._generate_chat(model, prompt, token_limit)
            if text:
                return text

        response = model(
            prompt,
            max_tokens=token_limit,
            temperature=self._config.temperature,
            top_p=self._config.top_p,
            repeat_penalty=self._config.repeat_penalty,
        )
        return self._extract_completion_text(response)

    def _generate_chat(self, model: Any, prompt: str, max_tokens: int) -> str:
        response = model.create_chat_completion(
            messages=[
                {"role": "system", "content": self._config.system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=self._config.temperature,
            top_p=self._config.top_p,
            repeat_penalty=self._config.repeat_penalty,
        )
        return self._extract_chat_text(response)

    def _get_model(self) -> Any:
        if self._model is None:
            if not self._model_path.exists():
                raise FileNotFoundError(f"LLM model file does not exist: {self._model_path}")
            factory = self._llama_factory or self._load_llama_factory()
            kwargs: dict[str, Any] = {
                "model_path": str(self._model_path),
                "n_ctx": self._config.n_ctx,
                "n_gpu_layers": self._config.n_gpu_layers,
                "verbose": self._config.verbose,
            }
            if self._config.n_threads is not None:
                kwargs["n_threads"] = self._config.n_threads
            if self._config.chat_format:
                kwargs["chat_format"] = self._config.chat_format
            self._model = factory(**kwargs)
        return self._model

    @staticmethod
    def _load_llama_factory() -> Callable[..., Any]:
        try:
            module = import_module("llama_cpp")
        except ImportError as exc:
            raise RuntimeError(
                "llama-cpp-python is not installed. Install the llm extra before using GGUF models."
            ) from exc
        return module.Llama

    @staticmethod
    def _extract_completion_text(response: Any) -> str:
        if isinstance(response, str):
            return response.strip()
        if not isinstance(response, dict):
            return str(response).strip()
        choices = response.get("choices") or []
        if not choices:
            return ""
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            return str(first_choice.get("text", "")).strip()
        return str(first_choice).strip()

    @staticmethod
    def _extract_chat_text(response: Any) -> str:
        if not isinstance(response, dict):
            return ""
        choices = response.get("choices") or []
        if not choices:
            return ""
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return ""
        message = first_choice.get("message") or {}
        if isinstance(message, dict):
            return str(message.get("content", "")).strip()
        return ""
