import sqlite3
import logging
from pathlib import Path

from yoyo import read_migrations, get_backend

import config

logger = logging.getLogger(__name__)

_DB_PATH = Path(config.CACHE_PATH) / "sizarr.db"
_MIGRATIONS_PATH = Path(__file__).parent / "migrations"


def _apply_migrations() -> None:
    backend = get_backend(f"sqlite:///{_DB_PATH}")
    migrations = read_migrations(str(_MIGRATIONS_PATH))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))


def _connect() -> sqlite3.Connection:
    _apply_migrations()
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transcoded (
            path TEXT PRIMARY KEY,
            transcoded_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


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
