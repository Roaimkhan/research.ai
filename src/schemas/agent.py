from typing import Annotated, List
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from src.schemas import UnifiedExtraction ,RequestContext

class AgentState(TypedDict):
    RequestContext:RequestContext
    unified_extraction:UnifiedExtraction
    messages: Annotated[List[BaseMessage], add_messages]
