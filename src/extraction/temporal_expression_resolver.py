from dateparser import parse
from datetime import datetime
from typing import Optional
import uuid
from src.schemas import SemanticMemoryStagerState, MemoryBatch, MemoryRecord


def temporal_expression_resolver(state: SemanticMemoryStagerState) -> dict:
    """
    LangGraph node: resolves valid_start/valid_end for each extracted memory.
    """
    extraction_result = state.get("extraction_result")
    snapshot = state.get("snapshot")

    if not snapshot:
        raise ValueError("SemanticMemoryStagerState missing required 'snapshot' field.")

    message_timestamp = snapshot.message_timestamp
    conversation_id = snapshot.conversation_id
    message_id = snapshot.message_id

    if (
        extraction_result is None
        or not extraction_result.should_write
        or not extraction_result.memmories
    ):
        return {"memory_batch": MemoryBatch()}

    memory_batch = MemoryBatch()

    for memory in extraction_result.memmories:
        valid_start, valid_end, was_inferred = resolve_valid_range(
            start_expr=memory.temporal_start_expression,
            end_expr=memory.temporal_end_expression,
            is_ongoing=memory.is_ongoing,
            message_timestamp=message_timestamp,
        )

        confidence_score = 0.6 if was_inferred else 0.95

        # Generate fact_id on the spot as requested by the user
        fact_id = uuid.uuid4()
        
        provenance_uri = (
            f"memory://conversation/{conversation_id}"
            f"/message/{message_id}#fact={fact_id}"
        )

        memory_record = MemoryRecord(
            **memory.model_dump(exclude={"temporal_start_expression", "temporal_end_expression", "is_ongoing"}),
            fact_id=fact_id,
            valid_start=valid_start,
            valid_end=valid_end,
            provenance_uri=provenance_uri,
            confidence_score=confidence_score,
        )

        memory_batch.memmories.append(memory_record)

    return {"memory_batch": memory_batch}


def resolve_valid_range(
    start_expr: Optional[str],
    end_expr: Optional[str],
    is_ongoing: bool,
    message_timestamp: datetime,
) -> tuple[datetime, Optional[datetime], bool]:
    """
    Resolves (valid_start, valid_end, was_inferred) for one extracted fact.
    """
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

    if is_ongoing:
        valid_end = None
    elif end_expr:
        resolved_end = parse(
            end_expr,
            settings={"RELATIVE_BASE": message_timestamp, "PREFER_DATES_FROM": "past"},
        )
        valid_end = resolved_end
    else:
        valid_end = None

    if valid_end is not None and valid_end < valid_start:
        valid_end = None

    return valid_start, valid_end, was_inferred