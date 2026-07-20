from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class RequestContext(BaseModel):
    run_id: UUID | None = None
    user_id: UUID
    thread_id: UUID
    session_id: UUID
    conversation_id: UUID
    message_id: UUID
    message_timestamp: datetime
    timestamp: datetime
    workspace_id: UUID | None

