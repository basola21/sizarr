import sqlite3
import logging
from pathlib import Path

import config

logger = logging.getLogger(__name__)

_DB_PATH = Path(config.CACHE_PATH) / "sizarr.db"


def _connect() -> sqlite3.Connection:
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


def mark_transcoded(path: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO transcoded (path) VALUES (?)",
            (path,),
        )
        conn.commit()
