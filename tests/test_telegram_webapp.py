import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from utils.telegram_webapp import TelegramWebAppAuthError, parse_init_data_user


def _build_init_data(*, token: str, auth_date: int, user: dict[str, object]) -> str:
    payload = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
    }
    data_check_string = "\n".join(f"{key}={payload[key]}" for key in sorted(payload))
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    payload["hash"] = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return urlencode(payload)


def test_parse_init_data_user_accepts_recent_payload() -> None:
    init_data = _build_init_data(
        token="123:ABC",
        auth_date=1_700_000_000,
        user={"id": 42, "username": "tester"},
    )

    parsed = parse_init_data_user(
        init_data,
        "123:ABC",
        86_400,
        now_ts=1_700_000_100,
    )

    assert parsed["id"] == 42
    assert parsed["username"] == "tester"


def test_parse_init_data_user_rejects_expired_payload() -> None:
    init_data = _build_init_data(
        token="123:ABC",
        auth_date=1_700_000_000,
        user={"id": 42},
    )

    with pytest.raises(TelegramWebAppAuthError, match="expired"):
        parse_init_data_user(
            init_data,
            "123:ABC",
            60,
            now_ts=1_700_001_000,
        )
