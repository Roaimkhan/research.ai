from typing import Annotated, List
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from src.schemas import MemoryItemEx
from src.schemas import WriterPipelineSnapshot
from src.schemas import AdjudicatedMemoryList

class WriterAgentState(TypedDict):
    snapshot:WriterPipelineSnapshot
    adjudicated_memories :AdjudicatedMemoryList
    semantic_memories_processed:list[MemoryItemEx]
    
    
