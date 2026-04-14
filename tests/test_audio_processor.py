from __future__ import annotations

from pathlib import Path

from meeting_note.core.audio_processor import AudioProcessingOptions, AudioProcessor


def test_build_command_converts_media_to_16k_mono_wav():
    processor = AudioProcessor(ffmpeg_path=Path("ffmpeg.exe"))

    command = processor.build_command(Path("input.mp4"), Path("output.wav"))

    assert command == [
        "ffmpeg.exe",
        "-y",
        "-i",
        "input.mp4",
        "-vn",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-acodec",
        "pcm_s16le",
        "output.wav",
    ]


def test_build_command_accepts_custom_options():
    processor = AudioProcessor()
    options = AudioProcessingOptions(sample_rate=24000, channels=2, codec="pcm_s24le", overwrite=False)

    command = processor.build_command(Path("input.wav"), Path("output.wav"), options)

    assert "-y" not in command
    assert command[command.index("-ar") + 1] == "24000"
    assert command[command.index("-ac") + 1] == "2"
    assert command[command.index("-acodec") + 1] == "pcm_s24le"


def test_format_ffmpeg_error_maps_common_failures():
    assert "audio track" in AudioProcessor._format_ffmpeg_error("No audio stream found").lower()
    assert "damaged" in AudioProcessor._format_ffmpeg_error("Invalid data found").lower()
    assert "permissions" in AudioProcessor._format_ffmpeg_error("Permission denied").lower()
