from __future__ import annotations

from pathlib import Path

import pytest

from meeting_note.core.llm_provider_factory import LLMProviderFactory
from meeting_note.core.model_settings import ModelSelection, ModelSettingsService
from meeting_note.data.database import initialize_database
from meeting_note.data.models import LocalModel, ModelProvider, ModelType, now_utc
from meeting_note.data.repositories import ModelRepository, SettingsRepository


class FakeLlamaModel:
    init_kwargs: dict[str, object] | None = None

    def __init__(self, **kwargs: object):
        FakeLlamaModel.init_kwargs = kwargs

    def __call__(self, prompt: str, **kwargs: object) -> dict[str, object]:
        return {"choices": [{"text": f"ok: {prompt}"}]}


def add_model(
    repository: ModelRepository,
    model_id: str,
    model_name: str,
    model_type: ModelType,
    path: Path,
) -> None:
    repository.upsert_model(
        LocalModel(
            id=model_id,
            name=model_name,
            path=path,
            model_type=model_type,
            provider=ModelProvider.LLAMA_CPP,
            created_at=now_utc(),
            file_size=path.stat().st_size,
        )
    )


def build_factory(tmp_path, selection: ModelSelection | None = None) -> LLMProviderFactory:
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    model_repository = ModelRepository(database_path)
    settings_repository = SettingsRepository(database_path)
    model_settings_service = ModelSettingsService(settings_repository)
    if selection:
        model_settings_service.save(selection)
    model_path = tmp_path / "models" / "llm" / "qwen3.gguf"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"gguf")
    add_model(model_repository, "qwen3-translation", "Qwen3", ModelType.LLM_TRANSLATION, model_path)
    add_model(model_repository, "qwen3-summary", "Qwen3", ModelType.LLM_SUMMARY, model_path)
    return LLMProviderFactory(
        model_repository=model_repository,
        model_settings_service=model_settings_service,
        llama_factory=FakeLlamaModel,
    )


def test_llm_provider_factory_builds_translation_provider_from_selected_model(tmp_path):
    factory = build_factory(
        tmp_path,
        ModelSelection(
            selected_translation_model_id="qwen3-translation",
            llm_context_length=32768,
            llm_gpu_layers=32,
            llm_chat_format="chatml",
            llm_use_chat_completion=False,
        ),
    )

    provider = factory.create_translation_provider()

    assert provider.generate("hello") == "ok: hello"
    assert FakeLlamaModel.init_kwargs is not None
    assert FakeLlamaModel.init_kwargs["n_ctx"] == 32768
    assert FakeLlamaModel.init_kwargs["n_gpu_layers"] == 32
    assert FakeLlamaModel.init_kwargs["chat_format"] == "chatml"


def test_llm_provider_factory_matches_saved_model_name(tmp_path):
    factory = build_factory(tmp_path, ModelSelection(selected_translation_model_id="qwen3"))

    provider = factory.create_translation_provider()

    assert provider.generate("translate") == "ok: translate"


def test_llm_provider_factory_falls_back_when_saved_model_missing(tmp_path):
    factory = build_factory(
        tmp_path,
        ModelSelection(selected_translation_model_id="missing-model", llm_use_chat_completion=False),
    )

    provider = factory.create_translation_provider()

    assert provider.generate("fallback") == "ok: fallback"


def test_llm_provider_factory_uses_first_available_model_when_none_selected(tmp_path):
    factory = build_factory(tmp_path)

    provider = factory.create_summary_provider()

    assert provider.generate("summary") == "ok: summary"


def test_llm_provider_factory_requires_at_least_one_model(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    factory = LLMProviderFactory(
        model_repository=ModelRepository(database_path),
        model_settings_service=ModelSettingsService(SettingsRepository(database_path)),
        llama_factory=FakeLlamaModel,
    )

    with pytest.raises(ValueError, match="No llm_translation model is available"):
        factory.create_translation_provider()
