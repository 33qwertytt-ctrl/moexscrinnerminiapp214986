import asyncio
import hashlib
import hmac
import json
import time
from pathlib import Path
from urllib.parse import urlencode

import pytest

from application.services.feedback_workflow import FeedbackWorkflow
from domain.entities.feedback import FeedbackStatus
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


class FakeBot:
    def __init__(self) -> None:
        self.edits: list[dict] = []
        self.deletes: list[tuple[int, int]] = []
        self.answers: list[dict] = []

    async def edit_message_text(self, **kwargs):
        self.edits.append(kwargs)
        return {"message_id": kwargs["message_id"]}

    async def edit_message_caption(self, **kwargs):
        self.edits.append(kwargs)
        return {"message_id": kwargs["message_id"]}

    async def delete_message(self, *, chat_id: int, message_id: int) -> None:
        self.deletes.append((chat_id, message_id))

    async def answer_callback_query(self, **kwargs) -> None:
        self.answers.append(kwargs)


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


def test_feedback_workflow_accepts_submission_without_pairing(tmp_path: Path) -> None:
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

    feedback_id = asyncio.run(
        workflow.submit_from_miniapp(
            init_data=_build_init_data(token=token),
            message_text="test",
            file_bytes=None,
            original_filename=None,
            content_type=None,
        )
    )

    record = repo.get_feedback(feedback_id)
    assert record is not None
    assert record.message_text == "test"
    assert record.paired_operator_telegram_id is None


def test_feedback_workflow_can_delete_archived_message(tmp_path: Path) -> None:
    token = "123:ABC"
    settings = Settings.model_validate(
        {
            "telegram_miniapp_bot_token": token,
            "telegram_init_data_ttl_seconds": 86_400,
            "feedback_db_path": str(tmp_path / "feedback.db"),
            "feedback_upload_dir": str(tmp_path / "uploads"),
            "feedback_admin_telegram_ids": "500",
        }
    )
    repo = FeedbackSqliteRepository(tmp_path / "feedback.db")
    repo.init_schema()
    feedback_id = repo.insert_feedback(
        telegram_user_id=101,
        telegram_username="demo",
        first_name="Demo",
        message_text="archive me",
        file_path=None,
        file_name=None,
        file_size=None,
        paired_operator_telegram_id=None,
    )
    repo.set_notify_message(feedback_id, 777, 42)
    bot = FakeBot()
    workflow = FeedbackWorkflow(settings=settings, repo=repo, feedback_bot=bot)

    asyncio.run(
        workflow.process_telegram_update(
            {
                "callback_query": {
                    "id": "cb-1",
                    "from": {"id": 500},
                    "data": f"ar2:{feedback_id}",
                    "message": {
                        "message_id": 42,
                        "chat": {"id": 777},
                        "text": "message",
                    },
                }
            }
        )
    )
    archived = repo.get_feedback(feedback_id)
    assert archived is not None
    assert archived.status == FeedbackStatus.ARCHIVED
    assert bot.edits[-1]["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == f"adl1:{feedback_id}"

    asyncio.run(
        workflow.process_telegram_update(
            {
                "callback_query": {
                    "id": "cb-2",
                    "from": {"id": 500},
                    "data": f"adl2:{feedback_id}",
                    "message": {
                        "message_id": 42,
                        "chat": {"id": 777},
                        "text": "message",
                    },
                }
            }
        )
    )
    deleted = repo.get_feedback(feedback_id)
    assert deleted is not None
    assert deleted.status == FeedbackStatus.DELETED
    assert (777, 42) in bot.deletes
