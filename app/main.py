"""FastAPI server: API + bundled Telegram Mini App."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.bonds_service import Bond, get_top_bonds_async
from app.feedback_routes import router as feedback_router
from app.feedback_routes import telegram_router as telegram_feedback_router
from app.public_routes import router as public_router
from app.security import SecurityHeadersMiddleware, enforce_rate_limit
from application.services.feedback_workflow import FeedbackWorkflow
from config.settings import settings
from infrastructure.persistence.feedback_sqlite import FeedbackSqliteRepository
from infrastructure.telegram.bot_api import TelegramBotApi

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize shared clients and repositories."""
    db_path = Path(settings.feedback_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    upload_dir = Path(settings.feedback_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    repo = FeedbackSqliteRepository(db_path)
    await asyncio.to_thread(repo.init_schema)

    client = httpx.AsyncClient()
    token = (settings.telegram_feedback_bot_token or "").strip()
    bot = TelegramBotApi(token, client) if token else None
    workflow = FeedbackWorkflow(settings=settings, repo=repo, feedback_bot=bot)

    app.state.http_client = client
    app.state.feedback_repo = repo
    app.state.feedback_bot = bot
    app.state.feedback_workflow = workflow
    yield
    await client.aclose()


app = FastAPI(
    title="Bond Screener MOEX",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list())
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.include_router(public_router)
app.include_router(feedback_router)
app.include_router(telegram_feedback_router)


def _parse_decimal(raw_value: str | None, field_name: str) -> Decimal | None:
    if raw_value is None:
        return None
    try:
        return Decimal(raw_value)
    except InvalidOperation as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid numeric value for `{field_name}`.",
        ) from exc


@app.get("/api/bonds", response_model=list[Bond])
async def bonds(
    request: Request,
    min_emitter_rating: str | None = Query(default=None),
    min_bond_rating: str | None = Query(default=None),
    currency: str | None = Query(default=None, pattern="^(RUB|CNY)$"),
    investor_profile: str | None = Query(default=None, pattern="^(QUAL|NONQUAL)$"),
    horizon_days: int | None = Query(default=None, ge=1, le=3650),
    limit: int = Query(default=settings.limit, ge=1, le=100),
    min_annual_yield: str | None = Query(default=None),
) -> list[Bond]:
    """Return bond screener results as JSON for the Mini App."""
    enforce_rate_limit(
        request,
        bucket="api_bonds",
        limit=settings.api_bonds_rate_limit_per_minute,
    )
    parsed_min_annual_yield = _parse_decimal(min_annual_yield, "min_annual_yield")
    return await get_top_bonds_async(
        horizon_days=horizon_days,
        limit=limit,
        min_annual_yield=parsed_min_annual_yield,
        min_bond_rating=min_bond_rating,
        min_emitter_rating=min_emitter_rating,
        currency=currency,
        investor_profile=investor_profile,
    )


assets_dir = FRONTEND_DIST / "assets"
if assets_dir.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(assets_dir)),
        name="miniapp_assets",
    )


def _serve_spa_file(full_path: str) -> FileResponse:
    dist = FRONTEND_DIST.resolve()
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = (FRONTEND_DIST / full_path).resolve()
    try:
        candidate.relative_to(dist)
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found") from None
    if candidate.is_file():
        return FileResponse(candidate)
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(
            status_code=503,
            detail="Mini App is not built. Run: cd frontend && npm ci && npm run build",
        )
    return FileResponse(index)


@app.get("/")
async def spa_root() -> FileResponse:
    """Telegram Mini App entry point."""
    return _serve_spa_file("")


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str) -> FileResponse:
    """Static files from dist or SPA fallback."""
    return _serve_spa_file(full_path)
