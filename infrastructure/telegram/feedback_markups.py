"""Telegram reply/inline keyboards for feedback operators."""

from __future__ import annotations

from typing import Any


def operator_reply_keyboard() -> dict[str, Any]:
    """Persistent-style key for listing archived feedback."""
    return {
        "keyboard": [[{"text": "Архив"}]],
        "resize_keyboard": True,
    }


def feedback_inline_actions(feedback_id: int) -> dict[str, Any]:
    """Primary actions under a feedback notification."""
    return {
        "inline_keyboard": [
            [
                {"text": "В архив", "callback_data": f"ar1:{feedback_id}"},
                {"text": "Удалить", "callback_data": f"dl1:{feedback_id}"},
            ],
        ],
    }


def confirm_archive_keyboard(feedback_id: int) -> dict[str, Any]:
    """Second step for archive."""
    return {
        "inline_keyboard": [
            [
                {"text": "Подтвердить", "callback_data": f"ar2:{feedback_id}"},
                {"text": "Отмена", "callback_data": f"arx:{feedback_id}"},
            ],
        ],
    }


def confirm_delete_keyboard(feedback_id: int) -> dict[str, Any]:
    """Second step for delete."""
    return {
        "inline_keyboard": [
            [
                {"text": "Подтвердить", "callback_data": f"dl2:{feedback_id}"},
                {"text": "Отмена", "callback_data": f"dlx:{feedback_id}"},
            ],
        ],
    }


def empty_inline_keyboard() -> dict[str, Any]:
    """Remove inline buttons."""
    return {"inline_keyboard": []}
