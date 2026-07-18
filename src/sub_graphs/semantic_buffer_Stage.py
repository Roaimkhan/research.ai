from langgraph.graph import StateGraph, END, START
from src.schemas import SemanticMemoryStagerState
from src.extraction import extract_semantic, temporal_expression_resolver, router_after_semantic_ex
from src.writeside import semantic_buffer_writer

graph = StateGraph(SemanticMemoryStagerState)

graph.add_node("Extractor", extract_semantic)
graph.add_node("TER", temporal_expression_resolver)
graph.add_node("semantic_buffer_writer", semantic_buffer_writer)

graph.add_edge(START, "Extractor")
graph.add_conditional_edges(
    "Extractor",
    router_after_semantic_ex,
    {
        "TER": "TER",
        "__end__": END,
    }
)
graph.add_edge("TER", "semantic_buffer_writer")
graph.add_edge("semantic_buffer_writer", END)

SemanticMemoryStager = graph.compile()
