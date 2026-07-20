from __future__ import annotations

from pydantic import BaseModel

from src.atsc.state import ProceduralConsolidationState
from src.clients.qwen_client import qwen_client
from src.shared.extraction_contract import wrap_extraction


class SkillDraft(BaseModel):
    skill_name: str
    trigger_pattern: str
    skill_body_markdown: str


class SkillSynthesisOutput(BaseModel):
    skill_name: str
    trigger_pattern: str
    skill_body_markdown: str
    confidence: float


PROMPT_TEMPLATE = (
    "Given the following successful tool-execution trace, synthesize a reusable procedural skill.\n\n"
    "Generalize the workflow instead of copying literal values, URLs, prompts, IDs, or user-specific information.\n\n"
    "Produce:\n"
    "- skill_name\n"
    "- trigger_pattern (when this skill should be considered)\n"
    "- skill_body_markdown (a reusable SKILL.md body)\n"
    "- confidence (0.0-1.0 indicating how reusable/general this skill is)\n\n"
    "Trace:\n\n"
    "{trace_text}\n"
)


def skill_synthesis_node(
    state: ProceduralConsolidationState,
) -> ProceduralConsolidationState:
    """Synthesize reusable skill drafts from successful task traces."""
    try:
        trace_text_by_task = state.get("trace_text_by_task", {})
        if not trace_text_by_task:
            state.setdefault("synthesized_drafts", [])
            return state

        synthesized_drafts = state.setdefault("synthesized_drafts", [])
        errors = state.setdefault("errors", [])

        for task_id, trace_text in trace_text_by_task.items():
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert at extracting reusable procedural skills "
                        "from successful execution traces."
                    ),
                },
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(trace_text=trace_text),
                },
            ]
            structured_llm = qwen_client.with_structured_output(SkillSynthesisOutput)
            try:
                response = structured_llm.invoke(messages)
            except Exception as exc:
                errors.append(
                    {
                        "task_id": task_id,
                        "stage": "skill_synthesis",
                        "message": str(exc),
                    }
                )
                continue

            payload = SkillDraft(
                skill_name=getattr(response, "skill_name", ""),
                trigger_pattern=getattr(response, "trigger_pattern", ""),
                skill_body_markdown=getattr(response, "skill_body_markdown", ""),
            )
            synthesized_drafts.append(
                {
                    "task_id": task_id,
                    "extraction": wrap_extraction(
                        payload=payload,
                        confidence = max(0.0,min(1.0,float(getattr(response, "confidence", 0.0)),),),
                        extractor_name="skill_synthesis_node",
                    ),
                }
            )

        state["synthesized_drafts"] = synthesized_drafts
        state["errors"] = errors
        return state
    except Exception as exc:
        errors = state.get("errors", [])
        errors.append(
            {
                "stage": "skill_synthesis",
                "message": f"skill_synthesis_node failed: {exc}",
            }
        )
        state["errors"] = errors
        return state
