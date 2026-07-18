from typing_extensions import TypedDict
from .semanticmemorystagersnap_schemas import SemanticMemoryStagerSnapShot
from .extraction_schemas import ExtractionResult, MemoryBatch

class SemanticMemoryStagerState(TypedDict):
    snapshot: SemanticMemoryStagerSnapShot
    extraction_result: ExtractionResult
    memory_batch: MemoryBatch
