from .extraction_schemas import ExtractionResult
from .EpisodicMarker_schemas import EpisodicMarkers
from pydantic import BaseModel

class UnifiedExtraction(BaseModel):
    semantic: ExtractionResult | None   
    episodic_markers: EpisodicMarkers | None 