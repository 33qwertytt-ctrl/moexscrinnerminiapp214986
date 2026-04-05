"""Application settings loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_id_list(raw: str) -> list[int]:
    ids: list[int] = []
    for part in raw.split(","):
        piece = part.strip()
        if not piece:
            continue
        ids.append(int(piece))
    return ids


def _parse_csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


class Settings(BaseSettings):
    """Runtime configuration for BondScreener."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="BONDS_")

    min_rating: str = Field(default="ruA")
    default_horizon: str = Field(default="30")
    limit: int = Field(default=20, ge=1, le=100)
    log_level: str = Field(default="INFO")
    cache_ttl: int = Field(default=3600, ge=0)
    cache_dir: str = Field(default="./.cache")
    bonds_snapshot_path: str = Field(default="./data/bonds_snapshot.json")
    bonds_snapshot_timezone: str = Field(default="Europe/Moscow")
    bonds_snapshot_refresh_hour: int = Field(default=0, ge=0, le=23)
    bonds_snapshot_refresh_minute: int = Field(default=30, ge=0, le=59)

    public_domain: str = Field(default="moextab.duckdns.org")
    public_ipv4: str = Field(default="")
    public_ipv6: str = Field(default="")
    allowed_hosts: str = Field(default="")

    telegram_miniapp_bot_token: str | None = Field(default=None)
    telegram_feedback_bot_token: str | None = Field(default=None)
    telegram_feedback_bot_username: str = Field(default="")
    telegram_feedback_webhook_secret: str | None = Field(default=None)
    telegram_init_data_ttl_seconds: int = Field(default=86_400, ge=0, le=604_800)

    feedback_admin_telegram_ids: str = Field(default="")
    feedback_notify_chat_ids: str = Field(default="")
    feedback_db_path: str = Field(default="./data/feedback.db")
    feedback_upload_dir: str = Field(default="./data/feedback_uploads")
    feedback_max_attachment_bytes: int = Field(default=26_214_400, ge=1)
    feedback_max_message_chars: int = Field(default=4_000, ge=1, le=20_000)
    feedback_allowed_mime_types: str = Field(
        default=(
            "image/png,image/jpeg,image/webp,"
            "application/pdf,text/plain,text/csv,application/json"
        )
    )
    feedback_allowed_extensions: str = Field(
        default="png,jpg,jpeg,webp,pdf,txt,log,csv,json"
    )
    feedback_pairing_code_ttl_minutes: int = Field(default=30, ge=1, le=1440)
    feedback_pairing_code_length: int = Field(default=8, ge=4, le=32)
    feedback_pairing_code_alphabet: str = Field(default="")
    feedback_archive_reply_limit: int = Field(default=25, ge=1, le=200)

    api_bonds_rate_limit_per_minute: int = Field(default=60, ge=1, le=600)
    feedback_submit_rate_limit_per_minute: int = Field(default=10, ge=1, le=120)
    feedback_pair_rate_limit_per_minute: int = Field(default=10, ge=1, le=120)
    feedback_webhook_max_body_bytes: int = Field(default=262_144, ge=1, le=5_242_880)

    def feedback_admin_ids(self) -> set[int]:
        """Telegram user ids allowed to manage feedback and generate pairing codes."""
        return set(_parse_id_list(self.feedback_admin_telegram_ids))

    def feedback_notify_chat_id_list(self) -> list[int]:
        """Chats where the feedback bot posts new items."""
        return _parse_id_list(self.feedback_notify_chat_ids)

    def feedback_allowed_mime_type_set(self) -> set[str]:
        """Allowed upload MIME types for feedback attachments."""
        return {item.lower() for item in _parse_csv(self.feedback_allowed_mime_types)}

    def feedback_allowed_extension_set(self) -> set[str]:
        """Allowed file extensions for feedback attachments."""
        return {item.lower().lstrip(".") for item in _parse_csv(self.feedback_allowed_extensions)}

    def allowed_host_list(self) -> list[str]:
        """Hosts accepted by FastAPI TrustedHostMiddleware."""
        derived = {
            "127.0.0.1",
            "localhost",
            "testserver",
        }
        if self.public_domain.strip():
            derived.add(self.public_domain.strip())
        if self.public_ipv4.strip():
            derived.add(self.public_ipv4.strip())
        if self.public_ipv6.strip():
            derived.add(self.public_ipv6.strip())
        explicit = set(_parse_csv(self.allowed_hosts))
        return sorted(explicit | derived)


settings = Settings()
