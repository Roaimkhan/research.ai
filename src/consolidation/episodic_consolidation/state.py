from typing import TypedDict
from uuid import UUID
from datetime import datetime

import redis


class RawEpisodicEntry(TypedDict):
    redis_entry_id: str
    user_id: UUID
    thread_id: UUID
    session_id: UUID
    timestamp: datetime
    emotional_valence: str
    emotional_intensity: str
    emotional_labels: list[str]
    is_significant_event: bool
    temporal_expression: str | None
    raw_message_text: str


class ConsolidationState(TypedDict):
    raw_entries: list[RawEpisodicEntry]
    grouped_by_session: dict[str, list[RawEpisodicEntry]]
    synthesized_gists: list[dict]
    scored_gists: list[dict]
    raw_scores: list[dict]
    embedded_gists: list[dict]
    written_gist_ids: list[str]
    skipped_session_ids: list[str]
    successful_session_ids: list[str]
    errors: list[dict]


def ensure_consumer_group(
    r: redis.Redis,
    stream_name: str = "episodic_stream",
    group_name: str = "consolidation_workers",
):
    try:
        r.xgroup_create(name=stream_name, groupname=group_name, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
