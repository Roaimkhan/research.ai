from langchain_core.messages import HumanMessage
from src.schemas.agent import AgentState
from src.schemas import RetrievalState


from langchain_core.messages import HumanMessage

from src.schemas import (
    AgentState,
    RetrievalState,
)
from src.retrieval import retrieval_graph


def retrieval_adapter(state: AgentState) -> AgentState:
    context = state["requestcontext"]

    retrieval_state: RetrievalState = {
        "user_id": context.user_id,
        # Conversation history excluding the current user message
        "messages":state["messages"][:-1],

        "query_text": state["messages"][-1].content,
    }
    

    result = retrieval_graph.invoke(retrieval_state)
    return {
        "retrieved_context":result.get("validated_context", [])
    }


