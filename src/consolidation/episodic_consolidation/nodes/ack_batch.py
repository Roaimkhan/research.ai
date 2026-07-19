import logging

import redis

from src.consolidation.episodic_consolidation.state import ConsolidationState

logger = logging.getLogger(__name__)


def ack_batch_node(state: ConsolidationState) -> ConsolidationState:
    successful = set(state.get("successful_session_ids", []))
    skipped = set(state.get("skipped_session_ids", []))
    failed = {e["session_id"] for e in state.get("errors", []) if "session_id" in e}

    try:
        r = redis.Redis()
    except Exception:
        return state

    for entry in state.get("raw_entries", []):
        sid = str(entry["session_id"])
        redis_entry_id = entry["redis_entry_id"]

        if sid in failed:
            logger.warning(
                f"Not ACKing entry {redis_entry_id}: session {sid} failed."
            )
            continue

        if sid in successful or sid in skipped:
            r.xack("episodic_stream", "consolidation_workers", redis_entry_id)
            continue

        logger.error(
            f"UNCLASSIFIED session {sid} for entry {redis_entry_id} — "
            f"not in successful, skipped, or failed. Leaving pending."
        )

    return state
