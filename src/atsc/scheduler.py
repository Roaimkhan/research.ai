import logging
import time
from uuid import uuid4

from src.logging import ensure_run_context, bind_run_context, record_memory_event, get_logger
from src.retrieval.memory_events import ensure_consumer_group
from src.atsc.graph import graph as procedural_consolidation_graph


logger = get_logger(__name__)

ATSC_CONSOLIDATION_INTERVAL_SECONDS = 300


def run_atsc_scheduler() -> None:
    ensure_consumer_group(
        "tool_execution_stream",
        "atsc_consolidation_workers",
    )
    logger.info(
        "Starting ATSC consolidation scheduler (interval=%s seconds).",
        ATSC_CONSOLIDATION_INTERVAL_SECONDS,
    )

    while True:
        scheduler_run_id = str(uuid4())
        logger.info("Starting ATSC consolidation cycle.", extra={"run_id": scheduler_run_id})

        with bind_run_context(run_id=scheduler_run_id):
            try:
                procedural_consolidation_graph.invoke({})
            except Exception:
                logger.exception("ATSC consolidation cycle failed in scheduler.")
                record_memory_event(scheduler_errors=1)

        logger.info(
            "ATSC consolidation cycle complete. Sleeping for %s seconds.",
            ATSC_CONSOLIDATION_INTERVAL_SECONDS,
        )

        time.sleep(ATSC_CONSOLIDATION_INTERVAL_SECONDS)
