from src.retrieval.graph import retrieval_graph
from src.retrieval.memory_events import ensure_consumer_group

def initialize_memory_streams():
    """Initialize all Redis consumer groups at application startup."""
    ensure_consumer_group("tool_execution_stream", "atsc_consolidation_workers")
    ensure_consumer_group("document_ingest_stream", "hcl_crossref_workers")
    ensure_consumer_group("document_ingest_stream", "smds_matrix_workers")