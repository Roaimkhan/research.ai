from __future__ import annotations

from src.atsc.state import ProceduralConsolidationState
from src.retrieval.memory_events import redis


def ack_batch_node(
    state: ProceduralConsolidationState,
) -> ProceduralConsolidationState:
    """Acknowledge successful and skipped Redis stream entries using the fail-closed policy."""
    try:
        successful = set(state.get("successful_task_ids", []))
        skipped = set(state.get("skipped_task_ids", []))
        failed = {
            entry["task_id"]
            for entry in state.get("errors", [])
            if entry.get("task_id") is not None
        }

        errors = state.setdefault("errors", [])
        raw_events = state.get("raw_events", [])

        for redis_entry_id, event in raw_events:
            task_id = str(event.source_id)
            if task_id in failed:
                continue
            if task_id in successful or task_id in skipped:
                try:
                    redis.xack(
                        "tool_execution_stream",
                        "atsc_consolidation_workers",
                        redis_entry_id,
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "task_id": task_id,
                            "stage": "ack_batch",
                            "message": str(exc),
                        }
                    )

        state["errors"] = errors
        return state
    except Exception as exc:
        errors = state.get("errors", [])
        errors.append(
            {
                "task_id": None,
                "stage": "ack_batch",
                "message": f"ack_batch_node failed: {exc}",
            }
        )
        state["errors"] = errors
        return state
