from src.schemas import ExtractionResult,EpisodicMarkers
from pydantic import BaseModel

class UnifiedExtraction(BaseModel):
    semantic: ExtractionResult | None   
    episodic_markers: EpisodicMarkers | None 