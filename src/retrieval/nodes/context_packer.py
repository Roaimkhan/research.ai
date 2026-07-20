from __future__ import annotations

from src.retrieval.config import CONTEXT_TOKEN_BUDGET
from src.retrieval.token_utils import approximate_token_count
from src.schemas import RetrievalState
from src.logging import get_logger

logger = get_logger(__name__)

def context_packer_node(state: RetrievalState) -> RetrievalState:
    validated_context = state.get("validated_context", [])
    input_count = len(validated_context)

    packed_items: list[dict] = []
    total_tokens = 0

    for item in validated_context:
        item_tokens = approximate_token_count([item])
        if total_tokens + item_tokens > CONTEXT_TOKEN_BUDGET:
            break
        packed_items.append(item)
        total_tokens += item_tokens

    state["packed_context"] = packed_items
    state["packed_token_count"] = total_tokens
    
    try:
        logger.info(
            "Context packing: %d validated → %d packed (%d tokens)",
            input_count,
            len(packed_items),
            total_tokens,
            extra={"validated": input_count, "packed": len(packed_items), "tokens": total_tokens}
        )
    except Exception:
        pass
    return state