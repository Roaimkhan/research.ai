from typing import TypedDict
from shared.extraction_contract import ExtractionResult
from retrieval.memory_events import MemoryEvent

class ProceduralConsolidationState(TypedDict):
    raw_events: list[tuple[str, MemoryEvent]]   # (redis_entry_id, event)
    grouped_by_task: dict[str, list[tuple[str, MemoryEvent]]]
    skipped_task_ids: list[str]
    trace_text_by_task: dict[str, str]
    synthesized_drafts: list[dict]                # {"task_id":..., "extraction": ExtractionResult}
    validated_skills: list[dict]
    rejected_skills: list[dict]
    deduped_skills: list[dict]
    written_skill_ids: list[str]
    successful_task_ids: list[str]
    errors: list[dict]                             # {"task_id":..., "stage":..., "message":...}
