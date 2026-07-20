import logging
import time
from uuid import uuid4

from src.logging import ensure_run_context, bind_run_context, record_memory_event, get_logger
from .decay_sweep import run_decay_sweep
from .tombstone_sweep import run_tombstone_sweep


logger = get_logger(__name__)

DECAY_INTERVAL_HOURS = 6
DECAY_INTERVAL_SECONDS = DECAY_INTERVAL_HOURS * 60 * 60


def run_decay_scheduler() -> None:
    logger.info(
        "Starting decay scheduler (interval=%s hours).",
        DECAY_INTERVAL_HOURS,
    )

    while True:
        scheduler_run_id = str(uuid4())
        logger.info("Starting decay maintenance cycle.", extra={"run_id": scheduler_run_id})

        with bind_run_context(run_id=scheduler_run_id):
            try:
                run_decay_sweep()
            except Exception:
                logger.exception("Decay sweep failed in scheduler.")
                record_memory_event(scheduler_errors=1)

            try:
                run_tombstone_sweep()
            except Exception:
                logger.exception("Tombstone sweep failed in scheduler.")
                record_memory_event(scheduler_errors=1)

        logger.info(
            "Decay maintenance cycle complete. Sleeping for %s hours.",
            DECAY_INTERVAL_HOURS,
        )

        time.sleep(DECAY_INTERVAL_SECONDS)