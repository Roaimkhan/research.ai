from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime
from dateparser import parse
from typing import Literal
from src.prompts.extraction_prompts import SYSTEM_EXTRACTION_PROMPT
from src.schemas import AgentState, ExtractionResult, MemoryBatch, MemoryRecord
from src.config import config
from src.memory import conn

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=config.GOOGLE_API_KEY)

def ExtractSemantic(state:AgentState) -> ExtractionResult:
    print("====ExtractSemantic Called==== ")
    cursor = conn.cursor()

    cursor.execute("""
            SELECT DISTINCT subject,predicate FROM active_beliefs
        """)

    result = cursor.fetchall()

    subjects = list({i[0] for i in result})
    predicates = list({i[1] for i in result})

    query = state["messages"][-1]
    structured_llm = llm.with_structured_output(ExtractionResult)
    response : ExtractionResult= structured_llm.invoke(
        [SystemMessage(content=SYSTEM_EXTRACTION_PROMPT.format(subjects=subjects,predicates=predicates)),
         HumanMessage(content=f"Latest User Message :{query.content}")])

    return {"samantic_memories_raw" : response }



def temporal_expression(
    state: AgentState,
    message_timestamp: datetime,
) -> AgentState:
    extraction_result = state.get("samantic_memories_raw")

    if (
        extraction_result is None
        or not extraction_result.should_write
        or not extraction_result.memmories
    ):
        state["samantic_memories_processed"] = MemoryBatch()
        return state

    memory_batch = MemoryBatch()

    for memory in extraction_result.memmories:

        valid_start = _resolve_valid_start(memory, message_timestamp)

        if memory.temporal_expression:
            valid_start = parse(
                memory.temporal_expression,
                settings={
                    "RELATIVE_BASE": message_timestamp
                },
            )

        memory_record = MemoryRecord(
            **memory.model_dump(),
            valid_start=valid_start,
            valid_end=None,
        )

        memory_batch.memmories.append(memory_record)

    state["samantic_memories_processed"] = memory_batch
    return state



def RouterAfterSemanticEx(state:AgentState)->Literal["__end__","adjudication_gate"]:
    memories = state.get("samantic_memories_raw")

    if memories and memories.should_write:
        return "adjudication_gate"
    return "__end__"






