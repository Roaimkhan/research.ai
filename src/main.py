from src.agent import AgentState
from langgraph.graph import StateGraph ,END, START
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.checkpoint.session_state import MemoryPostgresSaver
import uuid



llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key = ""
)

def ask(state:AgentState)->AgentState:
    result =llm.invoke(state["messages"])
    print(f"AI: {result.content}")
    return {
        "messages":[result]
    }

graph = StateGraph(AgentState)
graph.add_node("ask",ask)
graph.add_edge(START,"ask")
graph.add_edge("ask",END)


DB_URI = (
    "postgresql://postgres:roaim123@localhost:5432/research_agent"
)

with MemoryPostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()
    agent = graph.compile(
        checkpointer=checkpointer
    )
    
    thread_id = str(uuid.uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id
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
