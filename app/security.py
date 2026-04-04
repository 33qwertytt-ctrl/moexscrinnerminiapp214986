"""HTTP security helpers and lightweight in-memory rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any, cast

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


def _build_content_security_policy() -> str:
    directives = {
        "default-src": "'self'",
        "script-src": "'self' https://telegram.org https://*.telegram.org",
        "style-src": "'self' 'unsafe-inline'",
        "img-src": "'self' data: blob: https://telegram.org https://*.telegram.org",
        "connect-src": "'self'",
        "font-src": "'self'",
        "object-src": "'none'",
        "base-uri": "'self'",
        "form-action": "'self'",
        "frame-ancestors": "'self' https://telegram.org https://*.telegram.org https://web.telegram.org",
    }
    return "; ".join(f"{key} {value}" for key, value in directives.items())


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach a conservative set of browser security headers."""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._csp = _build_content_security_policy()

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response = cast(Response, await call_next(request))
        response.headers.setdefault("Content-Security-Policy", self._csp)
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers.setdefault("Pragma", "no-cache")
        return response


class InMemoryRateLimiter:
    """Small process-local sliding window rate limiter."""

    def __init__(self) -> None:
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, bucket: str, key: str, limit: int, window_seconds: int) -> int | None:
        now = time.monotonic()
        event_key = (bucket, key)
        with self._lock:
            window = self._events[event_key]
            while window and now - window[0] >= window_seconds:
                window.popleft()
            if len(window) >= limit:
                retry_after = max(1, int(window_seconds - (now - window[0])) + 1)
                return retry_after
            window.append(now)
        return None


rate_limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """Resolve client IP, preferring X-Forwarded-For when present."""
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        first = forwarded_for.split(",", 1)[0].strip()
        if first:
            return first
    if request.client is not None:
        return request.client.host
    return "unknown"


def enforce_rate_limit(
    request: Request,
    *,
    bucket: str,
    limit: int,
    window_seconds: int = 60,
) -> None:
    """Raise 429 when the caller exceeds the configured request budget."""
    retry_after = rate_limiter.hit(bucket, get_client_ip(request), limit, window_seconds)
    if retry_after is None:
        return
    raise HTTPException(
        status_code=429,
        detail="Too many requests. Please retry later.",
        headers={"Retry-After": str(retry_after)},
    )


def enforce_content_length(request: Request, *, max_bytes: int) -> None:
    """Fail fast when Content-Length is larger than allowed."""
    raw_length = request.headers.get("Content-Length")
    if raw_length is None:
        return
    try:
        parsed_length = int(raw_length)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Content-Length header.") from None
    if parsed_length > max_bytes:
        raise HTTPException(status_code=413, detail="Request body is too large.")
