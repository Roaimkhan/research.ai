from episodic_consolidation.state import ConsolidationState

from src.memory import episodic_store
from src.memory.semantic_store import conn


def stag_edge_node(state: ConsolidationState) -> ConsolidationState:
    written = state.get("written_gist_ids", [])

    if not written:
        return state

    state.setdefault("errors", [])

    for gist_id in written:
        try:
            with conn.transaction():
                with conn.cursor() as cursor:

                    meta = episodic_store.get_gist_metadata(
                        cursor,
                        gist_id
                    )

                    if meta is None:
                        raise ValueError(
                            f"gist_id not found: {gist_id}"
                        )

                    user_id, recorded_at = meta

                    previous_gist_id = episodic_store.get_previous_gist_id(
                        cursor,
                        user_id,
                        recorded_at
                    )

                    if previous_gist_id is None:
                        continue

                    episodic_store.insert_stag_edge(
                        cursor,
                        previous_gist_id,
                        gist_id
                    )

        except Exception as exc:
            state.setdefault("errors", []).append({
                "session_id": "unknown",
                "stage": "stag_edges",
                "message": str(exc),
            })

    return state