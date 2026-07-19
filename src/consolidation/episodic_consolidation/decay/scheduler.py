import logging
import time

from .decay_sweep import run_decay_sweep
from .tombstone_sweep import run_tombstone_sweep


logger = logging.getLogger(__name__)

DECAY_INTERVAL_HOURS = 6
DECAY_INTERVAL_SECONDS = DECAY_INTERVAL_HOURS * 60 * 60


def run_decay_scheduler() -> None:
    logger.info(
        "Starting decay scheduler (interval=%s hours).",
        DECAY_INTERVAL_HOURS,
    )

    while True:
        logger.info("Starting decay maintenance cycle.")

        try:
            run_decay_sweep()
        except Exception:
            logger.exception("Decay sweep failed in scheduler.")

        try:
            run_tombstone_sweep()
        except Exception:
            logger.exception("Tombstone sweep failed in scheduler.")

        logger.info(
            "Decay maintenance cycle complete. Sleeping for %s hours.",
            DECAY_INTERVAL_HOURS,
        )

        time.sleep(DECAY_INTERVAL_SECONDS)