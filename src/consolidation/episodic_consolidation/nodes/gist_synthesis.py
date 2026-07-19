from pydantic import BaseModel, Field
from typing import Sequence, Mapping

from src.clients.qwen_client import qwen_client
from src.consolidation.episodic_consolidation.state import ConsolidationState, RawEpisodicEntry


class GistSynthesisOutput(BaseModel):
    gist_text: str = Field(
        description="A compressed 1-3 sentence summary of what happened in "
                    "this session slice — the event, decision, or reaction, "
                    "not a verbatim transcript."
    )
    dominant_emotion_label: str = Field(
        description="The single most prominent emotion CATEGORY across this batch, "
                    "e.g. 'frustration', 'joy', 'relief'. This is a readable label "
                    "for humans/metadata only — it is NEVER used for numeric scoring. "
                    "Scoring reads emotional_intensity directly from raw entries "
                    "instead (see Step 3.5)."
    )


PROMPT_TEMPLATE = (
    "Summarize the following sequence of user interactions into a single\n"
    "compressed gist. Focus on what happened, what was decided, or how the user\n"
    "reacted — not routine chit-chat. Do not invent details not present in the\n"
    "text.\n\n"
    "Interactions (chronological):\n"
    "{formatted_entries}\n\n"
    "Output only the structured gist."
)


def episodic_gist_synthesis_node(state: ConsolidationState) -> ConsolidationState:
    grouped = state.get("grouped_by_session", {})
    synthesized: list[dict] = []

    for session_id, entries in grouped.items():
        if not entries:
            continue

        if session_id in state.get("skipped_session_ids", []):
            continue

        session_entries = sorted(entries, key=lambda entry: entry["timestamp"])

        formatted_entries = "\n".join(
            "- {timestamp}: {text} | valence={valence} | intensity={intensity} "
            "| labels={labels} | significant={significant}".format(
                timestamp=entry["timestamp"],
                text=entry["raw_message_text"],
                valence=entry["emotional_valence"],
                intensity=entry["emotional_intensity"],
                labels=entry["emotional_labels"],
                significant=entry["is_significant_event"],
            )
            for entry in session_entries
        )

        prompt = PROMPT_TEMPLATE.format(formatted_entries=formatted_entries)

        # Use the centralized Qwen client for structured output
        messages: list[Mapping[str, str]] = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": ""},
        ]

        structured_llm = qwen_client.with_structured_output(GistSynthesisOutput)
        try:
            response = structured_llm.invoke(messages)
        except Exception as exc:
            state.setdefault("errors", []).append({
                "session_id": session_id,
                "stage": "gist_synthesis",
                "message": str(exc),
            })
            continue

        synthesized.append(
            {
                "session_id": session_id,
                "user_id": session_entries[0]["user_id"],
                "gist_text": getattr(response, "gist_text", None),
                "dominant_emotion_label": getattr(response, "dominant_emotion_label", None),
                "source_entry_ids": [entry["redis_entry_id"] for entry in session_entries],
                "recorded_at": session_entries[-1]["timestamp"],
                "session_start_candidate": session_entries[0]["timestamp"],
            }
        )

    state["synthesized_gists"] = state.get("synthesized_gists", []) + synthesized
    return state
