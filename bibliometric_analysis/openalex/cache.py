"""SQLite read-through HTTP cache for OpenAlex API responses."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode


def cache_key(url: str, params: dict | None) -> str:
    q = urlencode(sorted((params or {}).items()))
    return hashlib.sha256(f"{url}?{q}".encode("utf-8")).hexdigest()


class HTTPCache:
    """Thread-safe SQLite cache keyed by URL + sorted query parameters."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS url_cache(
                    key TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    params TEXT,
                    json TEXT NOT NULL,
                    ts REAL NOT NULL
                )
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_url_cache_ts ON url_cache(ts)")
            con.commit()

    def get(self, key: str) -> Optional[dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as con:
            row = con.execute("SELECT json FROM url_cache WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else None

    def set(self, key: str, url: str, params: dict, payload: dict) -> None:
        with self._lock, sqlite3.connect(self.db_path) as con:
            con.execute(
                "REPLACE INTO url_cache(key,url,params,json,ts) VALUES (?,?,?,?,?)",
                (key, url, json.dumps(params, sort_keys=True), json.dumps(payload), time.time()),
            )
            con.commit()

    def clear(self) -> None:
        with self._lock, sqlite3.connect(self.db_path) as con:
            con.execute("DELETE FROM url_cache")
            con.commit()
