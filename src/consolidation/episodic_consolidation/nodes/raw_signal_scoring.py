from src.consolidation.episodic_consolidation.state import ConsolidationState


INTENSITY_WEIGHTS = {
    "HIGH": 1.0,
    "MEDIUM": 0.5,
    "LOW": 0.1,
}


def raw_signal_scoring_node(state: ConsolidationState) -> ConsolidationState:
    grouped = state.get("grouped_by_session", {})
    raw_scores: list[dict] = []

    for session_id, entries in grouped.items():
        if not entries:
            continue

        if session_id in state.get("skipped_session_ids", []):
            continue

        entity_salience_score = 0.5
        outcome_score = 0.5

        raw_scores.append(
            {
                "session_id": session_id,
                "user_id": entries[0]["user_id"],
                "entity_salience_score": entity_salience_score,
                "outcome_score": outcome_score,
            }
        )

    state["raw_scores"] = raw_scores
    return state
