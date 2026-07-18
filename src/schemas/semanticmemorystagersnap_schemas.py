import uuid
from datetime import datetime
from dataclasses import dataclass 
from langchain_core.messages import BaseMessage

@dataclass(frozen=True)
class SemanticMemoryStagerSnapShot:
    run_id: uuid.UUID
    user_id: str
    conversation_id: str
    message_id: str
    message_timestamp: datetime
    latest_message: list[BaseMessage]
    