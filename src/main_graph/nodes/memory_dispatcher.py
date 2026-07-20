from threading import Thread
from src.schemas import AgentState

from src.main_graph.sub_graphs.episodicbuffer_Ingest import EpisodicBufferIngest
from src.main_graph.sub_graphs.semantic_adapter import semantic_adapter
from src.main_graph import semantic_memory_stager_graph  




import threading

import threading
import traceback

def _spawn(graph, state, *args, **kwargs):
    # Determine the execution target
    if hasattr(graph, "invoke") and callable(graph.invoke):
        target_func = graph.invoke
    else:
        target_func = graph

    # This wrapper function forces background errors to print to your terminal
    def safe_execute():
        try:
            print("🚀 [THREAD] Background thread is successfully starting...")
            target_func(state, *args, **kwargs)
            print("✅ [THREAD] Background thread finished without throwing exceptions.")
        except Exception as e:
            print("❌ [THREAD CRASH] The background thread exploded!")
            traceback.print_exc()

    thread = threading.Thread(target=safe_execute)
    thread.daemon = True
    thread.start()

def memory_dispatcher_node(state: AgentState) -> AgentState:
    print("====memory_dispatcher_node Called====")
    extraction = state["unified_extraction"]

    if extraction.semantic:
        semantic_state = semantic_adapter(state)

        _spawn(
            semantic_memory_stager_graph,
            semantic_state,
        )

    if extraction.episodic_markers:

        _spawn(
            EpisodicBufferIngest,
            state,
        )

    return {}