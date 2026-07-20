import json
import redis  # This imports the module
from pydantic import BaseModel
from src.schemas import AgentState

# Initialize a connection instance to your Redis server.
# (Adjust host/port/db/password if your hackathon setup uses non-defaults)
r = redis.Redis(host="localhost", port=6379, decode_responses=True)


def EpisodicBufferIngest(state: AgentState) -> AgentState:
    extractions = state.get("unified_extraction")
    episodic = extractions.episodic_markers
    context = state.get("RequestContext")
    raw_message = state.get("messages")[-1].content

    # Use 'r' (the instance) instead of 'redis' (the module)
    r.xadd(
        "episodic_stream",
        {
            "payload": episodic.model_dump_json(),
            "context": json.dumps(context, default=str),
            "raw_message_text": raw_message,
        },
    )
    return state