from __future__ import annotations

import math
from datetime import datetime

from rank_bm25 import BM25Okapi

from src.persistence.semantic_store import  get_serg_proximity

def _cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(l * r for l, r in zip(left, right))
    left_norm = math.sqrt(sum(l * l for l in left))
    right_norm = math.sqrt(sum(r * r for r in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)




def score_semantic_candidates(
    candidates: list[dict],
    query_embedding: list[float],
    resolved_query_text: str,
    weights: dict[str, float],
    as_of: datetime,
) -> list[dict]:
    if not candidates:
        return []

    corpus = [
        f"{candidate['subject']} {candidate['predicate']} {candidate['object']}".lower().split()
        for candidate in candidates
    ]
    bm25 = BM25Okapi(corpus)
    query_tokens = resolved_query_text.lower().split()
    bm25_scores = bm25.get_scores(query_tokens)
    max_bm25 = max(bm25_scores) if len(bm25_scores) > 0 else 0.0

    scored_candidates: list[dict] = []
    for index, candidate in enumerate(candidates):
        fact_embedding = candidate.get("fact_embedding")
        s_cos = _cosine_similarity(fact_embedding, query_embedding) if fact_embedding is not None else 0.0
        s_bm25_normalized = bm25_scores[index] / max_bm25 if max_bm25 > 0.0 else 0.0
        s_prox = get_serg_proximity(candidate["subject"], candidate["predicate"], [])
        decay_term = (as_of - candidate["transaction_start"]).total_seconds() / 3600.0

        scored_candidate = dict(candidate)
        scored_candidate["score"] = (
            weights["w_sem"] * s_cos
            + weights["w_key"] * s_bm25_normalized
            + weights["w_graph"] * s_prox
            - weights["lambda_decay"] * decay_term
        )
        scored_candidates.append(scored_candidate)

    scored_candidates.sort(key=lambda candidate: candidate["score"], reverse=True)
    return scored_candidates


def score_episodic_candidates(
    candidates: list[dict],
    query_embedding: list[float],
    weights: dict[str, float],
) -> list[dict]:
    if not candidates:
        return []

    scored_candidates: list[dict] = []
    for candidate in candidates:
        similarity = _cosine_similarity(candidate["gist_embedding"], query_embedding)
        episodic_score = (
            weights["w_imp"] * candidate["importance_score_current"]
            + weights["w_sim"] * similarity
        )

        scored_candidate = dict(candidate)
        scored_candidate["episodic_score"] = episodic_score
        scored_candidates.append(scored_candidate)

    scored_candidates.sort(key=lambda candidate: candidate["episodic_score"], reverse=True)
    return scored_candidates