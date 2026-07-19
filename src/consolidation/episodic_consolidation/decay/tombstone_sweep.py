import logging

from src.memory.semantic_store import conn


logger = logging.getLogger(__name__)


def run_tombstone_sweep() -> None:
    try:
        with conn.transaction():
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

        logger.info(
            "Tombstone sweep completed.\n"
            f"Tombstoned: {tombstoned_count}"
        )
    except Exception:
        logger.exception("Tombstone sweep failed.")