from __future__ import annotations

import re
from pathlib import Path

from meeting_note.data.database import initialize_database
from meeting_note.data.models import LocalModel, ModelProvider, ModelType, RecordStatus, now_utc
from meeting_note.data.repositories import ModelRepository, RecordRepository, SettingsRepository


def test_record_repository_creates_lists_and_marks_ready(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    repo = RecordRepository(database_path)

    record = repo.create_record("Demo", Path("demo.mp3"))
    repo.mark_transcript_ready(record.id, Path("processed.wav"), "zh", has_speakers=True)

    records = repo.list_records()

    assert len(records) == 1
    assert records[0].title == "Demo"
    assert records[0].status == RecordStatus.READY
    assert records[0].has_transcript is True
    assert records[0].has_speakers is True


def test_record_repository_generates_datetime_style_record_id(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    repo = RecordRepository(database_path)

    record = repo.create_record("Demo")

    assert re.fullmatch(r"\d{8}_\d{6}_[0-9a-f]{8}", record.id)


def test_record_repository_marks_translation_and_summary_ready(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    repo = RecordRepository(database_path)
    record = repo.create_record("Demo")

    repo.mark_translation_ready(record.id)
    repo.mark_summary_ready(record.id)

    updated_record = repo.get_record(record.id)
    assert updated_record is not None
    assert updated_record.has_translation is True
    assert updated_record.has_summary is True


def test_record_repository_clears_all_records(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    repo = RecordRepository(database_path)
    first = repo.create_record("First")
    second = repo.create_record("Second")

    cleared_ids = repo.clear_all_records()

    assert set(cleared_ids) == {first.id, second.id}
    assert repo.list_records() == []


def test_model_repository_upserts_and_filters_models(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    repo = ModelRepository(database_path)
    model = LocalModel(
        id="qwen3-4b",
        name="Qwen3 4B",
        path=Path("models/llm/qwen3-4b.gguf"),
        model_type=ModelType.LLM_TRANSLATION,
        provider=ModelProvider.LLAMA_CPP,
        file_size=123,
        created_at=now_utc(),
    )

    repo.upsert_model(model)

    assert repo.list_models(ModelType.ASR) == []
    translation_models = repo.list_models(ModelType.LLM_TRANSLATION)
    assert len(translation_models) == 1
    assert translation_models[0].name == "Qwen3 4B"



def test_settings_repository_gets_sets_and_deletes_values(tmp_path):
    database_path = tmp_path / "database.sqlite"
    initialize_database(database_path)
    repo = SettingsRepository(database_path)

    repo.set("selected_translation_model_id", "qwen3-4b")
    repo.set("llm_context_length", 32768)
    repo.set("llm_use_chat_completion", True)
    repo.set_many({"llm_gpu_layers": -1, "empty_value": None})

    assert repo.get("selected_translation_model_id") == "qwen3-4b"
    assert repo.get("missing", "fallback") == "fallback"
    assert repo.get_int("llm_context_length", 8192) == 32768
    assert repo.get_bool("llm_use_chat_completion", False) is True
    assert repo.get_int("bad_int", 7) == 7
    assert repo.all() == {
        "llm_context_length": "32768",
        "llm_gpu_layers": "-1",
        "llm_use_chat_completion": "1",
        "selected_translation_model_id": "qwen3-4b",
    }

    repo.delete("selected_translation_model_id")

    assert repo.get("selected_translation_model_id") is None
