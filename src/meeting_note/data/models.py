from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path


class RecordStatus(str, Enum):
    NEW = "new"
    PREPROCESSING = "preprocessing"
    TRANSCRIBING = "transcribing"
    READY = "ready"
    FAILED = "failed"


class ModelType(str, Enum):
    ASR = "asr"
    LLM_SUMMARY = "llm_summary"
    LLM_TRANSLATION = "llm_translation"


class ModelProvider(str, Enum):
    FUNASR = "funasr"
    LLAMA_CPP = "llama_cpp"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    PREPROCESS_AUDIO = "preprocess_audio"
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"
    SUMMARIZE = "summarize"


@dataclass(frozen=True)
class Record:
    id: str
    title: str
    status: RecordStatus
    created_at: datetime
    updated_at: datetime
    original_file_path: Path | None = None
    processed_audio_path: Path | None = None
    source_language: str | None = None
    duration_seconds: float = 0.0
    has_transcript: bool = False
    has_translation: bool = False
    has_summary: bool = False
    has_speakers: bool = False


@dataclass(frozen=True)
class LocalModel:
    id: str
    name: str
    path: Path
    model_type: ModelType
    provider: ModelProvider
    created_at: datetime
    file_size: int = 0
    quantization: str | None = None
    context_length: int | None = None
    status: str = "unknown"
    last_checked_at: datetime | None = None


@dataclass(frozen=True)
class TaskRecord:
    id: str
    task_type: TaskType
    status: TaskStatus
    progress: int
    record_id: str | None = None
    message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


def now_utc() -> datetime:
    return datetime.now(UTC)
