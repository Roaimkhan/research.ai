import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.schemas.agent import AgentState
from langgraph.graph import StateGraph ,END, START
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.store.memory import InMemoryStore
from src.checkpoint import MemoryPostgresSaver
import uuid
import asyncio
from src.prompts import FINAL_ANSWER_PROMPT
from src.config import config
from src.memory import initialize_db
from src.schemas import SemanticMemoryStagerSnapShot, SemanticMemoryStagerState
from src.sub_graphs import SemanticMemoryStager



initialize_db()

async def SemanticMemoryStagerAdapter(state: AgentState) -> AgentState:
    writer_state :SemanticMemoryStagerSnapShot = 
    run_id: uuid.UUID
    user_id: str
    conversation_id: str
    message_id: str
    message_timestamp: datetime
    latest_message: state["messages"][-1]
    
    bufferstate :SemanticMemoryStagerState = {
        "snapshot" : writer_state
    }

    asyncio.create_task(
        SemanticMemoryStager.ainvoke(bufferstate)
    )

    return state



llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=config.GOOGLE_API_KEY
)

graph = StateGraph(AgentState)

graph.add_node("writeSide",writeSide)


