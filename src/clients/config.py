from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

DEFAULT_QWEN_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULT_QWEN_MODEL = "qwen3.7-plus"


@dataclass(frozen=True)
class Settings:
    # Optional now. Only needed for Qwen chat/completion calls.
    DASHSCOPE_API_KEY: str | None = None

    QWEN_BASE_URL: str = DEFAULT_QWEN_BASE_URL
    QWEN_MODEL: str = DEFAULT_QWEN_MODEL
    QWEN_MODEL_CHEAP: str = DEFAULT_QWEN_MODEL

    VECTOR_DB_URL: str | None = None
    VECTOR_DB_TYPE: str | None = None


def _load_with_dotenv() -> Settings:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=ENV_FILE, override=False)

    return Settings(
        DASHSCOPE_API_KEY=(
            os.getenv("QWEN_API_KEY")
            or os.getenv("DASHSCOPE_API_KEY")
        ),

        QWEN_BASE_URL=os.getenv(
            "QWEN_BASE_URL",
            DEFAULT_QWEN_BASE_URL,
        ),

        QWEN_MODEL=os.getenv(
            "QWEN_MODEL",
            DEFAULT_QWEN_MODEL,
        ),

        QWEN_MODEL_CHEAP=os.getenv(
            "QWEN_MODEL_CHEAP",
            DEFAULT_QWEN_MODEL,
        ),

        VECTOR_DB_URL=os.getenv("VECTOR_DB_URL"),

        VECTOR_DB_TYPE=os.getenv("VECTOR_DB_TYPE"),
    )


def _load_with_pydantic_settings() -> Settings:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict


    class RawSettings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=ENV_FILE,
            env_file_encoding="utf-8",
            extra="ignore",
        )

        DASHSCOPE_API_KEY: str | None = Field(default=None)

        QWEN_BASE_URL: str = DEFAULT_QWEN_BASE_URL
        QWEN_MODEL: str = DEFAULT_QWEN_MODEL
        QWEN_MODEL_CHEAP: str | None = None

        VECTOR_DB_URL: str | None = None
        VECTOR_DB_TYPE: str | None = None


    raw = RawSettings()

    return Settings(
        DASHSCOPE_API_KEY=raw.DASHSCOPE_API_KEY,

        QWEN_BASE_URL=raw.QWEN_BASE_URL,

        QWEN_MODEL=raw.QWEN_MODEL,

        QWEN_MODEL_CHEAP=(
            raw.QWEN_MODEL_CHEAP
            or raw.QWEN_MODEL
        ),

        VECTOR_DB_URL=raw.VECTOR_DB_URL,

        VECTOR_DB_TYPE=raw.VECTOR_DB_TYPE,
    )


def _build_settings() -> Settings:
    try:
        return _load_with_pydantic_settings()

    except ImportError:
        return _load_with_dotenv()


settings = _build_settings()