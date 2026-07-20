from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


_COLORS = {
    logging.DEBUG: "\033[36m",
    logging.INFO: "\033[32m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[35m",
}
_RESET = "\033[0m"


class ContextAwareFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if getattr(record, "summary_display", None):
            return str(record.summary_display)
        base = super().format(record)
        color = _COLORS.get(record.levelno)
        if color:
            return f"{color}{base}{_RESET}"
        return base


class CompactConsoleFormatter(ContextAwareFormatter):
    def __init__(self) -> None:
        super().__init__(fmt="%(asctime)s | %(levelname)s | run=%(run_id)s | graph=%(graph_name)s | node=%(node_name)s | %(message)s", datefmt="%H:%M:%S")


class StructuredJSONFormatter(logging.Formatter):
    _standard_keys = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "run_id": getattr(record, "run_id", None),
            "graph_name": getattr(record, "graph_name", None),
            "node_name": getattr(record, "node_name", None),
            "level": record.levelname,
            "message": record.getMessage(),
            "duration_ms": getattr(record, "duration_ms", None),
            "thread_name": record.threadName,
            "process_id": record.process,
            "persistence_module": getattr(record, "persistence_module", None),
            "sql_operation": getattr(record, "sql_operation", None),
            "table": getattr(record, "table", None),
            "rows_returned": getattr(record, "rows_returned", None),
            "rows_affected": getattr(record, "rows_affected", None),
            "provider": getattr(record, "provider", None),
            "model": getattr(record, "model", None),
            "prompt_tokens": getattr(record, "prompt_tokens", None),
            "completion_tokens": getattr(record, "completion_tokens", None),
            "total_tokens": getattr(record, "total_tokens", None),
            "cost_usd": getattr(record, "cost_usd", None),
            "status": getattr(record, "status", None),
            "extra": self._extract_extra(record),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )

    def _extract_extra(self, record: logging.LogRecord) -> dict[str, Any]:
        extra: dict[str, Any] = {}

        for key, value in record.__dict__.items():
            if key in self._standard_keys or key.startswith("_"):
                continue

            try:
                # If already JSON serializable, keep it.
                json.dumps(value)
                extra[key] = value
            except TypeError:
                # Otherwise store a readable string.
                extra[key] = str(value)

        return extra