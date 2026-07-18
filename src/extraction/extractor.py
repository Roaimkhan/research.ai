from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Literal
from src.prompts.extraction_prompts import SYSTEM_EXTRACTION_PROMPT
from src.schemas import SemanticMemoryStagerState, ExtractionResult
from src.config import config
from src.memory import pool

# Initialize LLM once at module level
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=config.GOOGLE_API_KEY)
structured_llm = llm.with_structured_output(ExtractionResult)

def extract_semantic(state: SemanticMemoryStagerState) -> dict:
    print("====ExtractSemantic Called====")
    
    # User's DB query to fetch existing subjects/predicates
    with pool.connection() as conn:
        with conn.cursor() as cursor: 
            cursor.execute("""
                    SELECT DISTINCT subject, predicate FROM active_beliefs
                """)
            result = cursor.fetchall()
              
    subjects = list({i[0] for i in result})
    predicates = list({i[1] for i in result})

    snapshot = state.get("snapshot")
    if not snapshot:
        raise ValueError("SemanticMemoryStagerState missing required 'snapshot' field.")
        
    query = snapshot.latest_message[-1]
    
    response: ExtractionResult = structured_llm.invoke([
        SystemMessage(content=SYSTEM_EXTRACTION_PROMPT.format(subjects=subjects, predicates=predicates)),
        HumanMessage(content=f"Latest User Message: {query.content}")
    ])

    return {"extraction_result": response}


def router_after_semantic_ex(state: SemanticMemoryStagerState) -> Literal["__end__", "TER"]:
    memories = state.get("extraction_result")

    if memories and memories.should_write:
        return "TER"
    return "__end__"
