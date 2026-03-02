from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.parse import urlparse

import pymysql

LOGGER = logging.getLogger(__name__)


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DBClient:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.getenv("CHRONATRIX_DB_DSN")

    def _conn_kwargs(self) -> dict[str, object]:
        if not self.dsn:
            raise RuntimeError("CHRONATRIX_DB_DSN is not configured")
        parsed = urlparse(self.dsn)
        if parsed.scheme != "mysql":
            raise RuntimeError("CHRONATRIX_DB_DSN must use mysql://")
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 3306,
            "user": parsed.username,
            "password": parsed.password,
            "database": parsed.path.lstrip("/"),
            "autocommit": True,
            "cursorclass": pymysql.cursors.DictCursor,
            "connect_timeout": 1,
            "read_timeout": 3,
            "write_timeout": 3,
            "charset": "utf8mb4",
        }

    @contextmanager
    def connection(self):
        conn = pymysql.connect(**self._conn_kwargs())
        try:
            yield conn
        finally:
            conn.close()

    def get_cache(self, cache_key: str) -> tuple[dict[str, object], datetime] | None:
        try:
            with self.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT payload_json, expires_at
                        FROM api_cache
                        WHERE cache_key=%s AND expires_at > UTC_TIMESTAMP()
                        """,
                        (cache_key,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    payload = json.loads(row["payload_json"])
                    expires_at = row["expires_at"]
                    return payload, expires_at
        except Exception:
            LOGGER.exception("db_cache_read_failed", extra={"cache_key": cache_key})
            return None

    def set_cache(self, cache_key: str, payload: dict[str, object], expires_at: datetime) -> None:
        try:
            with self.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO api_cache(cache_key, payload_json, expires_at, created_at, updated_at)
                        VALUES(%s, %s, %s, UTC_TIMESTAMP(), UTC_TIMESTAMP())
                        ON DUPLICATE KEY UPDATE
                          payload_json=VALUES(payload_json),
                          expires_at=VALUES(expires_at),
                          updated_at=UTC_TIMESTAMP()
                        """,
                        (cache_key, json.dumps(payload), expires_at),
                    )
        except Exception:
            LOGGER.exception("db_cache_write_failed", extra={"cache_key": cache_key})

    def find_api_key(self, key_hash: bytes) -> dict[str, object] | None:
        try:
            with self.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, key_prefix, label, status, rate_limit_rpm
                        FROM api_keys
                        WHERE key_hash=%s
                        LIMIT 1
                        """,
                        (key_hash,),
                    )
                    return cur.fetchone()
        except Exception:
            LOGGER.exception("db_api_key_lookup_failed")
            return None

    def touch_api_key(self, key_id: int) -> None:
        try:
            with self.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE api_keys SET last_used_at=UTC_TIMESTAMP() WHERE id=%s",
                        (key_id,),
                    )
        except Exception:
            LOGGER.exception("db_api_key_touch_failed", extra={"key_id": key_id})
