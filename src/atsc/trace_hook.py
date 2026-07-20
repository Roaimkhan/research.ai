from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from src.retrieval.memory_events import MemoryEvent, emit_memory_event
from src.schemas.agent import AgentState


def _coerce_uuid(value: Any) -> UUID:
    if value is None:
        return uuid4()
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except Exception:
        return uuid4()


def _resolve_state_value(state: AgentState, *candidate_keys: str) -> Any:
    for key in candidate_keys:
        if key in state:
            return state[key]

    request_context = state.get("requestcontext")
    if request_context is None:
        return None

    for key in candidate_keys:
        if hasattr(request_context, key):
            return getattr(request_context, key)
    return None


def trace_logger_hook(
    state: AgentState,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_output: dict[str, Any],
    success: bool,
) -> None:
    """
    Emit a fire-and-forget tool-execution memory event without changing the
    existing tool-execution flow.
    """
    try:
        request_context = state.get("requestcontext") if isinstance(state, dict) else None
        user_id = None
        if request_context is not None and hasattr(request_context, "user_id"):
            user_id = getattr(request_context, "user_id")
        if user_id is None:
            user_id = state.get("user_id") if isinstance(state, dict) else None

        workspace_id = getattr(request_context, "workspace_id", None)
        source_id = _resolve_state_value(state, "task_id", "conversation_id", "thread_id", "session_id", "run_id")

        event = MemoryEvent(
            event_id=uuid4(),
            event_type="tool_execution",
            user_id=_coerce_uuid(user_id),
            workspace_id=_coerce_uuid(workspace_id) if workspace_id is not None else None,
            source_id=str(source_id) if source_id is not None else "unknown",
            timestamp=datetime.utcnow(),
            payload={
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_output": tool_output,
                "success": success,
            },
            provenance_uri=f"tool_execution://{source_id or 'unknown'}/{tool_name}",
        )
        emit_memory_event("tool_execution_stream", event)
    except Exception:
        # Keep this hook best-effort and non-disruptive.
        return
