from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  original_file_path TEXT,
  processed_audio_path TEXT,
  source_language TEXT,
  duration_seconds REAL DEFAULT 0,
  status TEXT NOT NULL,
  has_transcript INTEGER DEFAULT 0,
  has_translation INTEGER DEFAULT 0,
  has_summary INTEGER DEFAULT 0,
  has_speakers INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS models (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  path TEXT NOT NULL,
  model_type TEXT NOT NULL,
  provider TEXT NOT NULL,
  file_size INTEGER DEFAULT 0,
  quantization TEXT,
  context_length INTEGER,
  status TEXT NOT NULL DEFAULT 'unknown',
  created_at TEXT NOT NULL,
  last_checked_at TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  record_id TEXT,
  task_type TEXT NOT NULL,
  status TEXT NOT NULL,
  progress INTEGER DEFAULT 0,
  message TEXT,
  started_at TEXT,
  finished_at TEXT,
  error TEXT
);

CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""


def initialize_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as conn:
        conn.executescript(SCHEMA)
