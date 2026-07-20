from __future__ import annotations

from src.atsc.state import ProceduralConsolidationState
from src.memory.procedural_store import append_source_task, find_similar_skill
from src.utils import embed_text


def dedup_check_node(
    state: ProceduralConsolidationState,
) -> ProceduralConsolidationState:
    """Deduplicate validated skills by trigger-pattern similarity."""
    try:
        validated_skills = state.get("validated_skills", [])
        deduped_skills = state.setdefault("deduped_skills", [])
        errors = state.setdefault("errors", [])

        user_id = None
        request_context = state.get("requestcontext")
        if request_context is not None and hasattr(request_context, "user_id"):
            user_id = getattr(request_context, "user_id")

        for skill_entry in validated_skills:
            task_id = skill_entry.get("task_id")
            extraction = skill_entry.get("original_extraction")
            if not task_id or extraction is None:
                continue

            payload = getattr(extraction, "payload", None)
            trigger_pattern = getattr(payload, "trigger_pattern", "") if payload is not None else ""

            try:
                trigger_embedding = embed_text(trigger_pattern)
                existing_skill_id = find_similar_skill(trigger_embedding, user_id)
            except Exception as exc:
                errors.append(
                    {
                        "task_id": task_id,
                        "stage": "dedup_check",
                        "message": str(exc),
                    }
                )
                continue

            if existing_skill_id is not None:
                try:
                    append_source_task(existing_skill_id, task_id)
                except Exception as exc:
                    errors.append(
                        {
                            "task_id": task_id,
                            "stage": "dedup_check",
                            "message": str(exc),
                        }
                    )
                continue
            skill_entry["trigger_embedding"] = trigger_embedding
            deduped_skills.append(skill_entry)

        state["deduped_skills"] = deduped_skills
        state["errors"] = errors
        return state
    except Exception as exc:
        errors = state.get("errors", [])
        errors.append(
            {
                "task_id": None,
                "stage": "dedup_check",
                "message": f"dedup_check_node failed: {exc}",
            }
        )
        state["errors"] = errors
        return state
