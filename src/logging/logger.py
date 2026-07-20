from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from src.config import config
from .context import get_run_context
from .formatters import CompactConsoleFormatter, StructuredJSONFormatter


_CONFIGURED = False


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = get_run_context()
        record.run_id = getattr(record, "run_id", None) or context.get("run_id")
        record.graph_name = getattr(record, "graph_name", None) or context.get("graph_name")
        record.node_name = getattr(record, "node_name", None) or context.get("node_name")
        record.persistence_module = getattr(record, "persistence_module", None) or context.get("persistence_module")
        record.duration_ms = getattr(record, "duration_ms", None)
        return True


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, str(config.LOG_LEVEL).upper(), logging.INFO))
    root.handlers.clear()

    log_dir = Path(config.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(root.level)
    console_handler.setFormatter(CompactConsoleFormatter())

    file_handler = RotatingFileHandler(
        log_dir / "latest.log",
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(StructuredJSONFormatter())

    error_handler = RotatingFileHandler(
        log_dir / "latest-error.log",
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredJSONFormatter())

    context_filter = ContextFilter()
    for handler in (console_handler, file_handler, error_handler):
        handler.addFilter(context_filter)
        root.addHandler(handler)

    logging.captureWarnings(True)
    _CONFIGURED = True


def get_logger(name: str | None = None) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name or "src")


def log_structured(logger: logging.Logger, level: int, message: str, **extra: Any) -> None:
    logger.log(level, message, extra=extra)
