from uuid import uuid4

from src.schemas import (
    AgentState,
    SemanticMemoryStagerSnapShot,
    SemanticMemoryStagerState,
)
from src.main_graph import semantic_memory_stager_graph


def semantic_adapter(state: AgentState) -> AgentState:
    context = state["requestcontext"]

    snapshot = SemanticMemoryStagerSnapShot(
        run_id=uuid4(),
        user_id=context.user_id,
        conversation_id=context.conversation_id,
        message_id=context.message_id,
        message_timestamp=context.message_timestamp,
        latest_message=[state["messages"][-1]],
    )

    semantic_state: SemanticMemoryStagerState = {
        "snapshot": snapshot,
        "extraction_result": state["unified_extraction"].semantic,
    }

    semantic_memory_stager_graph.invoke(semantic_state)

    return state