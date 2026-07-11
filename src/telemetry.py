from __future__ import annotations

import inspect
import json
import logging
import time
from collections import defaultdict
from functools import wraps
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

_TELEMETRY_LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "telemetry.jsonl"


def track_call(call_type: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(function):

            @wraps(function)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                started_at = time.time()
                monotonic_start = time.perf_counter()
                success = True
                error_type: str | None = None
                result: Any = None
                try:
                    result = await function(*args, **kwargs)
                    if is_failure_result(result):
                        success = False
                        error_type = _extract_error_type(result)
                    return result
                except Exception as error:
                    success = False
                    error_type = type(error).__name__
                    raise
                finally:
                    _append_event(
                        {
                            "timestamp": started_at,
                            "call_type": call_type,
                            "latency_ms": int((time.perf_counter() - monotonic_start) * 1000),
                            "prompt_tokens": _extract_prompt_tokens(args, result),
                            "completion_tokens": _extract_completion_tokens(args, result),
                            "success": success,
                            "error_type": error_type,
                        }
                    )

            return async_wrapper

        @wraps(function)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            started_at = time.time()
            monotonic_start = time.perf_counter()
            success = True
            error_type: str | None = None
            result: Any = None
            try:
                result = function(*args, **kwargs)
                if is_failure_result(result):
                    success = False
                    error_type = _extract_error_type(result)
                return result
            except Exception as error:
                success = False
                error_type = type(error).__name__
                raise
            finally:
                _append_event(
                    {
                        "timestamp": started_at,
                        "call_type": call_type,
                        "latency_ms": int((time.perf_counter() - monotonic_start) * 1000),
                        "prompt_tokens": _extract_prompt_tokens(args, result),
                        "completion_tokens": _extract_completion_tokens(args, result),
                        "success": success,
                        "error_type": error_type,
                    }
                )

        return sync_wrapper

    return decorator


def summarize() -> dict[str, Any]:
    events = _read_events()
    if not events:
        return {
            "avg_latency_ms": 0.0,
            "total_tokens": 0,
            "tokens_per_call_type": {},
            "error_rate": 0.0,
        }

    total_latency = 0.0
    total_tokens = 0
    total_errors = 0
    tokens_per_call_type: dict[str, int] = defaultdict(int)

    for event in events:
        call_type = str(event.get("call_type", "unknown"))
        latency_ms = float(event.get("latency_ms", 0) or 0)
        prompt_tokens = int(event.get("prompt_tokens") or 0)
        completion_tokens = int(event.get("completion_tokens") or 0)
        success = bool(event.get("success", True))

        total_latency += latency_ms
        tokens = prompt_tokens + completion_tokens
        total_tokens += tokens
        tokens_per_call_type[call_type] += tokens
        if not success:
            total_errors += 1

    total_calls = len(events)
    return {
        "avg_latency_ms": total_latency / total_calls,
        "total_tokens": total_tokens,
        "tokens_per_call_type": dict(tokens_per_call_type),
        "error_rate": total_errors / total_calls,
    }


def _append_event(event: dict[str, Any]) -> None:
    try:
        _TELEMETRY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _TELEMETRY_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    except Exception:
        logger.exception("Failed to append telemetry event")


def _read_events() -> list[dict[str, Any]]:
    if not _TELEMETRY_LOG_PATH.exists():
        return []

    events: list[dict[str, Any]] = []
    with _TELEMETRY_LOG_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
    return events


def _extract_prompt_tokens(args: tuple[Any, ...], result: Any) -> int | None:
    telemetry = _extract_telemetry(args, result)
    if telemetry is not None:
        return getattr(telemetry, "prompt_tokens", None)
    return None


def _extract_completion_tokens(args: tuple[Any, ...], result: Any) -> int | None:
    telemetry = _extract_telemetry(args, result)
    if telemetry is not None:
        return getattr(telemetry, "completion_tokens", None)
    return None


def _extract_telemetry(args: tuple[Any, ...], result: Any) -> Any | None:
    if result is not None:
        telemetry = getattr(result, "qwen_telemetry", None)
        if telemetry is not None:
            return telemetry
        usage = getattr(result, "usage", None)
        if usage is not None:
            return usage

    if args:
        first_arg = args[0]
        telemetry = getattr(first_arg, "last_telemetry", None)
        if telemetry is not None:
            return telemetry

    return None


def _extract_error_type(result: Any) -> str | None:
    if isinstance(result, dict):
        error_value = result.get("error")
        if isinstance(error_value, dict):
            error_type = error_value.get("type")
            if error_type:
                return str(error_type)
        if error_value is not None:
            return "tool_error"

        content = result.get("content")
        if isinstance(content, str):
            try:
                parsed_content = json.loads(content)
            except Exception:
                return None
            if isinstance(parsed_content, dict):
                error_value = parsed_content.get("error")
                if isinstance(error_value, dict):
                    error_type = error_value.get("type")
                    if error_type:
                        return str(error_type)
                if error_value is not None:
                    return "tool_error"

    return None


def is_failure_result(result: Any) -> bool:
    if isinstance(result, dict):
        if result.get("error") is not None and result.get("role") != "tool":
            return True
        if result.get("role") == "tool" and isinstance(result.get("content"), str):
            try:
                content = json.loads(result["content"])
            except Exception:
                return False
            return isinstance(content, dict) and (content.get("ok") is False or content.get("error") is not None)
    return False
