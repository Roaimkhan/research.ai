from pydantic import BaseModel, Field
from src.extraction import ExtractSemantic
from typing import List

class MemoryItemRe(BaseModel):
    text:str = Field(description = "Atomic user memory")

class SemanticMemories(BaseModel):
        memmories: List[MemoryItemRe] = Field(default_factory=list, description = "Atomic user memories to store for providing to llm as context")

class MemoriesRe(BaseModel):
    found_relevant:bool = Field(default_factory=list, description = "True if relelvant memories found, False if not")
    memmories: SemanticMemories
