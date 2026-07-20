from langgraph.graph import END, StateGraph

from src.retrieval.nodes.context_packer import context_packer_node
from src.retrieval.nodes.context_validation import context_validation_node
from src.retrieval.nodes.contextual_reinstatement import (
    contextual_reinstatement_node,
)
from src.retrieval.nodes.coreference_resolver import (
    coreference_resolver_node,
)
from src.retrieval.nodes.episodic_retrieval import episodic_retrieval_node
from src.retrieval.nodes.fusion import fusion_node
from src.retrieval.nodes.query_router import query_router_node
from src.retrieval.nodes.semantic_retrieval import semantic_retrieval_node
from src.schemas import RetrievalState
from src.logging.decorators import log_graph, log_node


graph = StateGraph(RetrievalState)

graph.add_node("query_router", log_node(query_router_node, node_name="query_router"))
graph.add_node("coreference_resolver", log_node(coreference_resolver_node, node_name="coreference_resolver"))
graph.add_node("semantic_retrieval", log_node(semantic_retrieval_node, node_name="semantic_retrieval"))
graph.add_node("episodic_retrieval", log_node(episodic_retrieval_node, node_name="episodic_retrieval"))
graph.add_node(
    "contextual_reinstatement",
    log_node(contextual_reinstatement_node, node_name="contextual_reinstatement"),
)
graph.add_node("fusion", log_node(fusion_node, node_name="fusion"))
graph.add_node("context_packer", log_node(context_packer_node, node_name="context_packer"))
graph.add_node("context_validation", log_node(context_validation_node, node_name="context_validation"))

graph.set_entry_point("query_router")

graph.add_conditional_edges(
    "query_router",
    lambda state: (
        "coreference_resolver"
        if state["needs_retrieval"]
        else END
    ),
)

graph.add_edge("coreference_resolver", "semantic_retrieval")
graph.add_edge("coreference_resolver", "episodic_retrieval")

graph.add_edge(
    "episodic_retrieval",
    "contextual_reinstatement",
)

graph.add_edge("semantic_retrieval", "fusion")
graph.add_edge(
    "contextual_reinstatement",
    "fusion",
)

graph.add_edge("fusion", "context_packer")
graph.add_edge("context_packer", "context_validation")
graph.add_edge("context_validation", END)

retrieval_graph = log_graph(graph.compile(), graph_name="Retrieval Graph")