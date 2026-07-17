from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
import uuid

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
    temporal_expression: Optional[str] = Field(
        default=None,
        description="The EXACT phrase from the user's text indicating when this fact became/becomes true. "
                    "e.g. 'last month', 'in 2021', 'since college', 'yesterday'. "
                    "Null if no temporal signal exists in the text."
    )
    temporal_precision: TemporalPrecision = Field(
        default=TemporalPrecision.UNKNOWN,
        description="Granularity of the temporal_expression. UNKNOWN if temporal_expression is null."
    )
    is_terminating: bool = Field(
        default=False,
        description="True if this statement means a PRIOR fact stopped being true "
                    "(e.g., 'I quit Google', 'I no longer like cats', 'I moved out of NY')."
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
    valid_start:
    valid_end:


class MemoryBatch(BaseModel):
    
    memmories: List[MemoryRecord] = Field(
        default_factory=list, description = "Atomic user memories listed"
    )