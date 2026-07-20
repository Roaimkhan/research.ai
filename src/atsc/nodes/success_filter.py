from __future__ import annotations

from src.atsc.state import ProceduralConsolidationState
from src.retrieval.memory_events import MemoryEvent


def success_filter_node(
    state: ProceduralConsolidationState,
) -> ProceduralConsolidationState:
    """Build human-readable trace text for tasks that were not skipped."""
    try:
        skipped_task_ids = set(state.get("skipped_task_ids", []))
        grouped_by_task = state.get("grouped_by_task", {})

        trace_text_by_task: dict[str, str] = {}
        for task_id, events in grouped_by_task.items():
            if task_id in skipped_task_ids:
                continue

            ordered_events = sorted(events, key=lambda event: event.timestamp)
            formatted_events: list[str] = []
            for index, event in enumerate(ordered_events, start=1):
                payload = event.payload or {}
                formatted_events.append(
                    "\n".join(
                        [
                            f"Step {index}",
                            f"Timestamp: {event.timestamp}",
                            f"Tool: {payload.get('tool_name', '')}",
                            "Input:",
                            f"{payload.get('tool_input', '')}",
                            "",
                            "Output:",
                            f"{payload.get('tool_output', '')}",
                            "",
                            f"Success: {payload.get('success', '')}",
                        ]
                    )
                )

            trace_text_by_task[task_id] = "\n--------------------------------------------------\n".join(
                formatted_events
            )

        state["trace_text_by_task"] = trace_text_by_task
        return state
    except Exception as exc:
        errors = state.get("errors", [])
        errors.append(
            f"success_filter_node failed while formatting task traces: {exc}"
        )
        state["errors"] = errors
        return state
