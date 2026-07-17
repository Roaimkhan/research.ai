import uuid
from pydantic import dataclass 
from src.schemas import Memmorieslisted
@dataclass(frozen=True)
class WriterPipelineSnapshot:
    run_id: uuid
    user_id: str
    thread_id: str
    raw_semantic_memories:Memmorieslisted