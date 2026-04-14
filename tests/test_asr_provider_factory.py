from __future__ import annotations

import pytest

from meeting_note.core.asr_provider_factory import ASRProviderFactory
from meeting_note.core.model_settings import ModelSelection, ModelSettingsService
from meeting_note.data.database import initialize_database
from meeting_note.data.models import LocalModel, ModelProvider, ModelType, now_utc
from meeting_note.data.repositories import ModelRepository, SettingsRepository


def add_asr_model(repository: ModelRepository, model_id: str, model_path) -> None:
    repository.upsert_model(
        LocalModel(
            id=model_id,
            name=model_path.name,
            path=model_path,
            model_type=ModelType.ASR,
            provider=ModelProvider.FUNASR,
            created_at=now_utc(),
            status="detected",
        )
    )


def build_factory(tmp_path, selection: ModelSelection | None = None) -> ASRProviderFactory:
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    model_repository = ModelRepository(database_path)
    settings_repository = SettingsRepository(database_path)
    settings_service = ModelSettingsService(settings_repository)
    if selection:
        settings_service.save(selection)
    model_path = tmp_path / "models" / "asr" / "SenseVoiceSmall"
    model_path.mkdir(parents=True)
    add_asr_model(model_repository, "sensevoice", model_path)
    return ASRProviderFactory(
        model_repository=model_repository,
        model_settings_service=settings_service,
        device="cuda:0",
        enable_speakers=False,
    )


def test_asr_provider_factory_builds_provider_from_selected_model(tmp_path):
    factory = build_factory(tmp_path, ModelSelection(selected_asr_model_id="sensevoice"))

    provider = factory.create_provider()
    kwargs = provider._build_model_kwargs()

    assert kwargs["model"].endswith("SenseVoiceSmall")
    assert kwargs["device"] == "cuda:0"
    assert "spk_model" not in kwargs


def test_asr_provider_factory_matches_saved_model_name(tmp_path):
    factory = build_factory(tmp_path, ModelSelection(selected_asr_model_id="SenseVoiceSmall"))

    provider = factory.create_provider()

    assert provider._build_model_kwargs()["model"].endswith("SenseVoiceSmall")


def test_asr_provider_factory_falls_back_when_saved_model_missing(tmp_path):
    factory = build_factory(tmp_path, ModelSelection(selected_asr_model_id="missing"))

    provider = factory.create_provider()

    assert provider._build_model_kwargs()["model"].endswith("SenseVoiceSmall")


def test_asr_provider_factory_uses_first_available_model_when_none_selected(tmp_path):
    provider = build_factory(tmp_path).create_provider()

    assert provider._build_model_kwargs()["model"].endswith("SenseVoiceSmall")


def test_asr_provider_factory_requires_at_least_one_model(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    factory = ASRProviderFactory(
        model_repository=ModelRepository(database_path),
        model_settings_service=ModelSettingsService(SettingsRepository(database_path)),
    )

    with pytest.raises(ValueError, match="No ASR model is available"):
        factory.create_provider()
