# placeholder
import uuid
from typings import list, str
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_google_genai import ChatGoogleGenerativeAI()
from langgraph.store import InMemoryStore import 
from prompts import MEMORY_PROMPT
from client import qwen_client

class MemoryItem(BaseModel):
    text:str = Field(description = "Atomic user memory")
    is_new: bool = Field(description = "True is new, False if old")

class MemoryDecision(BaseModel):
    should_write: bool
    memmories: List[MemoryItem] = Field(default_factory=list)

def ExtractSemantic(query:str):
    ##Memmory STRORE 

    store = InMemoryStore()

    store

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = llm.structured_output(MemoryDecision)

    response = llm.invoke(MEMORY_PROMPT.format(user_details_content=user_details_content, user_message=query))
    print(response)



ExtractSemantic("my name is roaim")



