"""Domain types for user feedback and operator pairing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FeedbackStatus(StrEnum):
    """Lifecycle of a feedback record in storage."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class FeedbackRecord:
    """Stored feedback item."""

    id: int
    telegram_user_id: int
    telegram_username: str | None
    first_name: str | None
    message_text: str
    file_path: str | None
    file_name: str | None
    file_size: int | None
    status: FeedbackStatus
    notify_chat_id: int | None
    notify_message_id: int | None
    paired_operator_telegram_id: int | None
    created_at_iso: str
