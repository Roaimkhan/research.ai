from pydantic import BaseModel, Field
from typing import List

class MemoryItemEx(BaseModel):
    text:str = Field(description = "Atomic user memory")
    is_new: bool = Field(description = "True is new, False if old")

class MemoryDecision(BaseModel):
    should_write: bool = Field(description = "Wheteher to store any memories or not")
    memmories: List[MemoryItemEx] = Field(default_factory=list, description = "Atomic user memories to store")
