from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class MediaKind(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"


SUPPORTED_AUDIO_FORMATS = frozenset({".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"})
SUPPORTED_VIDEO_FORMATS = frozenset({".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"})


@dataclass(frozen=True)
class MediaFile:
    path: Path
    kind: MediaKind

    @property
    def display_name(self) -> str:
        return self.path.name


def detect_media_kind(path: Path) -> MediaKind | None:
    suffix = path.suffix.lower()
    if suffix in SUPPORTED_AUDIO_FORMATS:
        return MediaKind.AUDIO
    if suffix in SUPPORTED_VIDEO_FORMATS:
        return MediaKind.VIDEO
    return None


def is_supported_media_file(path: Path) -> bool:
    return detect_media_kind(path) is not None


def validate_media_file(path: Path) -> MediaFile:
    if not path.exists():
        raise FileNotFoundError(f"Media file does not exist: {path}")

    kind = detect_media_kind(path)
    if kind is None:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_FORMATS | SUPPORTED_VIDEO_FORMATS))
        raise ValueError(f"Unsupported media format: {path.suffix}. Supported formats: {supported}")

    return MediaFile(path=path, kind=kind)


def qt_file_dialog_filter() -> str:
    all_formats = sorted(SUPPORTED_AUDIO_FORMATS | SUPPORTED_VIDEO_FORMATS)
    audio_formats = sorted(SUPPORTED_AUDIO_FORMATS)
    video_formats = sorted(SUPPORTED_VIDEO_FORMATS)
    return ";;".join(
        [
            "Media files ({} )".format(" ".join(f"*{suffix}" for suffix in all_formats)),
            "Audio files ({} )".format(" ".join(f"*{suffix}" for suffix in audio_formats)),
            "Video files ({} )".format(" ".join(f"*{suffix}" for suffix in video_formats)),
            "All files (*.*)",
        ]
    )
