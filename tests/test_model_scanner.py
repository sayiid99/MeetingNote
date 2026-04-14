from __future__ import annotations

from meeting_note.core.model_scanner import ModelScanner
from meeting_note.data.models import ModelProvider, ModelType


def test_model_scanner_detects_gguf_llm_models(tmp_path):
    llm_dir = tmp_path / "models" / "llm"
    llm_dir.mkdir(parents=True)
    model_path = llm_dir / "Qwen3-4B-Q4_K_M.gguf"
    model_path.write_bytes(b"fake model")
    (llm_dir / "notes.txt").write_text("ignore", encoding="utf-8")

    models = ModelScanner(tmp_path / "models").scan_llm_models()

    assert len(models) == 1
    assert models[0].name == "Qwen3-4B-Q4_K_M"
    assert models[0].path == model_path
    assert models[0].provider == ModelProvider.LLAMA_CPP
    assert models[0].model_type == ModelType.LLM_TRANSLATION
    assert models[0].quantization == "Q4_K_M"
    assert models[0].file_size == len(b"fake model")


def test_model_scanner_returns_empty_when_llm_dir_missing(tmp_path):
    assert ModelScanner(tmp_path / "models").scan_llm_models() == []


def test_model_scanner_maps_same_gguf_as_summary_models(tmp_path):
    llm_dir = tmp_path / "models" / "llm"
    llm_dir.mkdir(parents=True)
    (llm_dir / "gemma4-q8_0.gguf").write_bytes(b"fake model")

    summary_models = ModelScanner(tmp_path / "models").scan_summary_models()

    assert len(summary_models) == 1
    assert summary_models[0].model_type == ModelType.LLM_SUMMARY
    assert summary_models[0].quantization == "Q8_0"


def test_model_scanner_detects_asr_model_directories(tmp_path):
    asr_dir = tmp_path / "models" / "asr" / "SenseVoiceSmall"
    asr_dir.mkdir(parents=True)
    (asr_dir / "config.yaml").write_text("model: sensevoice", encoding="utf-8")
    (tmp_path / "models" / "asr" / "readme.txt").write_text("ignore", encoding="utf-8")

    models = ModelScanner(tmp_path / "models").scan_asr_models()

    assert len(models) == 1
    assert models[0].name == "SenseVoiceSmall"
    assert models[0].path == asr_dir
    assert models[0].provider == ModelProvider.FUNASR
    assert models[0].model_type == ModelType.ASR
    assert models[0].file_size == len("model: sensevoice")


def test_model_scanner_scan_all_models_combines_asr_translation_and_summary(tmp_path):
    (tmp_path / "models" / "asr" / "SenseVoiceSmall").mkdir(parents=True)
    llm_dir = tmp_path / "models" / "llm"
    llm_dir.mkdir(parents=True)
    (llm_dir / "Qwen3-4B-Q4_K_M.gguf").write_bytes(b"fake model")

    models = ModelScanner(tmp_path / "models").scan_all_models()

    assert [model.model_type for model in models] == [
        ModelType.ASR,
        ModelType.LLM_TRANSLATION,
        ModelType.LLM_SUMMARY,
    ]
