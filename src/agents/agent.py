from typing import Annotated, List
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from src.schemas.retrieval_schemas import SemanticMemories

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    samantic_mem:SemanticMemories


    


