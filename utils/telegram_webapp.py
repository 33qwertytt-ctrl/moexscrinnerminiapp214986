"""Validate Telegram Web App initData (Mini App)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, cast
from urllib.parse import parse_qsl


class TelegramWebAppAuthError(ValueError):
    """initData signature invalid or missing fields."""


def parse_init_data_user(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 0,
    *,
    now_ts: int | None = None,
) -> dict[str, Any]:
    """Parse and validate initData; return the `user` object as dict.

    Args:
        init_data: Raw query string from Telegram.WebApp.initData.
        bot_token: Token of the bot that hosts the Mini App.
        max_age_seconds: Optional max allowed age of initData.
        now_ts: Optional current UNIX timestamp for tests.

    Returns:
        Parsed Telegram user payload.

    Raises:
        TelegramWebAppAuthError: If hash is wrong or user is absent.
    """
    pairs = parse_qsl(init_data, keep_blank_values=True)
    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if not received_hash:
        msg = "initData is missing hash"
        raise TelegramWebAppAuthError(msg)

    check_pairs = [f"{key}={data[key]}" for key in sorted(data.keys())]
    data_check_string = "\n".join(check_pairs)

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        msg = "initData hash mismatch"
        raise TelegramWebAppAuthError(msg)

    auth_date_raw = data.get("auth_date")
    if not auth_date_raw:
        msg = "initData is missing auth_date"
        raise TelegramWebAppAuthError(msg)
    try:
        auth_date = int(auth_date_raw)
    except ValueError as exc:
        msg = "initData auth_date is invalid"
        raise TelegramWebAppAuthError(msg) from exc

    if max_age_seconds > 0:
        current_ts = int(time.time()) if now_ts is None else now_ts
        if auth_date > current_ts + 60:
            msg = "initData auth_date is in the future"
            raise TelegramWebAppAuthError(msg)
        if current_ts - auth_date > max_age_seconds:
            msg = "initData is expired"
            raise TelegramWebAppAuthError(msg)

    raw_user = data.get("user")
    if not raw_user:
        msg = "initData is missing user"
        raise TelegramWebAppAuthError(msg)
    try:
        return cast(dict[str, Any], json.loads(raw_user))
    except json.JSONDecodeError as exc:
        msg = "initData user is not valid JSON"
        raise TelegramWebAppAuthError(msg) from exc
