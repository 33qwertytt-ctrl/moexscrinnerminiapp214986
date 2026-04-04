"""HTTP API for Mini App feedback and Telegram webhook processing."""

from __future__ import annotations

import json
from typing import Annotated, cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.security import enforce_content_length, enforce_rate_limit
from application.services.feedback_workflow import FeedbackWorkflow
from config.settings import settings
from utils.telegram_webapp import TelegramWebAppAuthError

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


def get_feedback_workflow(request: Request) -> FeedbackWorkflow:
    workflow = getattr(request.app.state, "feedback_workflow", None)
    if workflow is None:
        raise HTTPException(status_code=503, detail="Feedback workflow is not initialized.")
    return cast(FeedbackWorkflow, workflow)


WorkflowDep = Annotated[FeedbackWorkflow, Depends(get_feedback_workflow)]


async def _read_upload_limited(
    upload: UploadFile,
    max_bytes: int,
) -> tuple[bytes | None, str | None]:
    if upload.filename in (None, ""):
        return None, None
    chunks: list[bytes] = []
    total = 0
    while True:
        block = await upload.read(64 * 1024)
        if not block:
            break
        total += len(block)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum size of {max_bytes} bytes.",
            )
        chunks.append(block)
    return b"".join(chunks), upload.filename


@router.post("/submit")
async def submit_feedback(
    request: Request,
    workflow: WorkflowDep,
    init_data: Annotated[str, Form()],
    message: Annotated[str, Form()] = "",
    file: Annotated[UploadFile | None, File()] = None,
) -> dict[str, int | str]:
    """Accept feedback from Telegram Mini App."""
    enforce_rate_limit(
        request,
        bucket="feedback_submit",
        limit=settings.feedback_submit_rate_limit_per_minute,
    )
    enforce_content_length(
        request,
        max_bytes=settings.feedback_max_attachment_bytes + 256_000,
    )

    max_bytes = settings.feedback_max_attachment_bytes
    file_bytes: bytes | None = None
    filename: str | None = None
    content_type: str | None = None
    if file is not None:
        file_bytes, filename = await _read_upload_limited(file, max_bytes)
        content_type = file.content_type

    try:
        feedback_id = await workflow.submit_from_miniapp(
            init_data=init_data,
            message_text=message,
            file_bytes=file_bytes,
            original_filename=filename,
            content_type=content_type,
        )
    except TelegramWebAppAuthError as exc:
        raise HTTPException(status_code=401, detail="Invalid Telegram initData.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"id": feedback_id, "status": "ok"}


@router.post("/pair")
async def pair_feedback_user(
    request: Request,
    workflow: WorkflowDep,
    init_data: Annotated[str, Form()],
    pairing_code: Annotated[str, Form()],
) -> dict[str, str]:
    """Bind Mini App Telegram user to operator via one-time code from /pair."""
    enforce_rate_limit(
        request,
        bucket="feedback_pair",
        limit=settings.feedback_pair_rate_limit_per_minute,
    )
    enforce_content_length(request, max_bytes=16_384)
    try:
        await workflow.pair_miniapp_user(init_data=init_data, pairing_code=pairing_code)
    except TelegramWebAppAuthError as exc:
        raise HTTPException(status_code=401, detail="Invalid Telegram initData.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "paired"}


telegram_router = APIRouter(prefix="/api/telegram", tags=["telegram"])


@telegram_router.post("/webhook/feedback")
async def telegram_feedback_webhook(request: Request) -> dict[str, str]:
    """Telegram Bot API webhook for the feedback operator bot."""
    secret = settings.telegram_feedback_webhook_secret
    if secret:
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header != secret:
            raise HTTPException(status_code=403, detail="Invalid webhook secret.")
    enforce_content_length(request, max_bytes=settings.feedback_webhook_max_body_bytes)

    workflow: FeedbackWorkflow | None = getattr(request.app.state, "feedback_workflow", None)
    if workflow is None:
        raise HTTPException(status_code=503, detail="Feedback workflow is not initialized.")

    try:
        update = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body.") from exc

    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="Update must be a JSON object.")

    await workflow.process_telegram_update(update)
    return {"ok": "true"}
