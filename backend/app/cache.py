"""SQLite caching engine: GitHub API responses and user settings."""
import json
import sqlite3
import time

from .config import CACHE_TTL_SECONDS, DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS api_cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, fetched_at REAL NOT NULL)"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return conn


def get(key: str):
    """Return cached value if it exists and is younger than the TTL, else None."""
    with _connect() as conn:
        row = conn.execute("SELECT value, fetched_at FROM api_cache WHERE key = ?", (key,)).fetchone()
    if row and time.time() - row[1] < CACHE_TTL_SECONDS:
        return json.loads(row[0])
    return None


def set(key: str, value) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO api_cache (key, value, fetched_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), time.time()),
        )


def get_setting(key: str, default=None):
    with _connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return json.loads(row[0]) if row else default


def set_setting(key: str, value) -> None:
    with _connect() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, json.dumps(value)))
