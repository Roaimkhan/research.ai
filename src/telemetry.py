from __future__ import annotations

from src.logging.decorators import track_call


def summarize() -> dict[str, object]:
    return {}


def is_failure_result(result: object) -> bool:
    return False
