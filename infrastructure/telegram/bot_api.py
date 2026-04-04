"""Minimal async client for Telegram Bot HTTP API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class TelegramBotApiError(RuntimeError):
    """Telegram Bot API returned ok=false or HTTP error."""


class TelegramBotApi:
    """Thin wrapper around api.telegram.org for the methods we need."""

    def __init__(self, token: str, client: httpx.AsyncClient) -> None:
        self._token = token
        self._client = client
        self._base = f"https://api.telegram.org/bot{token}"

    async def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}/{method}"
        response = await self._client.post(url, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            desc = data.get("description", "unknown_error")
            logger.warning("telegram_api_error", method=method, description=desc)
            msg = f"Telegram API error: {desc}"
            raise TelegramBotApiError(msg)
        result = data.get("result")
        if not isinstance(result, dict):
            msg = "Telegram API returned unexpected result shape"
            raise TelegramBotApiError(msg)
        return result

    async def _post_multipart(
        self,
        method: str,
        data: dict[str, Any],
        file_path: Path,
        file_field: str,
        filename: str,
    ) -> dict[str, Any]:
        url = f"{self._base}/{method}"
        with file_path.open("rb") as handle:
            files = {file_field: (filename, handle)}
            response = await self._client.post(
                url,
                data=data,
                files=files,
                timeout=120.0,
            )
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            desc = body.get("description", "unknown_error")
            logger.warning("telegram_api_error", method=method, description=desc)
            msg = f"Telegram API error: {desc}"
            raise TelegramBotApiError(msg)
        result = body.get("result")
        if not isinstance(result, dict):
            msg = "Telegram API returned unexpected result shape"
            raise TelegramBotApiError(msg)
        return result

    async def send_message(
        self,
        *,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return await self._post("sendMessage", payload)

    async def send_document(
        self,
        *,
        chat_id: int,
        file_path: Path,
        filename: str,
        caption: str | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {"chat_id": str(chat_id)}
        if caption is not None:
            data["caption"] = caption
        if reply_markup is not None:
            data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        return await self._post_multipart(
            "sendDocument",
            data,
            file_path=file_path,
            file_field="document",
            filename=filename,
        )

    async def edit_message_text(
        self,
        *,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return await self._post("editMessageText", payload)

    async def edit_message_caption(
        self,
        *,
        chat_id: int,
        message_id: int,
        caption: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "caption": caption,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return await self._post("editMessageCaption", payload)

    async def edit_message_reply_markup(
        self,
        *,
        chat_id: int,
        message_id: int,
        reply_markup: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return await self._post("editMessageReplyMarkup", payload)

    async def delete_message(self, *, chat_id: int, message_id: int) -> None:
        url = f"{self._base}/deleteMessage"
        response = await self._client.post(
            url,
            json={"chat_id": chat_id, "message_id": message_id},
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            desc = data.get("description", "unknown_error")
            logger.warning("telegram_api_error", method="deleteMessage", description=desc)
            msg = f"Telegram API error: {desc}"
            raise TelegramBotApiError(msg)

    async def answer_callback_query(
        self,
        *,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
    ) -> None:
        payload: dict[str, Any] = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert,
        }
        if text is not None:
            payload["text"] = text
        url = f"{self._base}/answerCallbackQuery"
        response = await self._client.post(url, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            desc = data.get("description", "unknown_error")
            logger.warning("telegram_api_error", method="answerCallbackQuery", description=desc)
            msg = f"Telegram API error: {desc}"
            raise TelegramBotApiError(msg)
