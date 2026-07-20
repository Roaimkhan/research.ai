from langgraph.graph import END, StateGraph

from src.atsc.nodes.ack_batch import ack_batch_node
from src.atsc.nodes.dedup_check import dedup_check_node
from src.atsc.nodes.read_batch import read_batch_node
from src.atsc.nodes.skill_file_writer import skill_file_writer_node
from src.atsc.nodes.skill_synthesis import skill_synthesis_node
from src.atsc.nodes.skill_validation import skill_validation_node
from src.atsc.nodes.success_filter import success_filter_node
from src.atsc.state import ProceduralConsolidationState


graph = StateGraph(ProceduralConsolidationState)

graph.add_node("read_batch", read_batch_node)
graph.add_node("success_filter", success_filter_node)
graph.add_node("skill_synthesis", skill_synthesis_node)
graph.add_node("skill_validation", skill_validation_node)
graph.add_node("dedup_check", dedup_check_node)
graph.add_node("skill_file_writer", skill_file_writer_node)
graph.add_node("ack_batch", ack_batch_node)

graph.set_entry_point("read_batch")

graph.add_edge("read_batch", "success_filter")
graph.add_edge("success_filter", "skill_synthesis")
graph.add_edge("skill_synthesis", "skill_validation")
graph.add_edge("skill_validation", "dedup_check")
graph.add_edge("dedup_check", "skill_file_writer")
graph.add_edge("skill_file_writer", "ack_batch")
graph.add_edge("ack_batch", END)
