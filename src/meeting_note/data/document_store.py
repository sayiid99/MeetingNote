from __future__ import annotations

import json
from pathlib import Path

from meeting_note.core.contracts import (
    Language,
    TranscriptDocument,
    TranscriptSegment,
    TranslationDocument,
    TranslationMode,
)
from meeting_note.infra.paths import AppPaths


class TranscriptStore:
    def __init__(self, paths: AppPaths):
        self._paths = paths

    def transcript_path(self, record_id: str) -> Path:
        return self._paths.record_dir(record_id) / "transcript.json"

    def save(self, transcript: TranscriptDocument) -> Path:
        path = self.transcript_path(transcript.record_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "record_id": transcript.record_id,
            "language": transcript.language.value,
            "segments": [
                {
                    "id": segment.id,
                    "text": segment.text,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "speaker_id": segment.speaker_id,
                    "is_edited": segment.is_edited,
                }
                for segment in transcript.segments
            ],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, record_id: str) -> TranscriptDocument | None:
        path = self.transcript_path(record_id)
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        return TranscriptDocument(
            record_id=str(data["record_id"]),
            language=Language(str(data.get("language", Language.AUTO.value))),
            segments=[
                TranscriptSegment(
                    id=str(item["id"]),
                    text=str(item["text"]),
                    start_time=float(item.get("start_time", 0)),
                    end_time=float(item.get("end_time", 0)),
                    speaker_id=str(item["speaker_id"]) if item.get("speaker_id") else None,
                    is_edited=bool(item.get("is_edited", False)),
                )
                for item in data.get("segments", [])
            ],
        )


class TranslationStore:
    def __init__(self, paths: AppPaths):
        self._paths = paths

    def translation_path(self, record_id: str) -> Path:
        return self._paths.record_dir(record_id) / "translation.json"

    def save(self, translation: TranslationDocument) -> Path:
        path = self.translation_path(translation.record_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "record_id": translation.record_id,
            "source_language": translation.source_language.value,
            "target_language": translation.target_language.value,
            "mode": translation.mode.value,
            "translated_text": translation.translated_text,
            "bilingual_text": translation.bilingual_text,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, record_id: str) -> TranslationDocument | None:
        path = self.translation_path(record_id)
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        return TranslationDocument(
            record_id=str(data["record_id"]),
            source_language=Language(str(data.get("source_language", Language.AUTO.value))),
            target_language=Language(str(data.get("target_language", Language.AUTO.value))),
            mode=TranslationMode(str(data.get("mode", TranslationMode.STANDARD.value))),
            translated_text=str(data.get("translated_text", "")),
            bilingual_text=str(data["bilingual_text"]) if data.get("bilingual_text") else None,
        )


class SummaryStore:
    def __init__(self, paths: AppPaths):
        self._paths = paths

    def summary_path(self, record_id: str) -> Path:
        return self._paths.record_dir(record_id) / "summary.json"

    def save(self, record_id: str, summary_text: str) -> Path:
        path = self.summary_path(record_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"record_id": record_id, "summary_text": summary_text}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, record_id: str) -> str | None:
        path = self.summary_path(record_id)
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        return str(data.get("summary_text", ""))
