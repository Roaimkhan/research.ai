from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.main_graph.main import run_request
from src.schemas.requestcontext_schema import RequestContext

app = FastAPI(title="Global AI Hackathon Demo API")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: UUID
    workspace_id: UUID | None = None
    conversation_id: UUID | None = None


class ChatResponse(BaseModel):
    response: dict


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    now = datetime.now(timezone.utc)
    conversation_id = request.conversation_id or uuid4()
    request_context = RequestContext(
        run_id=uuid4(),
        user_id=request.user_id,
        thread_id=conversation_id,
        session_id=uuid4(),
        conversation_id=conversation_id,
        message_id=uuid4(),
        message_timestamp=now,
        timestamp=now,
        workspace_id=request.workspace_id,
    )

    result = run_request(request.message, request_context=request_context)
    return ChatResponse(response=result)
