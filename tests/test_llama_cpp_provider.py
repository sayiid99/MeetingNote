from __future__ import annotations

import types

import pytest

from meeting_note.providers.llama_cpp_provider import LlamaCppConfig, LlamaCppProvider


class FakeCompletionModel:
    init_kwargs: dict[str, object] | None = None
    calls: list[dict[str, object]] = []

    def __init__(self, **kwargs: object):
        FakeCompletionModel.init_kwargs = kwargs

    def __call__(self, prompt: str, **kwargs: object) -> dict[str, object]:
        FakeCompletionModel.calls.append({"prompt": prompt, **kwargs})
        return {"choices": [{"text": " Generated text. "}]}


class FakeChatModel(FakeCompletionModel):
    chat_calls: list[dict[str, object]] = []

    def create_chat_completion(self, **kwargs: object) -> dict[str, object]:
        FakeChatModel.chat_calls.append(kwargs)
        return {"choices": [{"message": {"content": " Chat text. "}}]}


class EmptyChatModel(FakeCompletionModel):
    def create_chat_completion(self, **kwargs: object) -> dict[str, object]:
        return {"choices": [{"message": {"content": ""}}]}


def test_llama_cpp_provider_lazy_loads_model_and_generates_completion(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_bytes(b"gguf")
    provider = LlamaCppProvider(
        model_path,
        config=LlamaCppConfig(use_chat_completion=False, n_ctx=4096, n_gpu_layers=12, n_threads=4),
        llama_factory=FakeCompletionModel,
    )

    assert FakeCompletionModel.init_kwargs is None

    result = provider.generate("Translate this", max_tokens=128)

    assert result == "Generated text."
    assert FakeCompletionModel.init_kwargs == {
        "model_path": str(model_path),
        "n_ctx": 4096,
        "n_gpu_layers": 12,
        "verbose": False,
        "n_threads": 4,
    }
    assert FakeCompletionModel.calls[-1] == {
        "prompt": "Translate this",
        "max_tokens": 128,
        "temperature": 0.2,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
    }


def test_llama_cpp_provider_uses_chat_completion_when_available(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_bytes(b"gguf")
    provider = LlamaCppProvider(model_path, llama_factory=FakeChatModel)

    result = provider.generate("Summarize this")

    assert result == "Chat text."
    assert FakeChatModel.chat_calls[-1]["messages"] == [
        {"role": "system", "content": "You are a precise offline meeting assistant."},
        {"role": "user", "content": "Summarize this"},
    ]
    assert FakeChatModel.chat_calls[-1]["max_tokens"] == 2048


def test_llama_cpp_provider_falls_back_when_chat_returns_empty_text(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_bytes(b"gguf")
    provider = LlamaCppProvider(model_path, llama_factory=EmptyChatModel)

    assert provider.generate("Prompt") == "Generated text."


def test_llama_cpp_provider_rejects_missing_model_file(tmp_path):
    provider = LlamaCppProvider(tmp_path / "missing.gguf", llama_factory=FakeCompletionModel)

    with pytest.raises(FileNotFoundError, match="LLM model file does not exist"):
        provider.generate("Prompt")


def test_llama_cpp_provider_reports_missing_dependency(monkeypatch, tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_bytes(b"gguf")

    def fake_import_module(name: str) -> types.ModuleType:
        raise ImportError(name)

    monkeypatch.setattr("meeting_note.providers.llama_cpp_provider.import_module", fake_import_module)
    provider = LlamaCppProvider(model_path)

    with pytest.raises(RuntimeError, match="llama-cpp-python is not installed"):
        provider.generate("Prompt")


def test_llama_cpp_provider_passes_optional_chat_format(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_bytes(b"gguf")
    provider = LlamaCppProvider(
        model_path,
        config=LlamaCppConfig(use_chat_completion=False, chat_format="gemma"),
        llama_factory=FakeCompletionModel,
    )

    provider.generate("Prompt")

    assert FakeCompletionModel.init_kwargs is not None
    assert FakeCompletionModel.init_kwargs["chat_format"] == "gemma"
