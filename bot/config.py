"""Configuration loading for the bot application."""

from __future__ import annotations

from pathlib import Path
import os
from typing import Self

from pydantic import BaseModel, ConfigDict, ValidationError


ENV_FILE_NAME = ".env.bot.secret"


class Settings(BaseModel):
    """Runtime settings loaded from environment variables."""

    model_config = ConfigDict(frozen=True)

    bot_token: str | None = None
    lms_api_base_url: str | None = None
    lms_api_key: str | None = None
    llm_api_key: str | None = None
    llm_api_base_url: str | None = None
    llm_api_model: str | None = None

    @classmethod
    def from_environment(cls) -> Self:
        """Load settings from the process environment after reading env files."""
        load_env_file()
        return cls(
            bot_token=os.getenv("BOT_TOKEN"),
            lms_api_base_url=os.getenv("LMS_API_BASE_URL"),
            lms_api_key=os.getenv("LMS_API_KEY"),
            llm_api_key=os.getenv("LLM_API_KEY"),
            llm_api_base_url=os.getenv("LLM_API_BASE_URL"),
            llm_api_model=os.getenv("LLM_API_MODEL"),
        )

    def require_bot_token(self) -> str:
        """Return the Telegram token or raise a clear error."""
        if not self.bot_token:
            raise ValueError(
                "BOT_TOKEN is required for Telegram mode. "
                "Set it in .env.bot.secret or the environment."
            )
        return self.bot_token


def load_settings() -> Settings:
    """Load and validate application settings."""
    try:
        return Settings.from_environment()
    except ValidationError as exc:
        raise RuntimeError(f"Invalid bot configuration: {exc}") from exc


def load_env_file() -> Path | None:
    """Load the first matching env file from common launch locations."""
    for candidate in _env_candidates():
        if not candidate.exists():
            continue
        _parse_env_file(candidate)
        return candidate
    return None


def _env_candidates() -> list[Path]:
    current_dir = Path(__file__).resolve().parent
    cwd = Path.cwd().resolve()
    return [
        cwd / ENV_FILE_NAME,
        cwd.parent / ENV_FILE_NAME,
        current_dir / ENV_FILE_NAME,
        current_dir.parent / ENV_FILE_NAME,
    ]


def _parse_env_file(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
