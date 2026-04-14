from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from meeting_note.core.contracts import Language, TranscriptDocument, TranscriptSegment


class FunASRProvider:
    ASR_MODEL_DIR = "speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    VAD_MODEL_DIR = "speech_fsmn_vad_zh-cn-16k-common-pytorch"
    PUNC_MODEL_DIR = "punc_ct-transformer_cn-en-common-vocab471067-large"
    SPEAKER_MODEL_DIR = "speech_campplus_sv_zh-cn_16k-common"

    def __init__(
        self,
        models_dir: Path,
        device: str = "cpu",
        enable_speakers: bool = True,
        asr_model_dir: Path | None = None,
        vad_model_dir: Path | None = None,
        punc_model_dir: Path | None = None,
        speaker_model_dir: Path | None = None,
    ):
        self._models_dir = models_dir
        self._device = device
        self._enable_speakers = enable_speakers
        self._asr_model_dir = asr_model_dir
        self._vad_model_dir = vad_model_dir
        self._punc_model_dir = punc_model_dir
        self._speaker_model_dir = speaker_model_dir
        self._model: Any | None = None

    def transcribe(self, audio_path: Path, source_language: Language = Language.AUTO) -> TranscriptDocument:
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")

        model = self._ensure_model()
        result = model.generate(
            input=str(audio_path),
            batch_size_s=60,
            use_itn=True,
            merge_vad=True,
            stream=False,
        )
        return self.parse_result(result, record_id=audio_path.stem, language=source_language)

    def _ensure_model(self):
        if self._model is not None:
            return self._model

        try:
            from funasr import AutoModel
        except ImportError as exc:
            raise RuntimeError(
                "FunASR is not installed. Install the optional ASR dependencies before transcription."
            ) from exc

        self._model = AutoModel(**self._build_model_kwargs())
        return self._model

    def _build_model_kwargs(self) -> dict[str, object]:
        asr_model_path = self._asr_model_dir or self._models_dir / self.ASR_MODEL_DIR
        vad_model_path = self._vad_model_dir or self._models_dir / self.VAD_MODEL_DIR
        punc_model_path = self._punc_model_dir or self._models_dir / self.PUNC_MODEL_DIR
        speaker_model_path = self._speaker_model_dir or self._models_dir / self.SPEAKER_MODEL_DIR

        if not asr_model_path.exists():
            raise FileNotFoundError(f"FunASR ASR model directory does not exist: {asr_model_path}")

        kwargs: dict[str, object] = {
            "model": str(asr_model_path),
            "device": self._device,
            "disable_update": True,
        }
        if vad_model_path.exists():
            kwargs["vad_model"] = str(vad_model_path)
        if punc_model_path.exists():
            kwargs["punc_model"] = str(punc_model_path)
        if self._enable_speakers and speaker_model_path.exists():
            kwargs["spk_model"] = str(speaker_model_path)
        return kwargs

    @classmethod
    def parse_result(
        cls,
        result: object,
        record_id: str,
        language: Language = Language.AUTO,
    ) -> TranscriptDocument:
        result_data = cls._first_result(result)
        segments: list[TranscriptSegment] = []

        sentence_info = result_data.get("sentence_info") if isinstance(result_data, dict) else None
        if isinstance(sentence_info, list):
            for item in sentence_info:
                if not isinstance(item, dict):
                    continue
                segment = cls._parse_sentence(item)
                if segment:
                    segments.append(segment)
        elif isinstance(result_data, dict):
            text = cls.clean_text(str(result_data.get("text", "")))
            if text:
                segments.append(
                    TranscriptSegment(
                        id=str(uuid4()),
                        text=text,
                        start_time=0.0,
                        end_time=0.0,
                    )
                )

        return TranscriptDocument(record_id=record_id, language=language, segments=segments)

    @classmethod
    def _parse_sentence(cls, item: dict[str, object]) -> TranscriptSegment | None:
        text = cls.clean_text(str(item.get("text", "")))
        if not text:
            return None

        speaker_id = None
        speaker_value = item.get("spk") if item.get("spk") is not None else item.get("spk_id")
        if speaker_value is not None:
            speaker_id = f"S{speaker_value + 1}" if isinstance(speaker_value, int) else str(speaker_value)

        return TranscriptSegment(
            id=str(uuid4()),
            text=text,
            start_time=cls._milliseconds_to_seconds(item.get("start", 0)),
            end_time=cls._milliseconds_to_seconds(item.get("end", 0)),
            speaker_id=speaker_id,
        )

    @staticmethod
    def _first_result(result: object) -> dict[str, object]:
        if isinstance(result, list) and result and isinstance(result[0], dict):
            return result[0]
        if isinstance(result, dict):
            return result
        return {}

    @staticmethod
    def _milliseconds_to_seconds(value: object) -> float:
        try:
            return float(value) / 1000.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r"<\s*\|\s*[^|]+\s*\|\s*>", "", text)
        return re.sub(r"\s+", " ", text).strip()
