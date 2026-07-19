import logging

from src.memory.semantic_store import conn


logger = logging.getLogger(__name__)


def run_decay_sweep() -> None:
    try:
        with conn.transaction():
            with conn.cursor() as cursor:
                cursor.execute("""
UPDATE episodic_gists
SET importance_score_current =
    importance_score_initial * EXP(
        -0.001 * EXTRACT(EPOCH FROM (
            CURRENT_TIMESTAMP - last_accessed_at
        )) / 3600.0
    )
WHERE is_active = TRUE;
""")
                updated_count = cursor.rowcount

                cursor.execute("""
UPDATE episodic_gists
SET is_active = FALSE
WHERE is_active = TRUE
  AND importance_score_current < 0.20;
""")
                deactivated_count = cursor.rowcount

        logger.info(
            "Decay sweep completed.\n"
            f"Updated scores: {updated_count}\n"
            f"Soft-deleted: {deactivated_count}"
        )
    except Exception:
        logger.exception("Decay sweep failed.")
