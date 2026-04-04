import asyncio
import hashlib
import hmac
import json
import time
from pathlib import Path
from urllib.parse import urlencode

import pytest

from application.services.feedback_workflow import FeedbackWorkflow
from config.settings import Settings
from infrastructure.persistence.feedback_sqlite import FeedbackSqliteRepository


def _build_init_data(*, token: str) -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(
            {"id": 101, "username": "demo"},
            separators=(",", ":"),
            ensure_ascii=False,
        ),
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


def test_feedback_workflow_rejects_disallowed_attachment(tmp_path: Path) -> None:
    token = "123:ABC"
    settings = Settings.model_validate(
        {
            "telegram_miniapp_bot_token": token,
            "telegram_init_data_ttl_seconds": 86_400,
            "feedback_db_path": str(tmp_path / "feedback.db"),
            "feedback_upload_dir": str(tmp_path / "uploads"),
        }
    )
    repo = FeedbackSqliteRepository(tmp_path / "feedback.db")
    repo.init_schema()
    workflow = FeedbackWorkflow(settings=settings, repo=repo, feedback_bot=None)

    with pytest.raises(ValueError, match="Недопуст"):
        asyncio.run(
            workflow.submit_from_miniapp(
                init_data=_build_init_data(token=token),
                message_text="test",
                file_bytes=b"binary",
                original_filename="payload.exe",
                content_type="application/x-msdownload",
            )
        )
