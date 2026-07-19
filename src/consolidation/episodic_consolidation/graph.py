from langgraph.graph import StateGraph, END

from episodic_consolidation.nodes.read_batch import read_batch_node
from episodic_consolidation.nodes.gist_synthesis import episodic_gist_synthesis_node
from episodic_consolidation.nodes.raw_signal_scoring import raw_signal_scoring_node
from episodic_consolidation.nodes.merge_gist_and_scores import merge_gist_and_scores_node
from episodic_consolidation.nodes.embed import embed_gist_node
from episodic_consolidation.nodes.compute_composite_importance import compute_composite_importance_node
from src.consolidation.episodic_consolidation.nodes.write_gists import write_gist_node
from episodic_consolidation.nodes.stag_edges import stag_edge_node
from episodic_consolidation.nodes.ack_batch import ack_batch_node
from src.consolidation.episodic_consolidation.state import ConsolidationState


graph = StateGraph(ConsolidationState)

graph.add_node("read_batch", read_batch_node)
graph.add_node("gist_synthesis", episodic_gist_synthesis_node)
graph.add_node("raw_signal_scoring", raw_signal_scoring_node)
graph.add_node("merge_gist_and_scores", merge_gist_and_scores_node)
graph.add_node("embed", embed_gist_node)
graph.add_node("compute_composite_importance", compute_composite_importance_node)
graph.add_node("write_gist", write_gist_node)
graph.add_node("stag_edges", stag_edge_node)
graph.add_node("ack_batch", ack_batch_node)

graph.set_entry_point("read_batch")

# Fan-out
graph.add_edge("read_batch", "gist_synthesis")
graph.add_edge("read_batch", "raw_signal_scoring")

# Fan-in
graph.add_edge("gist_synthesis", "merge_gist_and_scores")
graph.add_edge("raw_signal_scoring", "merge_gist_and_scores")

# Sequential pipeline
graph.add_edge("merge_gist_and_scores", "embed")
graph.add_edge("embed", "compute_composite_importance")
graph.add_edge("compute_composite_importance", "write_gist")
graph.add_edge("write_gist", "stag_edges")
graph.add_edge("stag_edges", "ack_batch")

# Terminal
graph.add_edge("ack_batch", END)

compiled_graph = graph.compile()