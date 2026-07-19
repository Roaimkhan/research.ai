import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.schemas.agent import AgentState
from langgraph.graph import StateGraph ,END, START
from langchain_core.messages import HumanMessage, BaseMessage
from src.checkpoint import MemoryPostgresSaver
import uuid
import asyncio
from src.config import config
from src.memory import initialize_db
from src.schemas import SemanticMemoryStagerSnapShot, SemanticMemoryStagerState
from src.sub_graphs import SemanticMemoryStager
from src.extraction import UnifiedExtractor


initialize_db()



graph = StateGraph(AgentState)

graph = StateGraph(AgentState)

graph.add_node("unifiedextractor",UnifiedExtractor)


