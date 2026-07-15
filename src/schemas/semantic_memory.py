from typing import TypedDict

class SemanticMemoryUnit(TypedDict):
    concept:str
    fact_value:str
    confidence:int
    source_type:str
    session_id:str
    embedding: list[float]