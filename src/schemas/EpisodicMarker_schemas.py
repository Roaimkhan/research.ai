from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EmotionalValence(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class EmotionalIntensity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class EpisodicMarkers(BaseModel):
    emotional_valence: EmotionalValence = Field(
        description="Overall emotional tone of the user's message."
    )
    emotional_intensity: EmotionalIntensity = Field(
        description="Strength of the emotional signal, not just its direction."
    )
    emotional_labels: list[str] = Field(
        default_factory=list,
        description="Short labels for detected emotions, e.g. ['frustration', 'relief']. "
                    "Empty list if neutral/no clear emotion present."
    )
    is_significant_event: bool = Field(
        description="True if this message describes something notable enough to be worth "
                    "recalling later — a decision, a setback, a breakthrough, a stated "
                    "preference shift, a strong reaction. False for routine/transactional turns "
                    "(e.g. 'ok', 'thanks', simple factual questions)."
    )
    temporal_expression: Optional[str] = Field(
        default=None,
        description="Verbatim phrase indicating when this event occurred, if stated "
                    "(e.g. 'earlier today', 'just now'). Null if no explicit signal — "
                    "downstream code falls back to message_timestamp, same as semantic pipeline."
    )