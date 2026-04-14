from __future__ import annotations

from meeting_note.core.contracts import Language
from meeting_note.providers.funasr_provider import FunASRProvider


def test_funasr_provider_parses_sentence_info_with_timestamps_and_speakers():
    result = [
        {
            "sentence_info": [
                {"text": " 大家好 ", "start": 0, "end": 1200, "spk": 0},
                {"text": "我们开始。", "start": 1200, "end": 2400, "spk_id": 1},
            ]
        }
    ]

    transcript = FunASRProvider.parse_result(result, record_id="rec-1", language=Language.CHINESE)

    assert transcript.record_id == "rec-1"
    assert transcript.language == Language.CHINESE
    assert [segment.text for segment in transcript.segments] == ["大家好", "我们开始。"]
    assert transcript.segments[0].start_time == 0.0
    assert transcript.segments[0].end_time == 1.2
    assert transcript.segments[0].speaker_id == "S1"
    assert transcript.segments[1].speaker_id == "S2"


def test_funasr_provider_parses_plain_text_result():
    transcript = FunASRProvider.parse_result(
        [{"text": "完整文本"}],
        record_id="rec-1",
        language=Language.AUTO,
    )

    assert len(transcript.segments) == 1
    assert transcript.full_text == "完整文本"


def test_funasr_provider_cleans_model_tags():
    assert FunASRProvider.clean_text("< | zh | > <|NEUTRAL|> hello") == "hello"


def test_funasr_provider_builds_kwargs_with_custom_model_directories(tmp_path):
    asr_model_dir = tmp_path / "asr" / "SenseVoiceSmall"
    vad_model_dir = tmp_path / "vad"
    punc_model_dir = tmp_path / "punc"
    speaker_model_dir = tmp_path / "speaker"
    for directory in (asr_model_dir, vad_model_dir, punc_model_dir, speaker_model_dir):
        directory.mkdir(parents=True)

    provider = FunASRProvider(
        models_dir=tmp_path,
        asr_model_dir=asr_model_dir,
        vad_model_dir=vad_model_dir,
        punc_model_dir=punc_model_dir,
        speaker_model_dir=speaker_model_dir,
        device="cuda:0",
    )

    assert provider._build_model_kwargs() == {
        "model": str(asr_model_dir),
        "device": "cuda:0",
        "disable_update": True,
        "vad_model": str(vad_model_dir),
        "punc_model": str(punc_model_dir),
        "spk_model": str(speaker_model_dir),
    }
