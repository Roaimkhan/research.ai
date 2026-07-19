from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class RequestContext(BaseModel):
    user_id: UUID
    thread_id: UUID
    session_id: UUID
    timestamp: datetime
