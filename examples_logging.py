#!/usr/bin/env python
"""
Example: Using the Production Logging System

This script demonstrates the complete logging, tracing, and observability system
integrated into the LangGraph-based AI agent.
"""

from datetime import datetime, timezone
from uuid import uuid4

from src.logging import configure_logging, get_logger, bind_run_context, record_memory_event
from src.persistence import initialize_db
from src.schemas.requestcontext_schema import RequestContext
from src.main_graph.main import run_request


def main():
    """Run a complete request with full observability."""
    
    # 1. Configure logging once at startup
    configure_logging()
    logger = get_logger(__name__)
    
    logger.info("Application startup")
    
    # 2. Initialize database
    initialize_db()
    
    # 3. Create a request context with run_id
    request_context = RequestContext(
        run_id=uuid4(),
        user_id=uuid4(),
        thread_id=uuid4(),
        session_id=uuid4(),
        conversation_id=uuid4(),
        message_id=uuid4(),
        message_timestamp=datetime.now(timezone.utc),
        timestamp=datetime.now(timezone.utc),
    )
    
    logger.info(
        "Starting request processing",
        extra={
            "run_id": str(request_context.run_id),
            "user_id": str(request_context.user_id),
        }
    )
    
    # 4. Run the request
    # This will automatically:
    # - Use the run_id from request_context
    # - Log all graph/node lifecycle events
    # - Log all database queries
    # - Log all LLM calls
    # - Log all embedding operations
    # - Print execution summary at the end
    try:
        result = run_request(
            "What's your understanding of AI memory systems?",
            request_context=request_context
        )
        logger.info("Request completed successfully")
        
        # 5. Access results
        messages = result.get("messages", [])
        if messages:
            logger.info(f"Got {len(messages)} messages in state")
        
    except Exception as e:
        logger.exception("Request failed")
        raise


def example_with_background_context():
    """Example showing context inheritance in background tasks."""
    from src.logging import spawn_background_task
    
    configure_logging()
    logger = get_logger(__name__)
    
    def background_worker(data):
        """A background worker that inherits the parent's run_id."""
        worker_logger = get_logger("background_worker")
        worker_logger.info("Background task started", extra={"data": data})
        # This log will have the same run_id as the parent
    
    with bind_run_context(run_id="my-run-id-123", graph_name="MainGraph"):
        logger.info("Main thread running")
        
        # Spawn background task - inherits run_id
        spawn_background_task(
            background_worker,
            "important_data",
            name="my-background-task"
        )
        
        logger.info("Background task spawned")


def example_recording_events():
    """Example showing how to record domain-level events."""
    from src.logging import record_memory_event, record_retrieval_event
    
    configure_logging()
    logger = get_logger(__name__)
    
    # Record semantic memory pipeline events
    record_memory_event(
        semantic_inserted=4,
        semantic_updated=2,
        semantic_ignored=1,
        semantic_merged=0,
        semantic_superseded=0,
    )
    
    # Record episodic memory pipeline events
    record_memory_event(
        episodic_inserted=2,
        episodic_reactivated=5,
        episodic_updated=7,
        stag_edges=3,
    )
    
    # Record retrieval metrics
    record_retrieval_event(
        duration_ms=157,
        semantic_candidates=27,
        episodic_candidates=12,
        semantic_top_k=5,
        episodic_top_k=3,
        packed_context_size=8,
        validated_context_size=7,
    )
    
    logger.info("All events recorded - check execution summary at end of run")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "background":
        example_with_background_context()
    elif len(sys.argv) > 1 and sys.argv[1] == "events":
        example_recording_events()
    else:
        main()
