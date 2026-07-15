# placeholder
import uuid
from typing import List
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.store.memory import BaseStore  
from src.prompts.extraction_prompts import SEMANTIC_MEMORY_EXTRACTION_PROMPT
from src.schemas.extraction_schemas import MemoryDecision
from src.config import config

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=config.GOOGLE_API_KEY)

def ExtractSemantic(state,store:BaseStore,config:RunnableConfig):
    print("====ExtractSemantic Called==== ")
    """
        This function takes the user input to the agent: query, a store (to store the extracted facts),
        and a 'RunnableConfig' (to store in the right place) for extracting and storing facts from the user data.
        It handles deduplication!
    """
    query = state["messages"][-1]
    nm = config["configurable"]["namespace"]
    existining_memories = store.search(nm)
    memories_text = [it.value.get("memory","") for it in existining_memories if it.value.get("memory")]

    structured_llm = llm.with_structured_output(MemoryDecision)
## Latest User Message

    response : MemoryDecision = structured_llm.invoke(
        [SystemMessage(content=SEMANTIC_MEMORY_EXTRACTION_PROMPT.format(user_details_content=memories_text,user_message=query.content)),
         HumanMessage(content=f"Latest User Message :{query.content}" )]
        )
    
    if response.should_write:
        for mem in response.memmories:
            print(f"DEBUG: Memory to write: {mem.text} (is_new={mem.is_new})")
            if mem.is_new:
                store.put(nm,str(uuid.uuid4()),{"memory":mem.text})
    else:
        print("DEBUG: LLM decided should_write=False")



