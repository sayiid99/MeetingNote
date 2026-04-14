from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from meeting_note.core.media import validate_media_file


@dataclass(frozen=True)
class AudioProcessingOptions:
    sample_rate: int = 16000
    channels: int = 1
    codec: str = "pcm_s16le"
    overwrite: bool = True


@dataclass(frozen=True)
class AudioProcessingResult:
    source_path: Path
    output_path: Path


class AudioProcessor:
    def __init__(self, ffmpeg_path: Path | str = "ffmpeg"):
        self._ffmpeg_path = str(ffmpeg_path)

    def preprocess(
        self,
        input_path: Path,
        output_path: Path,
        options: AudioProcessingOptions | None = None,
    ) -> AudioProcessingResult:
        media_file = validate_media_file(input_path)
        options = options or AudioProcessingOptions()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = self.build_command(media_file.path, output_path, options)
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        if completed.returncode != 0:
            raise RuntimeError(self._format_ffmpeg_error(completed.stderr))
        if not output_path.exists():
            raise RuntimeError(f"ffmpeg finished but output was not created: {output_path}")
        if output_path.stat().st_size < 100:
            raise RuntimeError("ffmpeg output is empty or too small to contain usable audio")

        return AudioProcessingResult(source_path=media_file.path, output_path=output_path)

    def build_command(
        self,
        input_path: Path,
        output_path: Path,
        options: AudioProcessingOptions | None = None,
    ) -> list[str]:
        options = options or AudioProcessingOptions()
        command = [self._ffmpeg_path]
        if options.overwrite:
            command.append("-y")
        command.extend(
            [
                "-i",
                str(input_path),
                "-vn",
                "-ar",
                str(options.sample_rate),
                "-ac",
                str(options.channels),
                "-acodec",
                options.codec,
                str(output_path),
            ]
        )
        return command

    @staticmethod
    def _format_ffmpeg_error(stderr: str) -> str:
        normalized = stderr.lower()
        if "does not contain any stream" in normalized or "no audio" in normalized:
            return "The selected video does not contain an audio track."
        if "invalid data found" in normalized:
            return "The media file is damaged or unsupported by ffmpeg."
        if "permission denied" in normalized or "access is denied" in normalized:
            return "The media file or output path is currently unavailable due to permissions."

        meaningful_lines = [
            line.strip()
            for line in stderr.splitlines()
            if line.strip()
            and not line.startswith("ffmpeg version")
            and not line.startswith("built with")
            and not line.startswith("  ")
        ]
        detail = "\n".join(meaningful_lines[-3:]) if meaningful_lines else stderr[:300]
        return f"ffmpeg failed: {detail}"
