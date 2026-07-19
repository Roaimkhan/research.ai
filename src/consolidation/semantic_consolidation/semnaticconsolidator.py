from langgraph.graph import StateGraph, END, START
from src.schemas import SemanticBufferConsolidatorState
from src.consolidation.semantic_consolidation.adjudication import ajudication_gate
from src.consolidation.semantic_consolidation.bitemporal_split import bitemporal_split, consolidate_fresh_memories

writer_graph = StateGraph(SemanticBufferConsolidatorState)

writer_graph.add_node("AG", ajudication_gate)
writer_graph.add_node("FM", consolidate_fresh_memories)
writer_graph.add_node("BS", bitemporal_split)

writer_graph.add_edge(START, "AG")
writer_graph.add_edge("AG", "FM")
writer_graph.add_edge("FM", "BS")
writer_graph.add_edge("BS", END)

SemanticBufferConsolidator = writer_graph.compile()




