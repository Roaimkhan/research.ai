from typing import TypeVar, Generic
from datetime import datetime
from pydantic import BaseModel

T = TypeVar("T")

class ExtractionResult(BaseModel, Generic[T]):
    payload: T
    confidence: float
    needs_review: bool
    review_reason: str | None
    extractor_name: str
    extracted_at: datetime

def wrap_extraction(payload: T, confidence: float, extractor_name: str,
                     review_threshold: float = 0.6) -> "ExtractionResult[T]":
    """
    needs_review is auto-computed as (confidence < review_threshold) —
    do not require callers to compute this manually. review_threshold
    is a parameter, not a global constant, since different extractors
    need different bars.
    """
    return ExtractionResult(
        payload=payload,
        confidence=confidence,
        needs_review=confidence < review_threshold,
        review_reason=(f"confidence {confidence} below threshold {review_threshold}"
                        if confidence < review_threshold else None),
        extractor_name=extractor_name,
        extracted_at=datetime.utcnow(),
    )
