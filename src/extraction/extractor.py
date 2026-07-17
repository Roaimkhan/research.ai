from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.prompts.extraction_prompts import SYSTEM_EXTRACTION_PROMPT
from psycopg2.errors import UndefinedTable
from src.schemas import ExtractionResult ,MemoryBatch
from src.schemas import AgentState 
from src.config import config
from typing import Literal
import uuid
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


def temporal_expression(state:AgentState):
    memorieslist = state.get("samantic_memories_raw",[])
    
    if memorieslist:
        for memory in memorieslist.memories:






def RouterAfterSemanticEx(state:AgentState)->Literal["__end__","adjudication_gate"]:
    memories = state.get("samantic_memories_raw")

    if memories and memories.should_write:
        return "adjudication_gate"
    return "__end__"






