"""SQLite persistence for feedback, pairing codes, and notification mapping."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from domain.entities.feedback import FeedbackRecord, FeedbackStatus


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


class FeedbackSqliteRepository:
    """Blocking SQLite access; call from asyncio.to_thread."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    def init_schema(self) -> None:
        """Create tables if missing."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    telegram_username TEXT,
                    first_name TEXT,
                    message_text TEXT NOT NULL,
                    file_path TEXT,
                    file_name TEXT,
                    file_size INTEGER,
                    status TEXT NOT NULL DEFAULT 'active',
                    notify_chat_id INTEGER,
                    notify_message_id INTEGER,
                    paired_operator_telegram_id INTEGER,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_feedback_status
                ON feedback(status);

                CREATE INDEX IF NOT EXISTS idx_feedback_user
                ON feedback(telegram_user_id);

                CREATE TABLE IF NOT EXISTS pairing_codes (
                    code TEXT PRIMARY KEY,
                    operator_telegram_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_operator_links (
                    telegram_user_id INTEGER PRIMARY KEY,
                    operator_telegram_id INTEGER NOT NULL,
                    linked_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS feedback_notify_messages (
                    feedback_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    PRIMARY KEY (feedback_id, chat_id)
                );
                """
            )
            conn.commit()

    def insert_feedback(
        self,
        *,
        telegram_user_id: int,
        telegram_username: str | None,
        first_name: str | None,
        message_text: str,
        file_path: str | None,
        file_name: str | None,
        file_size: int | None,
        paired_operator_telegram_id: int | None,
    ) -> int:
        created = _utc_now_iso()
        with closing(self._connect()) as conn:
            cur = conn.execute(
                """
                INSERT INTO feedback (
                    telegram_user_id, telegram_username, first_name, message_text,
                    file_path, file_name, file_size, status,
                    notify_chat_id, notify_message_id, paired_operator_telegram_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', NULL, NULL, ?, ?)
                """,
                (
                    telegram_user_id,
                    telegram_username,
                    first_name,
                    message_text,
                    file_path,
                    file_name,
                    file_size,
                    paired_operator_telegram_id,
                    created,
                ),
            )
            conn.commit()
            row_id = cur.lastrowid
            if row_id is None:
                msg = "SQLite insert did not return row id"
                raise RuntimeError(msg)
            return int(row_id)

    def update_feedback_attachment(
        self,
        feedback_id: int,
        *,
        file_path: str,
        file_name: str,
        file_size: int,
    ) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                UPDATE feedback
                SET file_path = ?, file_name = ?, file_size = ?
                WHERE id = ?
                """,
                (file_path, file_name, file_size, feedback_id),
            )
            conn.commit()

    def clear_feedback_attachment(self, feedback_id: int) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                UPDATE feedback
                SET file_path = NULL, file_name = NULL, file_size = NULL
                WHERE id = ?
                """,
                (feedback_id,),
            )
            conn.commit()

    def get_feedback(self, feedback_id: int) -> FeedbackRecord | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM feedback WHERE id = ?",
                (feedback_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def set_notify_message(self, feedback_id: int, chat_id: int, message_id: int) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                UPDATE feedback
                SET notify_chat_id = ?, notify_message_id = ?
                WHERE id = ?
                """,
                (chat_id, message_id, feedback_id),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO feedback_notify_messages (feedback_id, chat_id, message_id)
                VALUES (?, ?, ?)
                """,
                (feedback_id, chat_id, message_id),
            )
            conn.commit()

    def list_notify_messages(self, feedback_id: int) -> list[tuple[int, int]]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT chat_id, message_id FROM feedback_notify_messages WHERE feedback_id = ?",
                (feedback_id,),
            ).fetchall()
        return [(int(r[0]), int(r[1])) for r in rows]

    def set_status(self, feedback_id: int, status: FeedbackStatus) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE feedback SET status = ? WHERE id = ?",
                (status.value, feedback_id),
            )
            conn.commit()

    def list_archived_for_operator(self, operator_id: int, limit: int) -> list[FeedbackRecord]:
        """Archived items created while linked to this operator (or global archive)."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT * FROM feedback
                WHERE status = 'archived'
                  AND (
                    paired_operator_telegram_id IS NULL
                    OR paired_operator_telegram_id = ?
                  )
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (operator_id, limit),
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def create_pairing_code(self, code: str, operator_telegram_id: int, ttl_minutes: int) -> None:
        now = datetime.now(tz=UTC)
        expires = now + timedelta(minutes=ttl_minutes)
        with closing(self._connect()) as conn:
            self._delete_expired_pairing_codes(conn)
            conn.execute(
                """
                INSERT OR REPLACE INTO pairing_codes (
                    code, operator_telegram_id, created_at, expires_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    code,
                    operator_telegram_id,
                    now.replace(microsecond=0).isoformat(),
                    expires.replace(microsecond=0).isoformat(),
                ),
            )
            conn.commit()

    def consume_pairing_code(self, code: str) -> int | None:
        """Return operator_telegram_id if code valid; delete row."""
        with closing(self._connect()) as conn:
            self._delete_expired_pairing_codes(conn)
            row = conn.execute(
                "SELECT operator_telegram_id, expires_at FROM pairing_codes WHERE code = ?",
                (code.upper(),),
            ).fetchone()
            if row is None:
                return None
            operator_id = int(row[0])
            expires_at = str(row[1])
            try:
                expires_dt = datetime.fromisoformat(expires_at)
            except ValueError:
                conn.execute("DELETE FROM pairing_codes WHERE code = ?", (code.upper(),))
                conn.commit()
                return None
            if expires_dt < datetime.now(tz=UTC):
                conn.execute("DELETE FROM pairing_codes WHERE code = ?", (code.upper(),))
                conn.commit()
                return None
            conn.execute("DELETE FROM pairing_codes WHERE code = ?", (code.upper(),))
            conn.commit()
        return operator_id

    def upsert_user_operator_link(self, telegram_user_id: int, operator_telegram_id: int) -> None:
        linked = _utc_now_iso()
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO user_operator_links (telegram_user_id, operator_telegram_id, linked_at)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    operator_telegram_id = excluded.operator_telegram_id,
                    linked_at = excluded.linked_at
                """,
                (telegram_user_id, operator_telegram_id, linked),
            )
            conn.commit()

    @staticmethod
    def _delete_expired_pairing_codes(conn: sqlite3.Connection) -> None:
        conn.execute(
            "DELETE FROM pairing_codes WHERE datetime(expires_at) < datetime(?)",
            (_utc_now_iso(),),
        )

    def get_linked_operator(self, telegram_user_id: int) -> int | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT operator_telegram_id FROM user_operator_links WHERE telegram_user_id = ?",
                (telegram_user_id,),
            ).fetchone()
        if row is None:
            return None
        return int(row[0])

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> FeedbackRecord:
        return FeedbackRecord(
            id=int(row["id"]),
            telegram_user_id=int(row["telegram_user_id"]),
            telegram_username=row["telegram_username"],
            first_name=row["first_name"],
            message_text=str(row["message_text"]),
            file_path=row["file_path"],
            file_name=row["file_name"],
            file_size=int(row["file_size"]) if row["file_size"] is not None else None,
            status=FeedbackStatus(str(row["status"])),
            notify_chat_id=(
                int(row["notify_chat_id"]) if row["notify_chat_id"] is not None else None
            ),
            notify_message_id=(
                int(row["notify_message_id"])
                if row["notify_message_id"] is not None
                else None
            ),
            paired_operator_telegram_id=int(row["paired_operator_telegram_id"])
            if row["paired_operator_telegram_id"] is not None
            else None,
            created_at_iso=str(row["created_at"]),
        )
