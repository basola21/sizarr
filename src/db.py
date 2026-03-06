import sqlite3
import logging
from pathlib import Path

import config

logger = logging.getLogger(__name__)

_DB_PATH = Path(config.CACHE_PATH) / "sizarr.db"

# Each migration is (step, sql). Each step must have a unique number.
# ADD COLUMN is always safe in SQLite — never touches existing data.
_MIGRATIONS = [
    (1, "ALTER TABLE transcoded ADD COLUMN size_before INTEGER"),
    (2, "ALTER TABLE transcoded ADD COLUMN size_after INTEGER"),
    (3, "ALTER TABLE transcoded ADD COLUMN codec_before TEXT"),
    (4, "ALTER TABLE transcoded ADD COLUMN duration_seconds REAL"),
]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transcoded (
            path TEXT PRIMARY KEY,
            transcoded_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    _run_migrations(conn)
    return conn


def _run_migrations(conn: sqlite3.Connection) -> None:
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_version")}

    for step, sql in _MIGRATIONS:
        if step in applied:
            continue
        logger.info(f"Applying schema migration step {step}")
        try:
            conn.execute(sql)
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                raise
            logger.warning(f"Column already exists, skipping: {e}")
        conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (?)", (step,))

    conn.commit()


def is_transcoded(path: str) -> bool:
    with _connect() as conn:
        row = conn.execute("SELECT 1 FROM transcoded WHERE path = ?", (path,)).fetchone()
        return row is not None


def mark_transcoded(
    path: str,
    *,
    size_before: int | None = None,
    size_after: int | None = None,
    codec_before: str | None = None,
    duration_seconds: float | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO transcoded
               (path, size_before, size_after, codec_before, duration_seconds)
               VALUES (?, ?, ?, ?, ?)""",
            (path, size_before, size_after, codec_before, duration_seconds),
        )
        conn.commit()
