from __future__ import annotations

from pathlib import Path

import pytest

from meeting_note.core.media import MediaKind, detect_media_kind, is_supported_media_file, validate_media_file


def test_detect_media_kind_handles_audio_and_video_extensions():
    assert detect_media_kind(Path("demo.MP3")) == MediaKind.AUDIO
    assert detect_media_kind(Path("demo.mp4")) == MediaKind.VIDEO
    assert detect_media_kind(Path("demo.txt")) is None


def test_validate_media_file_rejects_missing_file(tmp_path):
    missing_file = tmp_path / "missing.mp3"

    with pytest.raises(FileNotFoundError):
        validate_media_file(missing_file)


def test_validate_media_file_accepts_supported_existing_file(tmp_path):
    audio_file = tmp_path / "demo.wav"
    audio_file.write_bytes(b"fake")

    media_file = validate_media_file(audio_file)

    assert is_supported_media_file(audio_file) is True
    assert media_file.kind == MediaKind.AUDIO
