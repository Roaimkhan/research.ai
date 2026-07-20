from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.atsc.state import ProceduralConsolidationState
from src.retrieval.memory_events import MemoryEvent, read_memory_event_batch


def read_batch_node(
    state: ProceduralConsolidationState,
) -> ProceduralConsolidationState:
    """Read a batch of tool-execution memory events from Redis for consolidation."""
    try:
        raw_events = read_memory_event_batch(
            "tool_execution_stream",
            group_name="atsc_consolidation_workers",
            count=500,
            block_ms=5000,
        )

        if not raw_events:
            state["raw_events"] = []
            state["grouped_by_task"] = {}
            state["skipped_task_ids"] = []
            return state

        state["raw_events"] = list(raw_events)

        grouped_by_task: dict[str, list[MemoryEvent]] = defaultdict(list)
        for _, event in raw_events:
            grouped_by_task[str(event.source_id)].append(event)

        state["grouped_by_task"] = {
            task_id: events for task_id, events in grouped_by_task.items()
        }

        skipped_task_ids: list[str] = []
        for task_id, events in state["grouped_by_task"].items():
            ordered_events = sorted(events, key=lambda event: event.timestamp)
            final_event = ordered_events[-1]
            if final_event.payload.get("success") is not True:
                skipped_task_ids.append(task_id)

        state["skipped_task_ids"] = skipped_task_ids
        return state
    except Exception as exc:
        errors = state.get("errors", [])
        errors.append(
            {
                "task_id": None,
                "stage": "read_batch",
                "message": f"read_batch_node failed while reading tool execution events: {exc}",
            }
        )
        state["errors"] = errors
        return state
