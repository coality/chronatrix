from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from .db import DBClient, utcnow_naive


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[datetime, dict[str, object]]] = {}

    def get(self, key: str) -> tuple[dict[str, object], int] | None:
        item = self._store.get(key)
        if not item:
            return None
        expires_at, value = item
        now = utcnow_naive()
        if expires_at <= now:
            self._store.pop(key, None)
            return None
        age = int((expires_at - now).total_seconds())
        return value, age

    def set(self, key: str, value: dict[str, object], ttl_seconds: int) -> None:
        self._store[key] = (utcnow_naive() + timedelta(seconds=ttl_seconds), value)


class MultiLevelCache:
    def __init__(self, db: DBClient | None = None) -> None:
        self.mem = TTLCache()
        self.db = db or DBClient()
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_or_set(
        self,
        key: str,
        ttl_seconds: int,
        fetcher: Callable[[], Awaitable[dict[str, object]]],
    ) -> tuple[dict[str, object], bool, int | None]:
        mem_hit = self.mem.get(key)
        if mem_hit:
            payload, age_s = mem_hit
            return payload, True, age_s

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            mem_hit = self.mem.get(key)
            if mem_hit:
                payload, age_s = mem_hit
                return payload, True, age_s

            db_hit = self.db.get_cache(key)
            if db_hit:
                payload, expires_at = db_hit
                age_s = int((expires_at - utcnow_naive()).total_seconds())
                self.mem.set(key, payload, max(age_s, 1))
                return payload, True, age_s

            payload = await fetcher()
            self.mem.set(key, payload, ttl_seconds)
            self.db.set_cache(key, payload, utcnow_naive() + timedelta(seconds=ttl_seconds))
            return payload, False, None
