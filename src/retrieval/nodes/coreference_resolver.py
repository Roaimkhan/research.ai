from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, Field

from src.clients.qwen_client import qwen_client
from src.schemas import RetrievalState


class ResolvedQuery(BaseModel):
    resolved_query_text: str = Field(
        description=(
            "The user's query with ambiguous references "
            "resolved into explicit entities whenever possible. "
            "If nothing is ambiguous, return the original "
            "query unchanged."
        )
    )


def _message_role(message: Any) -> str:
    if isinstance(message, Mapping):
        return str(message.get("role", "user"))
    role = getattr(message, "type", None) or getattr(message, "role", None)
    return str(role or "user")


def _message_content(message: Any) -> str:
    if isinstance(message, Mapping):
        content = message.get("content", "")
    else:
        content = getattr(message, "content", "")
    return str(content).strip()


def _format_recent_history(messages: list[Any], limit: int = 8) -> str:
    lines: list[str] = []
    for message in messages[-limit:]:
        content = _message_content(message)
        if not content:
            continue
        lines.append(f"{_message_role(message)}: {content}")
    return "\n".join(lines)


def coreference_resolver_node(state: RetrievalState) -> RetrievalState:
    if not state.get("needs_retrieval", False):
        return state

    query_text = state.get("query_text", "")
    if not query_text:
        state["resolved_query_text"] = query_text
        return state

    messages = state.get("messages", [])
    history_text = _format_recent_history(messages) if isinstance(messages, list) else ""

    if not history_text:
        state["resolved_query_text"] = query_text
        return state

    system_prompt = (
        "Resolve ambiguous references in the user's latest query using only the provided "
        "conversation history. Resolve references like it/that/this/those/the project/the paper/"
        "that formula/the algorithm/the previous one only when unambiguous. If not confident, "
        "preserve the original wording exactly. Do not add facts."
    )

    llm_messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Conversation history:\n{history_text}\n\n"
                f"Latest user query:\n{query_text}\n\n"
                "Return only the resolved query text."
            ),
        },
    ]

    structured = qwen_client.with_structured_output(ResolvedQuery)
    try:
        resolved = structured.invoke(llm_messages)
    except Exception:
        resolved = None

    if isinstance(resolved, ResolvedQuery) and resolved.resolved_query_text:
        state["resolved_query_text"] = resolved.resolved_query_text
    elif isinstance(resolved, dict) and resolved.get("resolved_query_text"):
        state["resolved_query_text"] = str(resolved["resolved_query_text"])
    else:
        state["resolved_query_text"] = query_text

    return state
