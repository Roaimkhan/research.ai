import json
import os
from typing import Any

import redis

from src.consolidation.episodic_consolidation.state import ConsolidationState, RawEpisodicEntry

BATCH_SIZE = 10


def read_batch_node(state: ConsolidationState) -> ConsolidationState:
    try:
        r = redis.Redis()
        raw = r.xreadgroup(
            groupname="consolidation_workers",
            consumername=f"worker-{os.getpid()}",
            streams={"episodic_stream": ">"},
            count=BATCH_SIZE,
            block=5000,
        )
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as exc:
        state.setdefault("errors", []).append({
            "session_id": "unknown",
            "stage": "read_batch",
            "message": str(exc),
        })
        return state

    if not raw:
        state["raw_entries"] = []
        state["grouped_by_session"] = {}
        state["skipped_session_ids"] = []
        return state

    entries: list[RawEpisodicEntry] = []
    for stream_name, stream_entries in raw:
        for entry_id, entry_fields in stream_entries:
            payload = json.loads(entry_fields["payload"])
            context = json.loads(entry_fields["context"])
            raw_message_text = entry_fields["raw_message_text"]

            entry: RawEpisodicEntry = {
                "redis_entry_id": entry_id,
                "user_id": context["user_id"],
                "thread_id": context["thread_id"],
                "session_id": context["session_id"],
                "timestamp": context["timestamp"],
                "emotional_valence": payload["emotional_valence"],
                "emotional_intensity": payload["emotional_intensity"],
                "emotional_labels": payload["emotional_labels"],
                "is_significant_event": payload["is_significant_event"],
                "temporal_expression": payload["temporal_expression"],
                "raw_message_text": raw_message_text,
            }
            entries.append(entry)
# ============================================
    state["raw_entries"] = entries
    grouped: dict[str, list[RawEpisodicEntry]] = {}
    for entry in entries:
        session_key = str(entry["session_id"])
        grouped.setdefault(session_key, []).append(entry)
# ============================================
    state["grouped_by_session"] = grouped
    state["skipped_session_ids"] = [
        sid for sid, entries in grouped.items()
        if not any(e["is_significant_event"] for e in entries)
    ]
    return state
