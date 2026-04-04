from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.security import InMemoryRateLimiter, SecurityHeadersMiddleware


def test_security_headers_middleware_adds_headers() -> None:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "true"}

    response = TestClient(app).get("/api/ping")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    assert "content-security-policy" in response.headers


def test_rate_limiter_blocks_after_limit() -> None:
    limiter = InMemoryRateLimiter()

    assert limiter.hit("tests", "127.0.0.1", 2, 60) is None
    assert limiter.hit("tests", "127.0.0.1", 2, 60) is None
    retry_after = limiter.hit("tests", "127.0.0.1", 2, 60)

    assert retry_after is not None
    assert retry_after >= 1
