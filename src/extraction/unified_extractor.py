from src.clients.qwen_client import qwen_client
from src.schemas import AgentState, UnifiedExtraction
from src.persistence import raw_pool
from src.prompts import UNIFIED_EXTRACTION_PROMPT

structured = qwen_client.with_structured_output(UnifiedExtraction)

def UnifiedExtractor(state:AgentState) -> AgentState:
    context = state.get("requestcontext")
    if context is None:
        raise ValueError("AgentState missing requestcontext.")

    user_id = context.user_id

    messages = state.get("messages", [])
    if not messages:
        raise ValueError("AgentState missing messages.")

    latest_message = messages[-1]

    with raw_pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT subject, predicate
                FROM active_beliefs
                WHERE user_id = %s
                """,
                (user_id,),
            )
            rows = cursor.fetchall()

    subjects = sorted({row[0] for row in rows if row[0]})
    predicates = sorted({row[1] for row in rows if row[1]})

    llm_messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": UNIFIED_EXTRACTION_PROMPT.format(
                subjects=subjects,
                predicates=predicates,
            ),
        },
        {
            "role": "user",
            "content": f"Latest User Message:\n{latest_message.content}",
        },
    ]


    try:
        response = structured.invoke(llm_messages)
    except Exception:
        response = None
    print(response)
    return {
        "unified_extraction": response,
    }

from langgraph.constants import Send
from langgraph.graph import END

def extraction_router(state: AgentState):
    extraction = state.get("unified_extraction")

    if extraction is None:
        return END

    sends = []

    if getattr(extraction, "semantic", None):
        sends.append(Send("semantic_stager", state))

    if getattr(extraction, "episodic_markers", None):
        sends.append(Send("episodic_stager", state))

    if not sends:
        return END

    return sends