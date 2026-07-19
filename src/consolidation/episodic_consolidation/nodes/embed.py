from __future__ import annotations

from src.consolidation.episodic_consolidation.state import ConsolidationState
from src.consolidation import embed_text   # change import path to wherever your function lives


EMBEDDING_DIM = 384


def embed_gist_node(state: ConsolidationState) -> ConsolidationState:
    scored_gists = state.get("scored_gists", [])

    if not scored_gists:
        state["embedded_gists"] = []
        return state

    embedded_gists: list[dict] = []

    for gist in scored_gists:
        session_id = gist["session_id"]

        try:
            embedding = embed_text(gist["gist_text"])

        except Exception as exc:
            state.setdefault("errors", []).append({
                "session_id": session_id,
                "stage": "embed",
                "message": str(exc),
            })
            continue

        if len(embedding) != EMBEDDING_DIM:
            state.setdefault("errors", []).append({
                "session_id": session_id,
                "stage": "embed",
                "message": f"invalid embedding length: {len(embedding)}",
            })
            continue

        embedded_gists.append(
            {
                **gist,
                "gist_embedding": embedding,
            }
        )

    state["embedded_gists"] = embedded_gists
    return state