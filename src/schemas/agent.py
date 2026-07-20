from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from .unifiedextractionschemas import UnifiedExtraction 
from .requestcontext_schema import RequestContext

class AgentState(TypedDict, total=False):
    requestcontext: RequestContext
    messages: Annotated[list[BaseMessage], add_messages]
    unified_extraction: UnifiedExtraction
    retrieved_context: list[dict]
    retrieved_procedural_skills: list[str]