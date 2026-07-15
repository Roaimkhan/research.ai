import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.agent import AgentState
from langgraph.graph import StateGraph ,END, START
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.store.memory import InMemoryStore
from src.checkpoint import MemoryPostgresSaver
import uuid
from src.extraction import ExtractSemantic
from src.prompts import FINAL_ANSWER_PROMPT
from src.config import config

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=config.GOOGLE_API_KEY
)
def ask(state:AgentState)->AgentState:
    result =llm.invoke(FINAL_ANSWER_PROMPT.format(semantic_memory=state["samantic_mem"], working_memory=state["messages"]))
    print(f"AI: {result.content}")
    return {
        "messages":[result]
    }

graph = StateGraph(AgentState)
graph.add_node("extract_semantic",ExtractSemantic)
# graph.add_node("ask",ask)
graph.add_edge(START,"extract_semantic")
# graph.add_edge("extract_semantic","ask")
graph.add_edge("extract_semantic",END)


DB_URI = config.DB_URI

with MemoryPostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()
    store = InMemoryStore()
    agent = graph.compile(
        checkpointer=checkpointer,
        store = store
    )
    
    thread_id = str(uuid.uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id,
            "namespace":"mmaa"
        }
    }

    user_input = input("Enter: ")
    while True:
        if user_input == "exit":
            break

        result = agent.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config
        )
        user_input = input("Enter: ")    

results = list(store.search(config["configurable"]["namespace"]))
print(f"Found {len(results)} memories")
for item in results:
    print(item)