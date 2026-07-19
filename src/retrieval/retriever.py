# placeholder
from langchain_core.runnables import RunnableConfig
from langgraph.store.memory import BaseStore
from typing import Mapping, Sequence
from src.clients.qwen_client import qwen_client
from src.schemas.retrieval_schemas import MemoriesRe
from src.prompts.retrieval_prompts import SEMANTIC_MEMORY_RETRIEVAL_PROMPT
from src.sub_graphs.agent import AgentState


def RetrieveSemantic(state:AgentState, store:BaseStore,config:RunnableConfig) -> AgentState:
    msg = state["messages"][-1]
    mem = store.search(config["configurable"]["namespace"]) if store is not None else []
    prompt = SEMANTIC_MEMORY_RETRIEVAL_PROMPT.format(stored_memories=mem, user_message=msg)

    messages: list[Mapping[str, str]] = [{"role": "system", "content": prompt}]

    structured = qwen_client.with_structured_output(MemoriesRe)
    try:
        retireved_memmry = structured.invoke(messages)
    except Exception:
        retireved_memmry = None

    if retireved_memmry and getattr(retireved_memmry, "found_relevant", False):
        state["samantic_mem"] = getattr(retireved_memmry, "memmories", [])
    else:
        state["samantic_mem"] = []

    return state

    