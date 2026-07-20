from __future__ import annotations

from src.persistence import semantic_store
from src.retrieval.config import MAX_FUSED_RESULTS
from src.schemas import RetrievalState


def _tag_with_source(items: list[dict], source: str) -> list[dict]:
    tagged: list[dict] = []
    for item in items:
        item_copy = dict(item)
        item_copy["source"] = source
        tagged.append(item_copy)
    return tagged


def fusion_node(state: RetrievalState) -> RetrievalState:
    try:
        weights = semantic_store.get_active_baca_weights()
        episodic_ratio = weights["w_epi"]
        semantic_ratio = 1.0 - episodic_ratio

        semantic_results = state.get("semantic_results", [])
        episodic_results = state.get("enriched_episodic_results", [])

        # Deterministic allocation.
        semantic_slots = round(MAX_FUSED_RESULTS * semantic_ratio)
        episodic_slots = MAX_FUSED_RESULTS - semantic_slots

        selected_semantic = semantic_results[:semantic_slots]
        selected_episodic = episodic_results[:episodic_slots]

        semantic_overflow = semantic_results[semantic_slots:]
        episodic_overflow = episodic_results[episodic_slots:]

        remaining_capacity = (
            MAX_FUSED_RESULTS
            - len(selected_semantic)
            - len(selected_episodic)
        )

        if remaining_capacity > 0:
            if len(selected_semantic) < semantic_slots:
                # Semantic underfilled -> allocate remaining capacity to episodic.
                selected_episodic.extend(
                    episodic_overflow[:remaining_capacity]
                )
            elif len(selected_episodic) < episodic_slots:
                # Episodic underfilled -> allocate remaining capacity to semantic.
                selected_semantic.extend(
                    semantic_overflow[:remaining_capacity]
                )
            else:
                # Defensive fallback (normally unreachable).
                overflow = semantic_overflow + episodic_overflow
                selected_semantic.extend(overflow[:remaining_capacity])

        fused_results = (
            _tag_with_source(selected_semantic, "semantic")
            + _tag_with_source(selected_episodic, "episodic")
        )

        state["fused_results"] = fused_results[:MAX_FUSED_RESULTS]
        return state

    except Exception as exc:
        state.setdefault("errors", []).append(
            {
                "stage": "fusion",
                "message": str(exc),
            }
        )
        state["fused_results"] = []
        return state