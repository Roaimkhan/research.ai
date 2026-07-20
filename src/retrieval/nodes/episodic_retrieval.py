from __future__ import annotations

import math
import time

from src.utils import embed_text
from src.persistence import semantic_store
from src.persistence import episodic_store
from src.retrieval.config import EPISODIC_TOP_K
from src.retrieval.scoring import score_episodic_candidates
from src.schemas import RetrievalState
from src.logging import get_logger

logger = get_logger(__name__)

def episodic_retrieval_node(state: RetrievalState) -> RetrievalState:
    started = time.perf_counter()
    try:
        query_embedding = state.get("query_embedding")
        if query_embedding is None:
            resolved_query = state.get("resolved_query_text")
            if not resolved_query:
                raise ValueError("resolved_query_text missing from RetrievalState")
            query_embedding = embed_text(resolved_query)
            state["query_embedding"] = query_embedding

        weights = semantic_store.get_active_baca_weights()

        candidates = episodic_store.retrieve_episodic_candidates(
            user_id=state["user_id"],
            min_importance=0.0,
        )
        retrieved_count = len(candidates)

        scored_candidates = score_episodic_candidates(
            candidates,
            state["query_embedding"],
            weights,
        )

        top_results = scored_candidates[:EPISODIC_TOP_K]

        episodic_store.reactivate_gists([gist["gist_id"] for gist in top_results])

        state["episodic_results"] = top_results
        
        # Log retrieval metrics
        try:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "Episodic retrieval: %d retrieved → %d top-k",
                retrieved_count,
                len(top_results),
                extra={"retrieval_stage": "episodic", "retrieved": retrieved_count, "selected": len(top_results), "duration_ms": duration_ms}
            )
        except Exception:
            pass
        return state
    except Exception as exc:
        try:
            logger.error("Episodic retrieval failed: %s", str(exc))
        except Exception:
            pass
        state.setdefault("errors", []).append(
            {
                "stage": "episodic_retrieval",
                "message": str(exc),
            }
        )
        state["episodic_results"] = []
        return state
