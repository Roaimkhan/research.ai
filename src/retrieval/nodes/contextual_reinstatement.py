from __future__ import annotations

from src.persistence import episodic_store
from src.schemas import RetrievalState


def contextual_reinstatement_node(state: RetrievalState) -> RetrievalState:
    episodic_results = state.get("episodic_results")
    if not episodic_results:
        state["enriched_episodic_results"] = []
        return state

    enriched_results: list[dict] = []
    for gist in episodic_results:
        try:
            enriched_gist = dict(gist)

            session_context = episodic_store.get_session_summary(gist["session_id"])
            enriched_gist["session_context"] = session_context if session_context is not None else None

            before_neighbors = episodic_store.get_stag_neighbors(
                gist["gist_id"],
                direction="before",
            )
            neighbor_ids = [
                row["neighbor_gist_id"]
                for row in before_neighbors[:2]
                if row.get("neighbor_gist_id") is not None
            ]
            preceding_context = episodic_store.get_gist_texts_by_ids(neighbor_ids) if neighbor_ids else []
            enriched_gist["preceding_context"] = preceding_context[:2]

            enriched_results.append(enriched_gist)
        except Exception as exc:
            state.setdefault("errors", []).append(
                {
                    "stage": "contextual_reinstatement",
                    "gist_id": gist.get("gist_id"),
                    "message": str(exc),
                }
            )

    state["enriched_episodic_results"] = enriched_results
    return state
