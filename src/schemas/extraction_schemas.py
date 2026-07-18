from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
import uuid
from datetime import datetime


class ExtractedMemory(BaseModel):
    fact_id: UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for this extracted fact."
    )
    subject: str = Field(
        description="The primary entity the memory is about (e.g., User, Paper_A, Drug_X)."
    )
    predicate: str = Field(
        description="The relationship or attribute connecting subject to object "
                    "(e.g., likes_pet, authored_by, works_at)."
    )
    object: str = Field(
        description="The value or entity associated with the subject via the predicate. "
                    "Single atomic fact."
    )
    temporal_start_expression: Optional[str] = Field(
        default=None,
        description="Verbatim phrase indicating when the fact STARTED being true. "
                    "Null if none present in the text."
    )
    temporal_end_expression: Optional[str] = Field(
        default=None,
        description="Verbatim phrase indicating when the fact ENDED, if stated "
                    "(e.g. 'until 2022', 'through last year'). Null if not mentioned."
    )
    is_ongoing: bool = Field(
        default=False,
        description="True ONLY if the text explicitly signals the fact is still continuing "
                    "(e.g. 'still', 'to this day', 'currently')."
    )


class ExtractionResult(BaseModel):
    should_write: bool = Field(
        description="True if stable memories were found; False if the message contains "
                    "nothing worth storing."
    )
    memmories: List[ExtractedMemory] = Field(
        default_factory=list,
        description="Atomic user memories extracted from the message."
    )


class MemoryRecord(ExtractedMemory):
    """
    ExtractedMemory enriched with resolved temporal bounds, provenance, and
    confidence. Produced by the Temporal Expression Resolver node.
    fact_id is inherited from ExtractedMemory (same UUID, same fact).
    """
    valid_start: datetime = Field(
        description="Resolved datetime for when this fact became true."
    )
    valid_end: Optional[datetime] = Field(
        default=None,
        description="Resolved datetime for when this fact stopped being true. "
                    "None = open-ended (ongoing or unknown)."
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="0.95 when temporal signal was explicit; "
                    "0.6 when valid_start was inferred from message timestamp."
    )
    provenance_uri: str = Field(
        description="URI identifying the source message for this fact."
    )


class MemoryBatch(BaseModel):
    """Wrapper retained for the consolidator pipeline's state contract."""
    memmories: List[MemoryRecord] = Field(
        default_factory=list,
        description="Batch of resolved memory records."
    )