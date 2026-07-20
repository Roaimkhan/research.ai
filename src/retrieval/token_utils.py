from __future__ import annotations

import json


def approximate_token_count(items: list[dict]) -> int:
    """
    Placeholder token estimator shared across retrieval nodes.

    Rough rule of thumb:
        ~1 token ~= 4 characters (English).
    """
    payload = json.dumps(items, default=str, ensure_ascii=False)
    return max(1, len(payload) // 4)