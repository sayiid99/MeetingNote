from __future__ import annotations

import sqlite3

from meeting_note.data.database import initialize_database


def test_initialize_database_creates_core_tables(tmp_path):
    database_path = tmp_path / "database.sqlite"

    initialize_database(database_path)

    with sqlite3.connect(database_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }

    assert {"records", "models", "tasks", "app_settings"}.issubset(table_names)
