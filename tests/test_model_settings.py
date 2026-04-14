from __future__ import annotations

from meeting_note.core.model_settings import ModelSelection, ModelSettingsService
from meeting_note.data.database import initialize_database
from meeting_note.data.repositories import SettingsRepository


def test_model_settings_service_loads_defaults(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    service = ModelSettingsService(SettingsRepository(database_path))

    assert service.load() == ModelSelection()


def test_model_settings_service_saves_and_loads_selection(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    service = ModelSettingsService(SettingsRepository(database_path))
    selection = ModelSelection(
        selected_asr_model_id="funasr-sensevoice",
        selected_translation_model_id="qwen3-4b",
        selected_summary_model_id="gemma-4-4b",
        ui_language="zh",
        llm_context_length=32768,
        llm_gpu_layers=99,
        llm_chat_format="chatml",
        llm_use_chat_completion=False,
    )

    service.save(selection)

    assert service.load() == selection


def test_model_settings_service_removes_optional_ids_when_saved_as_none(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    service = ModelSettingsService(SettingsRepository(database_path))
    service.save(ModelSelection(selected_translation_model_id="qwen3-4b"))

    service.save(ModelSelection(selected_translation_model_id=None))

    assert service.load().selected_translation_model_id is None


def test_model_settings_service_normalizes_ui_language(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    service = ModelSettingsService(SettingsRepository(database_path))

    service.save(ModelSelection(ui_language="zh-CN"))

    assert service.load().ui_language == "zh"
