"""Application settings and configuration helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"


def default_database_url() -> str:
    db_path = BASE_DIR / "data" / "webwatcher.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path}"


class Settings(BaseSettings):
    """Centralised application settings."""

    model_config = SettingsConfigDict(env_file=(BASE_DIR / ".env.dev", BASE_DIR / ".env"), env_file_encoding="utf-8", env_prefix="WEBWATCHER_")

    database_url: str = Field(default_factory=default_database_url)
    telegram_bot_token: str | None = None
    telegram_chat_ids: List[str] = Field(default_factory=list)
    brevo_api_key: str | None = None
    brevo_sender: str | None = None
    brevo_recipients: List[str] = Field(default_factory=list)
    topics_file: Path = Field(default=CONFIG_DIR / "topics.yaml")
    feeds_file: Path = Field(default=CONFIG_DIR / "feeds.yaml")
    digest_hour_utc: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
