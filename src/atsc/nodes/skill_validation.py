from __future__ import annotations

import re
from pydantic import BaseModel

from src.atsc.state import ProceduralConsolidationState
from src.clients.qwen_client import qwen_client


SECRET_PATTERNS = [
    r"(?i)api[_-]?key\s*[=:]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]",
    r"/home/[a-zA-Z0-9_\-]+/",
    r"(?i)password\s*[=:]\s*['\"].+['\"]",
]


class SkillValidationVerdict(BaseModel):
    is_valid: bool
    generality_score: float
    reasoning: str
    issues: list[str]


PROMPT_TEMPLATE = (
    "Evaluate the following synthesized procedural skill against the original execution trace.\n\n"
    "Assess whether the skill is reusable and sufficiently general, whether it contains unnecessary hardcoded values, whether it faithfully represents the original trace, whether it introduces hallucinated or unsupported steps, and whether it is suitable to persist as procedural memory.\n\n"
    "Synthesized skill:\n\n"
    "{skill_text}\n\n"
    "Original execution trace:\n\n"
    "{trace_text}\n"
)


def skill_validation_node(
    state: ProceduralConsolidationState,
) -> ProceduralConsolidationState:
    """Validate synthesized skill drafts against their original execution traces."""
    try:
        synthesized_drafts = state.get("synthesized_drafts", [])
        trace_text_by_task = state.get("trace_text_by_task", {})
        validated_skills = state.setdefault("validated_skills", [])
        rejected_skills = state.setdefault("rejected_skills", [])
        errors = state.setdefault("errors", [])

        for draft_entry in synthesized_drafts:
            task_id = draft_entry.get("task_id")
            extraction = draft_entry.get("extraction")
            if not task_id or extraction is None:
                continue

            draft_payload = getattr(extraction, "payload", None)
            skill_body = getattr(draft_payload, "skill_body_markdown", "") if draft_payload is not None else ""
            trace_text = trace_text_by_task.get(task_id, "")

            matched_pattern = None
            for pattern in SECRET_PATTERNS:
                if re.search(pattern, skill_body):
                    matched_pattern = pattern
                    break

            if matched_pattern is not None:
                verdict = SkillValidationVerdict(
                    is_valid=False,
                    generality_score=0.0,
                    reasoning=f"Matched secret/path pattern: {matched_pattern}",
                    issues=[matched_pattern],
                )
                rejected_skills.append(
                    {
                        "task_id": task_id,
                        "original_extraction": extraction,
                        "validation_verdict": verdict,
                    }
                )
                continue

            messages = [
                {
                    "role": "system",
                    "content": PROMPT_TEMPLATE.format(
                        skill_text=skill_body,
                        trace_text=trace_text,
                    ),
                },
                {"role": "user", "content": ""},
            ]

            structured_llm = qwen_client.with_structured_output(SkillValidationVerdict)
            try:
                response = structured_llm.invoke(messages)
                verdict = SkillValidationVerdict(
                    is_valid=bool(getattr(response, "is_valid", False)),
                    generality_score=float(getattr(response, "generality_score", 0.0)),
                    reasoning=str(getattr(response, "reasoning", "")),
                    issues=list(getattr(response, "issues", []) or []),
                )
            except Exception as exc:
                errors.append(
                    {
                        "task_id": task_id,
                        "stage": "skill_validation",
                        "message": str(exc),
                    }
                )
                continue

            if verdict.is_valid:
                validated_skills.append(
                    {
                        "task_id": task_id,
                        "original_extraction": extraction,
                        "validation_verdict": verdict,
                    }
                )
            else:
                rejected_skills.append(
                    {
                        "task_id": task_id,
                        "original_extraction": extraction,
                        "validation_verdict": verdict,
                    }
                )

        state["validated_skills"] = validated_skills
        state["rejected_skills"] = rejected_skills
        state["errors"] = errors
        return state
    except Exception as exc:
        errors = state.get("errors", [])
        errors.append(
            {
                "task_id": None,
                "stage": "skill_validation",
                "message": f"skill_validation_node failed: {exc}",
            }
        )
        state["errors"] = errors
        return state
