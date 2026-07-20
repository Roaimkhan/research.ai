from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List

from src.consolidation.episodic_consolidation.state import ConsolidationState
from src.persistence import episodic_store
from src.persistence.semantic_store import conn


SIMILARITY_THRESHOLD = 0.80


def compute_composite_importance_node(state: ConsolidationState) -> ConsolidationState:
    embedded = state.get("embedded_gists", [])
    if not embedded:
        return state

    successful_gists: List[dict] = []

    for gist in list(embedded):
        session_id = gist.get("session_id")
        try:
            user_id = gist.get("user_id")
            current_embedding = gist.get("gist_embedding")
            recorded_at = gist.get("recorded_at")

            if user_id is None or current_embedding is None or recorded_at is None:
                raise ValueError("missing required fields for importance computation")

            # 1) Recency factor
            now = datetime.now(timezone.utc)
            if getattr(recorded_at, "tzinfo", None) is None:
                recorded_at_utc = recorded_at.replace(tzinfo=timezone.utc)
            else:
                recorded_at_utc = recorded_at.astimezone(timezone.utc)
            delta_hours = (now - recorded_at_utc).total_seconds() / 3600.0
            f_rec = math.exp(-0.05 * delta_hours)

            # 2) Frequency and 3) Surprise via DB helpers — run inside a transaction cursor
            with conn.transaction():
                with conn.cursor() as cursor:
                    session_ids = episodic_store.get_recent_session_ids(cursor, user_id, limit=10)
                    similar_count = episodic_store.count_similar_recent_gists(
                        cursor, session_ids, current_embedding, SIMILARITY_THRESHOLD
                    )

                    f_freq = min(math.log(1 + similar_count) / math.log(11), 1.0)

                    centroid_row = episodic_store.get_user_centroid(cursor, user_id)
                    if centroid_row is None:
                        # no centroid yet -> maximal surprise
                        f_surp = 1.0
                        # prepare new centroid in memory
                        new_count = 1
                        new_centroid = list(current_embedding)
                    else:
                        centroid_embedding, embedding_count = centroid_row
                        # compute cosine similarity using DB helper to remain consistent with pgvector
                        cosine_sim = episodic_store.get_user_centroid_similarity(cursor, user_id, current_embedding)
                        if cosine_sim is None:
                            f_surp = 1.0
                        else:
                            f_surp = 1.0 - float(cosine_sim)

                        # compute new centroid incrementally in memory (do NOT persist here)
                        new_count = embedding_count + 1
                        new_centroid = [
                            c + (cur - c) / new_count for c, cur in zip(centroid_embedding, current_embedding)
                        ]

            # 4) Composite score — rely on entity_salience_score and outcome_score already present
            entity_salience = gist.get("entity_salience_score")
            outcome_score = gist.get("outcome_score")
            if entity_salience is None or outcome_score is None:
                raise ValueError("missing entity_salience_score or outcome_score required for composite")

            importance_score_initial = (
                0.25 * f_rec
                + 0.25 * f_freq
                + 0.20 * f_surp
                + 0.15 * entity_salience
                + 0.15 * outcome_score
            )

            # 5) Update gist in memory (in-place) with surprise and importance and new centroid info
            gist["bayesian_surprise_score"] = f_surp
            gist["importance_score_initial"] = importance_score_initial
            gist["new_centroid_embedding"] = new_centroid
            gist["new_centroid_count"] = new_count

            successful_gists.append(gist)

        except Exception as exc:
            state.setdefault("errors", []).append({
                "session_id": session_id,
                "stage": "compute_composite_importance",
                "message": str(exc),
            })
            # exclude gist by not adding to successful_gists

    # 3) Replace the embedded_gists list with successfully processed gists
    state["embedded_gists"] = successful_gists
    return state
