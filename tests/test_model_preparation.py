from __future__ import annotations

from pathlib import Path

from meeting_note.core.model_catalog import DEFAULT_ASR_MODEL, DEFAULT_TRANSLATION_MODEL
from meeting_note.core.model_preparation import LocalModelPreparationService, format_model_availability


def test_model_preparation_reports_missing_defaults(tmp_path):
    service = LocalModelPreparationService(tmp_path / "models")

    summary = service.inspect()

    assert summary.asr_ready is False
    assert summary.translation_ready is False
    assert summary.missing_required() == (DEFAULT_ASR_MODEL, DEFAULT_TRANSLATION_MODEL)
    assert any("Missing defaults:" in line for line in format_model_availability(summary))


def test_model_preparation_reports_ready_when_models_exist(tmp_path):
    asr_dir = tmp_path / "models" / "asr" / "SenseVoiceSmall"
    asr_dir.mkdir(parents=True)
    (asr_dir / "config.yaml").write_text("model: sensevoice", encoding="utf-8")
    llm_path = tmp_path / "models" / "llm" / "qwen2.5-3b-instruct-q4_k_m.gguf"
    llm_path.parent.mkdir(parents=True)
    llm_path.write_bytes(b"fake gguf")
    service = LocalModelPreparationService(tmp_path / "models")

    summary = service.inspect()

    assert summary.asr_ready is True
    assert summary.translation_ready is True
    assert summary.summary_ready is True
    assert summary.missing_required() == ()


def test_model_preparation_downloads_missing_llm_file(tmp_path, monkeypatch):
    calls = []

    def fake_snapshot_download(**kwargs):
        calls.append(kwargs)
        target = Path(kwargs["local_dir"]) / DEFAULT_TRANSLATION_MODEL.target_name
        target.write_bytes(b"fake gguf")
        return str(target)

    monkeypatch.setattr(
        LocalModelPreparationService,
        "_load_snapshot_download",
        staticmethod(lambda: fake_snapshot_download),
    )
    service = LocalModelPreparationService(tmp_path / "models")

    ready_path = service.download(DEFAULT_TRANSLATION_MODEL)

    assert ready_path == tmp_path / "models" / "llm" / DEFAULT_TRANSLATION_MODEL.target_name
    assert calls[0]["model_id"] == DEFAULT_TRANSLATION_MODEL.repo_id
    assert calls[0]["allow_patterns"] == [DEFAULT_TRANSLATION_MODEL.target_name]


def test_model_preparation_downloads_missing_asr_directory(tmp_path, monkeypatch):
    calls = []

    def fake_snapshot_download(**kwargs):
        calls.append(kwargs)
        target = Path(kwargs["local_dir"])
        target.mkdir(parents=True, exist_ok=True)
        (target / "config.yaml").write_text("model: sensevoice", encoding="utf-8")
        return str(target)

    monkeypatch.setattr(
        LocalModelPreparationService,
        "_load_snapshot_download",
        staticmethod(lambda: fake_snapshot_download),
    )
    service = LocalModelPreparationService(tmp_path / "models")

    ready_path = service.download(DEFAULT_ASR_MODEL)

    assert ready_path == tmp_path / "models" / "asr" / DEFAULT_ASR_MODEL.target_name
    assert calls[0]["model_id"] == DEFAULT_ASR_MODEL.repo_id
    assert "allow_patterns" not in calls[0]
