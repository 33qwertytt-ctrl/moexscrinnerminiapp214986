"""Public settings for the Mini App without secrets."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from config.settings import settings

router = APIRouter(prefix="/api", tags=["public"])


class PublicConfigResponse(BaseModel):
    """Non-secret values that help the frontend validate input."""

    public_domain: str = Field(description="Primary public domain of the application.")
    public_ipv4: str = Field(default="", description="Configured IPv4 hint, if present.")
    public_ipv6: str = Field(default="", description="Configured IPv6 hint, if present.")
    feedback_max_attachment_bytes: int = Field(
        description="Maximum feedback attachment size in bytes.",
    )
    feedback_max_message_chars: int = Field(
        description="Maximum feedback message length.",
    )
    feedback_allowed_mime_types: list[str] = Field(
        description="Allowed MIME types for feedback attachments.",
    )
    feedback_pairing_code_length: int = Field(
        description="One-time pairing code length.",
    )


@router.get("/public-config", response_model=PublicConfigResponse)
def get_public_config() -> PublicConfigResponse:
    """Return public network hints and frontend validation limits."""
    return PublicConfigResponse(
        public_domain=settings.public_domain.strip() or "localhost",
        public_ipv4=settings.public_ipv4.strip(),
        public_ipv6=settings.public_ipv6.strip(),
        feedback_max_attachment_bytes=settings.feedback_max_attachment_bytes,
        feedback_max_message_chars=settings.feedback_max_message_chars,
        feedback_allowed_mime_types=sorted(settings.feedback_allowed_mime_type_set()),
        feedback_pairing_code_length=settings.feedback_pairing_code_length,
    )
