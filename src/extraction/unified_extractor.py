from typing import Sequence, Mapping

from src.clients.qwen_client import qwen_client
from src.schemas import AgentState, UnifiedExtraction
from src.memory import pool
from src.prompts import UNIFIED_EXTRACTION_PROMPT


def UnifiedExtractor(state:AgentState) -> AgentState:
    # User's DB query to fetch existing subjects/predicates
    user_id = state.get("context").user_id
    query = state.get("messages")[-1]
    with pool.connection() as conn:
        with conn.cursor() as cursor: 
            cursor.execute("""
                    SELECT DISTINCT subject, predicate FROM active_beliefs
                           WHERE user_id =%s
                """,(user_id))
            result = cursor.fetchall()
    subjects = list({i[0] for i in result})
    predicates = list({i[1] for i in result})
    messages: list[Mapping[str, str]] = [
        {"role": "system", "content": UNIFIED_EXTRACTION_PROMPT.format(subjects=subjects, predicates=predicates)},
        {"role": "user", "content": f"Latest User Message: {query.content}"},
    ]

    structured = qwen_client.with_structured_output(UnifiedExtraction)
    try:
        response = structured.invoke(messages)
    except Exception:
        response = None

    return {"unified_extraction": response}


def router_Ep(state:AgentState) -> AgentState:
    exe = state["unified_extraction"]
    if exe.get("episodic_markers"):
        return "continue"
    else:
        return "__end__"

def router_Se(state:AgentState) -> AgentState:
    exe = state["unified_extraction"]
    if exe.get("semantic"):
        return "continue"
    else:
        return "__end__"
