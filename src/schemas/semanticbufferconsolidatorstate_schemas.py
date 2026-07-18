from typing_extensions import TypedDict
from .semanticmemorystagersnap_schemas import SemanticMemoryStagerSnapShot
from .extraction_schemas import MemoryBatch
from .adjudication_schemas import AdjudicatedMemoryList


class SemanticBufferStage(TypedDict):
    snapshot: SemanticMemoryStagerSnapShot
    semantic_memories_processed: MemoryBatch


class SemanticBufferConsolidatorState(TypedDict):
    snapshot: SemanticMemoryStagerSnapShot
    semantic_memories_processed: MemoryBatch
    fresh_memories:MemoryBatch
    adjudicated_memories: AdjudicatedMemoryList
