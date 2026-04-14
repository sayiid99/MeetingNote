from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    project_root: Path
    data_dir: Path
    records_dir: Path
    logs_dir: Path
    models_dir: Path
    database_path: Path

    @classmethod
    def from_project_root(cls, project_root: Path) -> "AppPaths":
        root = project_root.resolve()
        data_dir = root / "data"
        return cls(
            project_root=root,
            data_dir=data_dir,
            records_dir=data_dir / "records",
            logs_dir=data_dir / "logs",
            models_dir=root / "models",
            database_path=data_dir / "database.sqlite",
        )

    def ensure_runtime_dirs(self) -> None:
        for path in (self.data_dir, self.records_dir, self.logs_dir, self.models_dir):
            path.mkdir(parents=True, exist_ok=True)

    def record_dir(self, record_id: str) -> Path:
        return self.records_dir / record_id

    def processed_audio_path(self, record_id: str) -> Path:
        return self.record_dir(record_id) / "audio.processed.wav"

    def exports_dir(self, record_id: str) -> Path:
        return self.record_dir(record_id) / "exports"
