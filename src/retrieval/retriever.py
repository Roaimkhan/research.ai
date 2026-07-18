# placeholder
from langchain_core.runnables import RunnableConfig
from langgraph.store.memory import BaseStore  
from langchain_google_genai import ChatGoogleGenerativeAI
from src.schemas.retrieval_schemas import MemoriesRe
from src.prompts.retrieval_prompts import SEMANTIC_MEMORY_RETRIEVAL_PROMPT
from src.sub_graphs.agent import AgentState
from src.config import config

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=config.GOOGLE_API_KEY)

def RetrieveSemantic(state:AgentState, store:BaseStore,config:RunnableConfig) -> AgentState:
    msg = state["messages"][-1]
    mem = store.search(config["configurable"]["namespace"])
    structured_llm = llm.with_structured_output(MemoriesRe)
    retireved_memmry:MemoriesRe = structured_llm.invoke(SEMANTIC_MEMORY_RETRIEVAL_PROMPT.format(stored_memories=mem,user_message=msg))
    if MemoriesRe.found_relevant:
        state["samantic_mem"] = retireved_memmry.memmories
    else:
        state["samantic_mem"] = []
    
    return state

    