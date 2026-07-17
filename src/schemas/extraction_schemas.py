from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from uuid import UUID
import uuid
from datetime import datetime
from enum import Enum

class TemporalPrecision(str, Enum):
    INSTANT = "instant"   # "right now", "just started"
    DAY = "day"           # "yesterday", "on July 3rd"
    MONTH = "month"       # "last month", "in June"
    YEAR = "year"         # "in 2021"
    UNKNOWN = "unknown"   # no temporal signal at all


class ExtractedMemory(BaseModel):
    subject: str = Field(
        description="The primary entity the memory is about (e.g., User, Paper_A, Drug_X)."
    )
    predicate: str = Field(
        description="The relationship or attribute connecting subject to object (e.g., likes_pet, authored_by, works_at)."
    )
    object: str = Field(
        description="The value, entity, or concept associated with the subject through the predicate. Single atomic fact."
    )
     temporal_start_expression: Optional[str] = Field(
        default=None,
        description="Verbatim phrase indicating when the fact STARTED being true. Null if none."
    )
    temporal_end_expression: Optional[str] = Field(
        default=None,
        description="Verbatim phrase indicating when the fact ENDED, if stated in this same "
                    "utterance (e.g. 'until 2022', 'through last year'). Null if not mentioned."
    )
    is_ongoing: bool = Field(
        default=False,
        description="True if text explicitly signals the fact is still continuing "
                    "(e.g. 'still', 'to this day')."
    )
    
class ExtractionResult(BaseModel):
    should_write:bool = Field(
        description = "True if memmories found, False if no memmories found"
    )
    
    memmories: List[ExtractedMemory] = Field(
        default_factory=list, description = "Atomic user memories listed"
    )

class MemoryRecord(ExtractedMemory):
    fact_id: UUID = Field(default_factory=uuid.uuid4)
    valid_start: datetime
    valid_end: datetime | Literal["ongoing"] | None = None


class MemoryBatch(BaseModel):
    
    memmories: List[MemoryRecord] = Field(
        default_factory=list, description = "Atomic user memories listed"
    )