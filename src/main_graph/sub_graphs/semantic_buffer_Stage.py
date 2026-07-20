from langgraph.graph import StateGraph, END, START
from src.schemas import SemanticMemoryStagerState
from src.extraction import temporal_expression_resolver
from src.main_graph.sub_graphs.semantic_buffer_writer import semantic_buffer_writer


def router_after_semantic_ex(state: SemanticMemoryStagerState) -> str:
    extraction_result = state.get("extraction_result")
    if extraction_result and hasattr(extraction_result, 'temporal_expressions') and extraction_result.temporal_expressions:
        return "TER"
    return "__end__"


graph = StateGraph(SemanticMemoryStagerState)

graph.add_node("TER", temporal_expression_resolver)
graph.add_node("semantic_buffer_writer", semantic_buffer_writer)

graph.add_conditional_edges(
    START,
    router_after_semantic_ex,
    {
        "TER": "TER",
        "__end__": END,
    }
)
graph.add_edge("TER", "semantic_buffer_writer")
graph.add_edge("semantic_buffer_writer", END)

SemanticMemoryStager = graph.compile()
