from typing import Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
import json, os
import redis
import logging

logger = logging.getLogger(__name__)

class MemoryEvent(BaseModel):
    event_id: UUID
    event_type: Literal["chat_message", "tool_execution",
                         "hypothesis_statement", "document_ingest"]
    user_id: UUID
    workspace_id: UUID | None
    source_id: str
    timestamp: datetime
    payload: dict
    provenance_uri: str

def emit_memory_event(stream_name: str, event: MemoryEvent) -> None:
    """
    redis.xadd(stream_name, {"event": event.model_dump_json()})
    Wrap in try/except — log and swallow errors here, this is a
    fire-and-forget call from the hot path, must never raise back into
    the caller's main flow.
    """
    try:
        r = redis.Redis()
        r.xadd(stream_name, {"event": event.model_dump_json()})
    except Exception as exc:
        logger.error(f"Failed to emit memory event to {stream_name}: {exc}")

def read_memory_event_batch(stream_name: str, group_name: str,
                             count: int = 500, block_ms: int = 5000) -> list[tuple[str, MemoryEvent]]:
    """
    r.xreadgroup(groupname=group_name, consumername=f"worker-{os.getpid()}",
                  streams={stream_name: ">"}, count=count, block=block_ms)
    Parse each entry's "event" field via MemoryEvent.model_validate_json().
    Return [] on empty batch — not an error. Do NOT ack here; caller
    acks only after successful downstream processing (same rule as the
    existing episodic consolidation pattern).
    Each returned MemoryEvent must also carry its redis_entry_id for
    later acking — since MemoryEvent itself has no such field, return a
    list of tuples (str_entry_id, MemoryEvent) instead of bare MemoryEvent
    objects. Tell me if you'd rather add redis_entry_id as an extra
    field on MemoryEvent instead — either works, pick one and be
    consistent across all pillars that use this function.
    """
    try:
        r = redis.Redis()
        raw = r.xreadgroup(
            groupname=group_name,
            consumername=f"worker-{os.getpid()}",
            streams={stream_name: ">"},
            count=count,
            block=block_ms,
        )
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as exc:
        logger.error(f"Failed to read from {stream_name} group {group_name}: {exc}")
        return []

    if not raw:
        return []

    results: list[tuple[str, MemoryEvent]] = []
    for stream_name, stream_entries in raw:
        for entry_id, entry_fields in stream_entries:
            event_json = entry_fields.get("event")
            if event_json:
                try:
                    event = MemoryEvent.model_validate_json(event_json)
                    results.append((entry_id, event))
                except Exception as exc:
                    logger.error(f"Failed to parse memory event {entry_id}: {exc}")
    return results

def ensure_consumer_group(stream_name: str, group_name: str) -> None:
    """ Same idempotent xgroup_create pattern as episodic_stream's setup. """
    try:
        r = redis.Redis()
        r.xgroup_create(name=stream_name, groupname=group_name, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
