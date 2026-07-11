from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
DEFAULT_QWEN_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULT_QWEN_MODEL = "qwen3.7-plus"


@dataclass(frozen=True)
class Settings:
    DASHSCOPE_API_KEY: str
    QWEN_BASE_URL: str = DEFAULT_QWEN_BASE_URL
    QWEN_MODEL: str = DEFAULT_QWEN_MODEL
    QWEN_MODEL_CHEAP: str = DEFAULT_QWEN_MODEL
    VECTOR_DB_URL: str | None = None
    VECTOR_DB_TYPE: str | None = None


def _missing_api_key_error() -> RuntimeError:
    return RuntimeError(
        "Missing QWEN_API_KEY. Set QWEN_API_KEY in .env or export DASHSCOPE_API_KEY before importing src.clients.config."
    )


def _load_with_pydantic_settings() -> Settings:
		from pydantic import AliasChoices, Field
		from pydantic import ValidationError
		from pydantic_settings import BaseSettings, SettingsConfigDict

		class RawSettings(BaseSettings):
				model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

				DASHSCOPE_API_KEY: str = Field(validation_alias=AliasChoices("QWEN_API_KEY", "DASHSCOPE_API_KEY"))
				QWEN_BASE_URL: str = DEFAULT_QWEN_BASE_URL
				QWEN_MODEL: str = DEFAULT_QWEN_MODEL
				QWEN_MODEL_CHEAP: str | None = None
				VECTOR_DB_URL: str | None = None
				VECTOR_DB_TYPE: str | None = None

		try:
				raw_settings = RawSettings()
		except ValidationError as error:
				raise _missing_api_key_error() from error
	cheap_model = raw_settings.QWEN_MODEL_CHEAP or raw_settings.QWEN_MODEL
	return Settings(
				DASHSCOPE_API_KEY=raw_settings.DASHSCOPE_API_KEY,
				QWEN_BASE_URL=raw_settings.QWEN_BASE_URL,
				QWEN_MODEL=raw_settings.QWEN_MODEL,
				QWEN_MODEL_CHEAP=cheap_model,
				VECTOR_DB_URL=raw_settings.VECTOR_DB_URL,
				VECTOR_DB_TYPE=raw_settings.VECTOR_DB_TYPE,
		)


def _load_with_dotenv() -> Settings:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=ENV_FILE, override=False)

    api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise _missing_api_key_error()

    qwen_base_url = os.getenv("QWEN_BASE_URL", DEFAULT_QWEN_BASE_URL)
    qwen_model = os.getenv("QWEN_MODEL", DEFAULT_QWEN_MODEL)
    qwen_model_cheap = os.getenv("QWEN_MODEL_CHEAP") or qwen_model
    vector_db_url = os.getenv("VECTOR_DB_URL")
    vector_db_type = os.getenv("VECTOR_DB_TYPE")

    return Settings(
        DASHSCOPE_API_KEY=api_key,
        QWEN_BASE_URL=qwen_base_url,
        QWEN_MODEL=qwen_model,
        QWEN_MODEL_CHEAP=qwen_model_cheap,
        VECTOR_DB_URL=vector_db_url,
        VECTOR_DB_TYPE=vector_db_type,
    )


def _build_settings() -> Settings:
    try:
        settings = _load_with_pydantic_settings()
    except ImportError:
        try:
            settings = _load_with_dotenv()
        except ImportError as error:
            raise ImportError(
                "Install pydantic-settings or python-dotenv to load configuration from .env."
            ) from error

    os.environ.setdefault("DASHSCOPE_API_KEY", settings.DASHSCOPE_API_KEY)
    return settings


settings = _build_settings()
