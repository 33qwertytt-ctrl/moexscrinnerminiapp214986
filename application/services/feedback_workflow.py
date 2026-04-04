"""Orchestration for Mini App feedback, pairing, and operator bot actions."""

from __future__ import annotations

import asyncio
import re
import secrets
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any, TypeVar

import structlog

from config.settings import Settings
from domain.entities.feedback import FeedbackRecord, FeedbackStatus
from infrastructure.persistence.feedback_sqlite import FeedbackSqliteRepository
from infrastructure.telegram.bot_api import TelegramBotApi, TelegramBotApiError
from infrastructure.telegram.feedback_markups import (
    confirm_archive_keyboard,
    confirm_delete_keyboard,
    empty_inline_keyboard,
    feedback_inline_actions,
    operator_reply_keyboard,
)
from utils.telegram_webapp import parse_init_data_user

logger = structlog.get_logger(__name__)

T = TypeVar("T")

_DEFAULT_PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _pairing_alphabet(settings: Settings) -> str:
    raw = settings.feedback_pairing_code_alphabet.strip()
    if not raw:
        return _DEFAULT_PAIRING_ALPHABET
    if len(set(raw)) < 2:
        return _DEFAULT_PAIRING_ALPHABET
    return raw


def _format_feedback_caption(
    record_id: int,
    tg_user_id: int,
    username: str | None,
    text: str,
) -> str:
    uname = f"@{username}" if username else "—"
    body = text.strip() or "—"
    if len(body) > 3000:
        body = body[:2997] + "..."
    return f"Фидбек #{record_id}\nОт: {uname} (id {tg_user_id})\n\n{body}"


def _truncate_telegram_caption(text: str, limit: int = 1000) -> str:
    """Telegram captions are short; keep room for confirmation suffix."""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


async def _edit_notification_message(
    bot: TelegramBotApi,
    *,
    msg: dict[str, Any],
    chat_id: int,
    message_id: int,
    body: str,
    reply_markup: dict[str, Any] | None,
) -> None:
    """Use caption API for document/media operator notifications."""
    if msg.get("document") or msg.get("photo") or msg.get("video"):
        cap = _truncate_telegram_caption(body)
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=cap,
            reply_markup=reply_markup,
        )
        return
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=body,
        reply_markup=reply_markup,
    )


def _safe_filename(name: str) -> str:
    base = Path(name).name
    cleaned = "".join(ch for ch in base if ch.isalnum() or ch in "._-")
    return cleaned[:120] if cleaned else "attachment"


def _file_extension(name: str | None) -> str:
    if not name:
        return ""
    return Path(name).suffix.lower().lstrip(".")


def _parse_callback(data: str) -> tuple[str, int] | None:
    if ":" not in data:
        return None
    prefix, _, rest = data.partition(":")
    try:
        fid = int(rest)
    except ValueError:
        return None
    return prefix, fid


