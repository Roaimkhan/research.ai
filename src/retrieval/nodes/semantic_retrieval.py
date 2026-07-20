from datetime import datetime, timezone
from src.utils import embed_text
from src.persistence import semantic_store
from src.retrieval.config import SEMANTIC_TOP_K
from src.retrieval.scoring import score_semantic_candidates
from src.schemas import RetrievalState
from src.logging import get_logger, record_retrieval_event
import time

logger = get_logger(__name__)

def semantic_retrieval_node(state: RetrievalState) -> RetrievalState:
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
        as_of = datetime.now(timezone.utc)

        semantic_candidates = semantic_store.retrieve_semantic_candidates(
            user_id=state["user_id"],
            query_embedding=state["query_embedding"],
            as_of=as_of,
        )
        retrieved_count = len(semantic_candidates)

        scored_candidates = score_semantic_candidates(
            semantic_candidates,
            state["query_embedding"],
            state["resolved_query_text"],
            weights,
            as_of,
        )

        top_k_results = scored_candidates[:SEMANTIC_TOP_K]
        state["semantic_results"] = top_k_results
        
        # Log retrieval metrics
        try:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "Semantic retrieval: %d retrieved → %d top-k",
                retrieved_count,
                len(top_k_results),
                extra={"retrieval_stage": "semantic", "retrieved": retrieved_count, "selected": len(top_k_results), "duration_ms": duration_ms}
            )
        except Exception:
            pass
        return state
    except Exception as exc:
        try:
            logger.error("Semantic retrieval failed: %s", str(exc))
        except Exception:
            pass
        state.setdefault("errors", []).append(
            {
                "stage": "semantic_retrieval",
                "message": str(exc),
            }
        )
        state["semantic_results"] = []
        return state
