from src.consolidation.episodic_consolidation.state import ConsolidationState


def merge_gist_and_scores_node(state: ConsolidationState) -> ConsolidationState:
    synthesized = state.get("synthesized_gists", [])
    raw_scores = state.get("raw_scores", [])
    score_lookup = {score["session_id"]: score for score in raw_scores}

    synthesized_session_ids = {gist["session_id"] for gist in synthesized}
    raw_score_session_ids = {score["session_id"] for score in raw_scores}

    missing_scores = synthesized_session_ids - raw_score_session_ids
    missing_gists = raw_score_session_ids - synthesized_session_ids

    for session_id in sorted(missing_scores):
        state.setdefault("errors", []).append({
            "session_id": session_id,
            "stage": "merge",
            "message": "missing raw_scores for session_id={session_id}".format(session_id=session_id),
        })

    for session_id in sorted(missing_gists):
        state.setdefault("errors", []).append({
            "session_id": session_id,
            "stage": "merge",
            "message": "missing synthesized_gists for session_id={session_id}".format(session_id=session_id),
        })

    matched_session_ids = synthesized_session_ids & raw_score_session_ids
    merged: list[dict] = []

    for gist in synthesized:
        session_id = gist["session_id"]
        if session_id not in matched_session_ids:
            continue

        score = score_lookup[session_id]
        merged.append(
            {
                "session_id": session_id,
                "user_id": gist["user_id"],
                "gist_text": gist["gist_text"],
                "dominant_emotion_label": gist["dominant_emotion_label"],
                "source_entry_ids": gist["source_entry_ids"],
                "recorded_at": gist["recorded_at"],
                "session_start_candidate": gist["session_start_candidate"],
                "entity_salience_score": score["entity_salience_score"],
                "outcome_score": score["outcome_score"],
            }
        )

    state["scored_gists"] = merged
    return state
