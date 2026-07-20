from src.schemas import AgentState
from pydantic import BaseModel
import redis
import json


def EpisodicBufferIngest(state:AgentState)->AgentState:
    extractions = state.get("unified_extraction")
    episodic = extractions.episodic_markers
    context = state.get("RequestContext")
    raw_message = state.get("query").content

    redis.xadd(
        "episodic_stream",
        {
            "payload": episodic.model_dump_json(),
            "context": json.dumps(context, default=str),
            "raw_message_text": raw_message,
        }
    )
    return state
