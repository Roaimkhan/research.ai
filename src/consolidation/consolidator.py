# placeholder
from langgraph.graph import StateGraph ,END, START
from src.schemas import SemanticBufferConsolidator
from src.writeside import ajudication_gate, bitemporal_split, semantic_buffer_writer



writer_graph = StateGraph(SemanticBufferConsolidator)

writer_graph.add_node("AG",ajudication_gate)
writer_graph.add_node("BS",bitemporal_split)
writer_graph.add_node("SBW",semantic_buffer_writer)

writer_graph.add_edge(START,"AG")
writer_graph.add_edge("AG","BS")
writer_graph.add_edge("BS","SBW")
writer_graph.add_edge("SBW",END)

SemanticBufferConsilidator = writer_graph.compile()

from IPython.display import Image, display
display(Image(app.writer_graph().draw_mermaid_png()))



