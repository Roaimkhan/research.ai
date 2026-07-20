from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from src.atsc.state import ProceduralConsolidationState
from src.memory.procedural_store import delete_skill, write_skill


def skill_file_writer_node(
    state: ProceduralConsolidationState,
) -> ProceduralConsolidationState:
    """Persist deduped skills to disk and database with rollback on partial failure."""
    try:
        deduped_skills = state.get("deduped_skills", [])
        written_skill_ids = state.setdefault("written_skill_ids", [])
        successful_task_ids = state.setdefault("successful_task_ids", [])
        errors = state.setdefault("errors", [])

        skills_dir = Path(".qwen/skills")
        skills_dir.mkdir(parents=True, exist_ok=True)

        for skill_entry in deduped_skills:
            task_id = skill_entry.get("task_id")
            extraction = skill_entry.get("original_extraction")
            if not task_id or extraction is None:
                continue

            payload = getattr(extraction, "payload", None)
            skill_name = getattr(payload, "skill_name", "") if payload is not None else ""
            trigger_pattern = getattr(payload, "trigger_pattern", "") if payload is not None else ""
            skill_body_markdown = getattr(payload, "skill_body_markdown", "") if payload is not None else ""
            trigger_embedding = skill_entry.get("trigger_embedding", [])
            validation_confidence = getattr(extraction, "confidence", 0.0)
            user_id = None
            workspace_id = None

            request_context = state.get("requestcontext")
            if request_context is not None:
                if hasattr(request_context, "user_id"):
                    user_id = getattr(request_context, "user_id")
                if hasattr(request_context, "workspace_id"):
                    workspace_id = getattr(request_context, "workspace_id")

            skill_id = uuid4()
            file_path = skills_dir / f"{skill_id}.md"

            try:
                file_path.write_text(skill_body_markdown, encoding="utf-8")
            except Exception as exc:
                errors.append(
                    {
                        "task_id": task_id,
                        "stage": "skill_file_writer",
                        "message": f"File write failed: {exc}",
                    }
                )
                continue

            try:
                write_skill(
                    skill_id=skill_id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    skill_name=skill_name,
                    trigger_pattern=trigger_pattern,
                    trigger_embedding=trigger_embedding,
                    file_path=str(file_path),
                    source_task_ids=[task_id],
                    validation_confidence=float(validation_confidence),
                )
            except Exception as exc:
                try:
                    if file_path.exists():
                        file_path.unlink()
                except Exception:
                    pass
                errors.append(
                    {
                        "task_id": task_id,
                        "stage": "skill_file_writer",
                        "message": f"Database insert failed: {exc}",
                    }
                )
                continue

            written_skill_ids.append(str(skill_id))
            successful_task_ids.append(task_id)

        state["written_skill_ids"] = written_skill_ids
        state["successful_task_ids"] = successful_task_ids
        state["errors"] = errors
        return state
    except Exception as exc:
        errors = state.get("errors", [])
        errors.append(
            {
                "task_id": None,
                "stage": "skill_file_writer",
                "message": f"skill_file_writer_node failed: {exc}",
            }
        )
        state["errors"] = errors
        return state