class FeedbackWorkflow:
    """Feedback ingestion, pairing, and operator bot handling."""

    def __init__(
        self,
        *,
        settings: Settings,
        repo: FeedbackSqliteRepository,
        feedback_bot: TelegramBotApi | None,
    ) -> None:
        self._settings = settings
        self._repo = repo
        self._bot = feedback_bot

    def _run_repo(
        self,
        fn: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> Coroutine[Any, Any, T]:
        return asyncio.to_thread(fn, *args, **kwargs)

    def _validate_message_text(self, text: str) -> None:
        if len(text) > self._settings.feedback_max_message_chars:
            msg = (
                "Сообщение слишком длинное "
                f"(максимум {self._settings.feedback_max_message_chars} символов)."
            )
            raise ValueError(msg)

    def _validate_attachment(self, filename: str | None, content_type: str | None) -> None:
        if not filename:
            return
        extension = _file_extension(filename)
        allowed_extensions = self._settings.feedback_allowed_extension_set()
        allowed_mime_types = self._settings.feedback_allowed_mime_type_set()
        if extension and extension not in allowed_extensions:
            msg = f"Недопустимое расширение файла: .{extension}"
            raise ValueError(msg)
        normalized_type = (content_type or "").strip().lower()
        if normalized_type in {"", "application/octet-stream"}:
            return
        if normalized_type not in allowed_mime_types:
            msg = f"Недопустимый тип файла: {normalized_type}"
            raise ValueError(msg)

    async def _delete_attachment(self, record: FeedbackRecord) -> None:
        if not record.file_path:
            return
        upload_root = Path(self._settings.feedback_upload_dir).resolve()
        candidate = Path(record.file_path).resolve()
        try:
            candidate.relative_to(upload_root)
        except ValueError:
            logger.warning(
                "feedback_attachment_outside_upload_root",
                feedback_id=record.id,
                file_path=str(candidate),
            )
            return

        if candidate.exists():
            await asyncio.to_thread(candidate.unlink, True)
        await self._run_repo(self._repo.clear_feedback_attachment, record.id)

    def _is_admin(self, user_id: int) -> bool:
        return user_id in self._settings.feedback_admin_ids()

    async def pair_miniapp_user(self, *, init_data: str, pairing_code: str) -> None:
        """Link Mini App Telegram user to the operator who issued the code."""
        token = self._settings.telegram_miniapp_bot_token
        if not token:
            msg = "Mini App bot token is not configured"
            raise RuntimeError(msg)
        user = parse_init_data_user(
            init_data,
            token,
            self._settings.telegram_init_data_ttl_seconds,
        )
        tg_user_id = int(user["id"])
        code = pairing_code.strip().upper()
        if not code or len(code) > self._settings.feedback_pairing_code_length:
            msg = "Неверный код привязки."
            raise ValueError(msg)
        operator_id = await self._run_repo(self._repo.consume_pairing_code, code)
        if operator_id is None:
            msg = "Неверный или просроченный код."
            raise ValueError(msg)
        await self._run_repo(self._repo.upsert_user_operator_link, tg_user_id, operator_id)
        logger.info("feedback_pairing_ok", user_id=tg_user_id, operator_id=operator_id)

    async def submit_from_miniapp(
        self,
        *,
        init_data: str,
        message_text: str,
        file_bytes: bytes | None,
        original_filename: str | None,
        content_type: str | None,
    ) -> int:
        """Validate WebApp user, persist feedback, notify operator chats."""
        token = self._settings.telegram_miniapp_bot_token
        if not token:
            msg = "Mini App bot token is not configured"
            raise RuntimeError(msg)
        user = parse_init_data_user(
            init_data,
            token,
            self._settings.telegram_init_data_ttl_seconds,
        )
        tg_user_id = int(user["id"])
        username = user.get("username")
        first_name = user.get("first_name")

        text = message_text.strip()
        self._validate_message_text(text)
        if not text and not file_bytes:
            msg = "Пустое сообщение."
            raise ValueError(msg)

        max_bytes = self._settings.feedback_max_attachment_bytes
        if file_bytes is not None and len(file_bytes) > max_bytes:
            msg = f"Файл больше лимита ({max_bytes} байт)."
            raise ValueError(msg)
        self._validate_attachment(original_filename, content_type)

        linked_operator = await self._run_repo(self._repo.get_linked_operator, tg_user_id)

        feedback_id = await self._run_repo(
            self._repo.insert_feedback,
            telegram_user_id=tg_user_id,
            telegram_username=username if isinstance(username, str) else None,
            first_name=first_name if isinstance(first_name, str) else None,
            message_text=text or "—",
            file_path=None,
            file_name=None,
            file_size=None,
            paired_operator_telegram_id=linked_operator,
        )

        upload_root = Path(self._settings.feedback_upload_dir)
        upload_root.mkdir(parents=True, exist_ok=True)

        if file_bytes is not None:
            fname = _safe_filename(original_filename or "attachment")
            disk_name = f"{feedback_id}_{secrets.token_hex(8)}_{fname}"
            disk_path = (upload_root / disk_name).resolve()
            try:
                disk_path.relative_to(upload_root.resolve())
            except ValueError as exc:
                msg = "Attachment path escaped upload directory."
                raise RuntimeError(msg) from exc
            await asyncio.to_thread(disk_path.write_bytes, file_bytes)
            await self._run_repo(
                self._repo.update_feedback_attachment,
                feedback_id,
                file_path=str(disk_path),
                file_name=fname,
                file_size=len(file_bytes),
            )

        record = await self._run_repo(self._repo.get_feedback, feedback_id)
        if record is None:
            msg = "Feedback row missing after insert."
            raise RuntimeError(msg)

        caption = _format_feedback_caption(
            record.id,
            record.telegram_user_id,
            record.telegram_username,
            record.message_text,
        )
        markup = feedback_inline_actions(record.id)
        notify_chats = self._settings.feedback_notify_chat_id_list()
        if not notify_chats:
            logger.warning("feedback_no_notify_chats", feedback_id=feedback_id)
            return feedback_id
        notify_bot = self._bot
        if notify_bot is None:
            logger.warning("feedback_bot_token_missing", feedback_id=feedback_id)
            return feedback_id

        file_path = Path(record.file_path) if record.file_path else None
        for chat_id in notify_chats:
            try:
                if file_path and file_path.is_file():
                    sent = await notify_bot.send_document(
                        chat_id=chat_id,
                        file_path=file_path,
                        filename=record.file_name or "file",
                        caption=caption,
                        reply_markup=markup,
                    )
                else:
                    sent = await notify_bot.send_message(
                        chat_id=chat_id,
                        text=caption,
                        reply_markup=markup,
                    )
                raw_message_id = sent.get("message_id")
                if raw_message_id is None:
                    continue
                await self._run_repo(
                    self._repo.set_notify_message,
                    feedback_id,
                    chat_id,
                    int(raw_message_id),
                )
            except TelegramBotApiError as exc:
                logger.warning(
                    "feedback_notify_failed",
                    feedback_id=feedback_id,
                    chat_id=chat_id,
                    error=str(exc),
                )

        logger.info("feedback_submitted", feedback_id=feedback_id, user_id=tg_user_id)
        return feedback_id

    async def process_telegram_update(self, update: dict[str, Any]) -> None:
        """Dispatch feedback-bot webhook updates (messages + callbacks)."""
        bot = self._bot
        if bot is None:
            logger.warning("telegram_update_ignored_no_bot")
            return
        if "callback_query" in update:
            await self._handle_callback(update["callback_query"], bot)
            return
        msg = update.get("message") or update.get("edited_message")
        if isinstance(msg, dict):
            await self._handle_message(msg, bot)

    async def _handle_message(self, msg: dict[str, Any], bot: TelegramBotApi) -> None:
        chat = msg.get("chat") or {}
        from_user = msg.get("from") or {}
        chat_id = int(chat["id"])
        user_id = int(from_user["id"])
        text = (msg.get("text") or "").strip()

        if text.startswith("/start"):
            await self._cmd_start(chat_id, user_id, text, bot)
            return
        if text == "/pair":
            await self._cmd_pair(chat_id, user_id, bot)
            return
        if text == "Архив":
            await self._cmd_archive_list(chat_id, user_id, bot)

    async def _cmd_start(self, chat_id: int, user_id: int, text: str, bot: TelegramBotApi) -> None:
        if not self._is_admin(user_id):
            await bot.send_message(
                chat_id=chat_id,
                text="Бот доступен только операторам фидбека.",
            )
            return
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "Бот фидбека BondScreener.\n"
                "Команды:\n"
                "/pair — выдать код для привязки Mini App пользователя\n"
                "Кнопка «Архив» — последние архивные сообщения\n\n"
                "Подсказка: пользователь вводит код в Mini App после /pair."
            ),
            reply_markup=operator_reply_keyboard(),
        )
        match = re.match(r"/start\s+(\S+)", text)
        if not match:
            return
        payload = match.group(1)
        if not payload.upper().startswith("PAIR_"):
            return
        code = payload.split("_", 1)[-1].strip().upper()
        if not code:
            return
        hint = (
            f"Код из ссылки: {code}\n"
            "Отправьте его пользователю для ввода в приложении."
        )
        await bot.send_message(chat_id=chat_id, text=hint)

    async def _cmd_pair(self, chat_id: int, user_id: int, bot: TelegramBotApi) -> None:
        if not self._is_admin(user_id):
            await bot.send_message(chat_id=chat_id, text="Команда недоступна.")
            return
        alphabet = _pairing_alphabet(self._settings)
        length = self._settings.feedback_pairing_code_length
        code = "".join(secrets.choice(alphabet) for _ in range(length))
        ttl = self._settings.feedback_pairing_code_ttl_minutes
        await self._run_repo(self._repo.create_pairing_code, code, user_id, ttl)
        lines = [
            f"Код привязки: {code}",
            f"Действителен {ttl} мин.",
            "Передайте код пользователю для ввода в Mini App.",
        ]
        username = self._settings.telegram_feedback_bot_username.strip().lstrip("@")
        if username:
            lines.append(f"Deep link: https://t.me/{username}?start=pair_{code}")
        await bot.send_message(
            chat_id=chat_id,
            text="\n".join(lines),
            reply_markup=operator_reply_keyboard(),
        )

    async def _cmd_archive_list(
        self,
        chat_id: int,
        user_id: int,
        bot: TelegramBotApi,
    ) -> None:
        if not self._is_admin(user_id):
            await bot.send_message(chat_id=chat_id, text="Недоступно.")
            return
        limit = self._settings.feedback_archive_reply_limit
        rows = await self._run_repo(self._repo.list_archived_for_operator, user_id, limit)
        if not rows:
            await bot.send_message(chat_id=chat_id, text="Архив пуст.")
            return
        chunks: list[str] = []
        buffer = "Архив (последние записи):\n\n"
        for row in rows:
            username = f"@{row.telegram_username}" if row.telegram_username else "—"
            line = f"#{row.id} {row.created_at_iso} | {username} | id {row.telegram_user_id}\n"
            snippet = row.message_text.replace("\n", " ")
            if len(snippet) > 180:
                snippet = snippet[:177] + "..."
            line += f"{snippet}\n\n"
            if len(buffer) + len(line) > 4000:
                chunks.append(buffer)
                buffer = line
            else:
                buffer += line
        if buffer.strip():
            chunks.append(buffer)
        for piece in chunks:
            await bot.send_message(chat_id=chat_id, text=piece.strip())

    async def _handle_callback(self, cq: dict[str, Any], bot: TelegramBotApi) -> None:
        from_user = cq.get("from") or {}
        user_id = int(from_user["id"])
        callback_query_id = str(cq["id"])
        data = str(cq.get("data") or "")
        msg = cq.get("message") or {}
        chat = msg.get("chat") or {}
        chat_id = int(chat["id"])
        message_id = int(msg["message_id"])

        parsed = _parse_callback(data)
        if parsed is None:
            await bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text="Некорректные данные.",
            )
            return

        prefix, feedback_id = parsed
        if not self._is_admin(user_id):
            await bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text="Нет доступа.",
                show_alert=True,
            )
            return

        record = await self._run_repo(self._repo.get_feedback, feedback_id)
        if record is None:
            await bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text="Запись не найдена.",
                show_alert=True,
            )
            return

        caption = _format_feedback_caption(
            record.id,
            record.telegram_user_id,
            record.telegram_username,
            record.message_text,
        )

        try:
            if prefix == "ar1":
                await _edit_notification_message(
                    bot,
                    msg=msg,
                    chat_id=chat_id,
                    message_id=message_id,
                    body=f"{caption}\n\nВы уверены? Переместить в архив?",
                    reply_markup=confirm_archive_keyboard(feedback_id),
                )
            elif prefix == "arx":
                await _edit_notification_message(
                    bot,
                    msg=msg,
                    chat_id=chat_id,
                    message_id=message_id,
                    body=caption,
                    reply_markup=feedback_inline_actions(feedback_id),
                )
            elif prefix == "ar2":
                await self._run_repo(self._repo.set_status, feedback_id, FeedbackStatus.ARCHIVED)
                await _edit_notification_message(
                    bot,
                    msg=msg,
                    chat_id=chat_id,
                    message_id=message_id,
                    body=f"[Архив]\n{caption}",
                    reply_markup=empty_inline_keyboard(),
                )
            elif prefix == "dl1":
                await _edit_notification_message(
                    bot,
                    msg=msg,
                    chat_id=chat_id,
                    message_id=message_id,
                    body=f"{caption}\n\nВы уверены? Удалить сообщение безвозвратно?",
                    reply_markup=confirm_delete_keyboard(feedback_id),
                )
            elif prefix == "dlx":
                await _edit_notification_message(
                    bot,
                    msg=msg,
                    chat_id=chat_id,
                    message_id=message_id,
                    body=caption,
                    reply_markup=feedback_inline_actions(feedback_id),
                )
            elif prefix == "dl2":
                await self._run_repo(self._repo.set_status, feedback_id, FeedbackStatus.DELETED)
                await self._delete_attachment(record)
                notify_rows = await self._run_repo(self._repo.list_notify_messages, feedback_id)
                for notify_chat_id, notify_message_id in notify_rows:
                    try:
                        await bot.delete_message(
                            chat_id=notify_chat_id,
                            message_id=notify_message_id,
                        )
                    except TelegramBotApiError:
                        logger.info(
                            "telegram_delete_skipped",
                            chat_id=notify_chat_id,
                            message_id=notify_message_id,
                        )
                if not notify_rows:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except TelegramBotApiError:
                        logger.info(
                            "telegram_delete_skipped",
                            chat_id=chat_id,
                            message_id=message_id,
                        )
            else:
                await bot.answer_callback_query(
                    callback_query_id=callback_query_id,
                    text="Неизвестное действие.",
                )
                return
        except TelegramBotApiError as exc:
            logger.warning("telegram_callback_failed", error=str(exc))
            await bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text="Не удалось обновить сообщение.",
                show_alert=True,
            )
            return

        await bot.answer_callback_query(callback_query_id=callback_query_id)
