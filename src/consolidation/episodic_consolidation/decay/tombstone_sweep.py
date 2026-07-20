from src.logging import get_logger, record_memory_event

from src.persistence.semantic_store import pool


logger = get_logger(__name__)


def run_tombstone_sweep() -> None:
    try:
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
UPDATE episodic_gists
SET gist_text = NULL,
    gist_embedding = NULL,
    erasure_tombstone = TRUE
WHERE erasure_tombstone = FALSE
  AND EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_accessed_at)) / 3600.0
      >= time_to_live_hours;
""")
                tombstoned_count = cursor.rowcount

        record_memory_event(tombstones=tombstoned_count)
        logger.info(
            "Tombstone sweep completed.\n"
            f"Tombstoned: {tombstoned_count}"
        )
    except Exception:
        logger.exception("Tombstone sweep failed.")
        record_memory_event(scheduler_errors=1)