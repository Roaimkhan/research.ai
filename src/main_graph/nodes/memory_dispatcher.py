from threading import Thread
from src.schemas import AgentState
from src.logging import spawn_background_task, get_logger

from src.main_graph.sub_graphs.episodicbuffer_Ingest import EpisodicBufferIngest
from src.main_graph.sub_graphs.semantic_adapter import semantic_adapter
from src.main_graph import semantic_memory_stager_graph


logger = get_logger(__name__)


def memory_dispatcher_node(state: AgentState) -> AgentState:

    extraction = state["unified_extraction"]

    if extraction.semantic:
        semantic_state = semantic_adapter(state)

        spawn_background_task(
            semantic_memory_stager_graph.invoke,
            semantic_state,
            name="semantic-memory-stager",
        )

    if extraction.episodic_markers:
        episodic_state = EpisodicBufferIngest(state)
        spawn_background_task(
            episodic_buffer_graph.invoke,
            episodic_state,
            name="episodic-buffer-ingest",
        )

    return {}