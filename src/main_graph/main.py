from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from uuid import uuid4

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from src.checkpoint.checkpointer import get_postgres_checkpointer
from src.extraction import UnifiedExtractor
from src.logging import configure_logging, get_logger
from src.main_graph.nodes.main_llm import main_llm_node
from src.main_graph.nodes.memory_dispatcher import memory_dispatcher_node
from src.main_graph.nodes.retreival_adapter import retrieval_adapter
from src.logging.decorators import log_graph, log_node
from src.persistence import initialize_db
from src.schemas.agent import AgentState
from src.schemas.requestcontext_schema import RequestContext

logger = get_logger(__name__)

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("unifiedextractor", log_node(UnifiedExtractor, node_name="unifiedextractor"))
    graph.add_node("memory_dispatcher", log_node(memory_dispatcher_node, node_name="memory_dispatcher"))
    graph.add_node("retrieval", log_node(retrieval_adapter, node_name="retrieval"))
    graph.add_node("main_llm", log_node(main_llm_node, node_name="main_llm"))
    graph.add_edge(START, "unifiedextractor")
    graph.add_edge("unifiedextractor", "memory_dispatcher")
    graph.add_edge("memory_dispatcher", "retrieval")
    graph.add_edge("retrieval", "main_llm")
    graph.add_edge("main_llm", END)
    checkpointer = get_postgres_checkpointer()
    return log_graph(graph.compile(checkpointer = checkpointer), graph_name="Main Graph")

roaim = "aaa44f24-d3f7-4f95-846d-5187dfe0366d"
ahmed = "99abb5a7-ac89-40a5-bae1-4b071d71cbd9"
def run_request(message: str, *, request_context: RequestContext | None = None) -> dict:
    configure_logging()
    initialize_db()
    compiled_graph = build_graph()
    context = request_context or RequestContext(
        run_id=uuid4(),
        user_id=roaim,
        thread_id=uuid4(),
        session_id=uuid4(),
        conversation_id=uuid4(),
        message_id=uuid4(),
        message_timestamp=datetime.now(timezone.utc),
        timestamp=datetime.now(timezone.utc),
    )
    config = {"configurable": {"thread_id": "session_2"}}
    state = {
        "requestcontext": context,
        "messages": [HumanMessage(content=message)],
    }
    logger.info("Dispatching main request", extra={"run_id": str(context.run_id) if context.run_id else None})
    return compiled_graph.invoke(state,config=config)


def main() -> None:
    query = input("AI : hi there how can i help you?")
    while query != "exit":
        run_request(query)
        query = input("Enter : ")


if __name__ == "__main__":
    main()