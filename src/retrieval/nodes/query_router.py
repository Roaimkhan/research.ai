from __future__ import annotations

import re
from src.schemas import RetrievalState




_SIMPLE_INPUTS = {
    "hi",
    "hello",
    "hey",
    "ok",
    "okay",
    "thanks",
    "thank you",
    "yes",
    "no",
    "cool",
    "nice",
}

_RETRIEVAL_CUES = (
    "what did i tell you",
    "remember",
    "last time",
    "earlier",
    "previous",
    "the project",
    "my preference",
    "continue",
    "recall",
    "what was",
    "which",
    "remember",
    "recall",
    "continue",
    "earlier",
    "previous",
    "last time",
    "what did i tell you",
    "what did we discuss",
    "what was",
    "my preference",
    "my preferences",
    "the project",
    "our conversation",
    "before",
)


def query_router_node(state: RetrievalState) -> RetrievalState:
    
    query_text = state.get("query_text")
    if not query_text:
        state["needs_retrieval"] = False
        return state
    
    normalized = re.sub(r"\s+", " ", query_text.lower()).strip()
    word_count = len(normalized.split()) if normalized else 0

    needs_retrieval = False
    
    has_retrieval_cue = any(
        cue in normalized
        for cue in _RETRIEVAL_CUES
    )
    if normalized:
        if normalized in _SIMPLE_INPUTS:
            needs_retrieval = False
        elif has_retrieval_cue:
            needs_retrieval = True
        elif word_count < 3:
            needs_retrieval = False
        else:
            needs_retrieval = False

    state["needs_retrieval"] = needs_retrieval
    return state
