from dateparser import parse
from datetime import datetime
from typing import Optional, Literal, Union
from src.schemas import AgentState, ExtractionResult, MemoryBatch, MemoryRecord


def temporal_expression_resolver(
    state: AgentState,
    message_timestamp: datetime,
    conversation_id: str,
    message_id: str,
) -> AgentState:
    """
    LangGraph node: resolves valid_start/valid_end for each extracted memory.
    Does NOT touch termination, DB lookups, or prior-fact matching —
    that belongs to a separate module.
    """
    extraction_result = state.get("samantic_memories_raw")

    if (
        extraction_result is None
        or not extraction_result.should_write
        or not extraction_result.memmories
    ):
        state["samantic_memories_processed"] = MemoryBatch()
        return state

    memory_batch = MemoryBatch()

    for memory in extraction_result.memmories:

        valid_start, valid_end, was_inferred = resolve_valid_range(
            start_expr=memory.temporal_start_expression,
            end_expr=memory.temporal_end_expression,
            is_ongoing=memory.is_ongoing,
            message_timestamp=message_timestamp,
        )

        confidence_score = 0.6 if was_inferred else 0.95

        provenance_uri = (
            f"memory://conversation/{conversation_id}"
            f"/message/{message_id}#fact={memory.fact_id}"
        )

        memory_record = MemoryRecord(
            **memory.model_dump(exclude={"temporal_start_expression", "temporal_end_expression", "is_ongoing"}),
            valid_start=valid_start,
            valid_end=valid_end,
            provenance_uri=provenance_uri,
            confidence_score=confidence_score,
        )

        memory_batch.memmories.append(memory_record)

    state["samantic_memories_processed"] = memory_batch
    return state


def resolve_valid_range(
    start_expr: Optional[str],
    end_expr: Optional[str],
    is_ongoing: bool,
    message_timestamp: datetime,
) -> tuple[datetime, Optional[datetime], bool]:
    """
    Resolves (valid_start, valid_end, was_inferred) for one extracted fact.

    valid_start : NEVER None (schema NOT NULL). Falls back to message_timestamp
                  when no temporal signal exists or parsing fails.
    valid_end   : None = open-ended (ongoing OR unknown — collapsed by design).
                  datetime = explicitly closed.
    was_inferred: True if valid_start had no real signal — use to discount
                  confidence_score downstream.
    """
    # ---- valid_start ----
    was_inferred = False

    if not start_expr:
        valid_start = message_timestamp
        was_inferred = True
    else:
        resolved_start = parse(
            start_expr,
            settings={"RELATIVE_BASE": message_timestamp, "PREFER_DATES_FROM": "past"},
        )
        if resolved_start is None:
            valid_start = message_timestamp
            was_inferred = True
        else:
            valid_start = resolved_start

    # ---- valid_end ----
    if is_ongoing:
        valid_end = None
    elif end_expr:
        resolved_end = parse(
            end_expr,
            settings={"RELATIVE_BASE": message_timestamp, "PREFER_DATES_FROM": "past"},
        )
        valid_end = resolved_end  # None if unparseable — stays open, not an error
    else:
        valid_end = None

    # ---- integrity guard: never let end precede start ----
    if valid_end is not None and valid_end < valid_start:
        valid_end = None

    return valid_start, valid_end, was_inferred