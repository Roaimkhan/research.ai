from typing_extensions import TypedDict
from src.schemas import MemoryBatch, AdjudicatedMemoryList


class SemanticBufferConsolidatorState(TypedDict):
    semantic_memories_unconsolodated:MemoryBatch
    adjudicated_memories :AdjudicatedMemoryList
