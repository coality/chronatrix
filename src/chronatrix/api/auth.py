from __future__ import annotations

import hashlib
import hmac
import os
import time
from collections import deque
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request

from .db import DBClient


@dataclass
class APIKeyPrincipal:
    key_id: int
    prefix: str
    rate_limit_rpm: int


class SlidingWindowRateLimiter:
    def __init__(self, default_rpm: int = 60) -> None:
        self.default_rpm = default_rpm
        self._events: dict[str, deque[float]] = {}

    def allow(self, subject: str, rpm: int | None = None) -> bool:
        now = time.time()
        limit = rpm or self.default_rpm
        window = self._events.setdefault(subject, deque())
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            return False
        window.append(now)
        return True


class APIKeyService:
    def __init__(self, db: DBClient | None = None, default_rpm: int = 60) -> None:
        self.db = db or DBClient()
        self.secret = os.getenv("CHRONATRIX_KEY_SECRET", "")
        self.key_limiter = SlidingWindowRateLimiter(default_rpm=default_rpm)
        self.ip_limiter = SlidingWindowRateLimiter(default_rpm=default_rpm * 2)

    def _hash(self, raw_key: str) -> bytes:
        return hmac.new(self.secret.encode("utf-8"), raw_key.encode("utf-8"), hashlib.sha256).digest()

    def authenticate(self, raw_key: str) -> APIKeyPrincipal:
        if not self.secret:
            raise HTTPException(status_code=500, detail="api_key_secret_missing")
        row = self.db.find_api_key(self._hash(raw_key))
        if not row or row.get("status") != "active":
            raise HTTPException(status_code=401, detail="invalid_api_key")
        principal = APIKeyPrincipal(
            key_id=int(row["id"]),
            prefix=str(row["key_prefix"]),
            rate_limit_rpm=int(row.get("rate_limit_rpm") or self.key_limiter.default_rpm),
        )
        return principal

    def enforce_limits(self, principal: APIKeyPrincipal, ip: str) -> None:
        if not self.key_limiter.allow(f"key:{principal.key_id}", principal.rate_limit_rpm):
            raise HTTPException(status_code=429, detail="api_key_rate_limited")
        if not self.ip_limiter.allow(f"ip:{ip}"):
            raise HTTPException(status_code=429, detail="ip_rate_limited")


def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> APIKeyPrincipal:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="missing_api_key")
    svc: APIKeyService = request.app.state.api_key_service
    principal = svc.authenticate(x_api_key)
    ip = request.client.host if request.client else "unknown"
    svc.enforce_limits(principal, ip)
    svc.db.touch_api_key(principal.key_id)
    return principal
