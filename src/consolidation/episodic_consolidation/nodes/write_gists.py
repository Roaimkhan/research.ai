from episodic_consolidation.state import ConsolidationState

from src.persistence import episodic_store
from src.persistence.semantic_store import conn


def write_gist_node(state: ConsolidationState) -> ConsolidationState:
    embedded = state.get("embedded_gists", [])
    if not embedded:
        return state

    state.setdefault("written_gist_ids", [])
    state.setdefault("errors", [])

    for gist in embedded:
        session_id = gist.get("session_id")
        try:
            # Each gist must be its own transaction; use psycopg3 transaction context
            with conn.transaction():
                with conn.cursor() as cursor:
                    # Ensure session exists (insert if missing)
                    episodic_store.ensure_session_upsert(cursor, gist)

                    # Increment interaction count by number of source entries
                    source_ids = gist.get("source_entry_ids", [])
                    episodic_store.increment_interaction_count(cursor, session_id, len(source_ids))

                    # Insert the gist row and get generated gist_id
                    gist_id = episodic_store.insert_gist(cursor, gist)
                    # If compute_composite_importance attached a new centroid, persist it here
                    new_centroid = gist.get("new_centroid_embedding")
                    new_count = gist.get("new_centroid_count")
                    if new_centroid is not None and new_count is not None:
                        episodic_store.upsert_user_centroid(cursor, gist["user_id"], new_centroid, new_count)

            # If we reach here the transaction committed successfully
            state.setdefault("written_gist_ids", []).append(gist_id)
            state.setdefault("successful_session_ids", []).append(str(gist["session_id"]))

        except Exception as e:
            # Transaction for this gist rolled back automatically; record error and continue
            state.setdefault("errors", []).append({
                "session_id": session_id,
                "stage": "write_gist",
                "message": str(e),
            })

    return state
