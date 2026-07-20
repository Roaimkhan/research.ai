from __future__ import annotations

from pathlib import Path

from src.schemas.agent import AgentState

embed_text = None
retrieve_matching_skills = None


def _resolve_embed_text():
    global embed_text
    if embed_text is None:
        from src.utils import embed_text as imported_embed_text

        embed_text = imported_embed_text
    return embed_text


def _resolve_retrieve_matching_skills():
    global retrieve_matching_skills
    if retrieve_matching_skills is None:
        from src.memory.procedural_store import retrieve_matching_skills as imported_retrieve_matching_skills

        retrieve_matching_skills = imported_retrieve_matching_skills
    return retrieve_matching_skills


def procedural_retrieval_node(state: AgentState) -> AgentState:
    """Retrieve relevant procedural skills for the current user request before planning."""
    try:
        requestcontext = state.get("requestcontext")
        if requestcontext is None or not hasattr(requestcontext, "user_id"):
            return state

        user_id = getattr(requestcontext, "user_id")
        messages = state.get("messages", [])
        if not messages:
            return state

        request_text = ""
        for message in messages:
            content = getattr(message, "content", None)
            if content:
                if isinstance(content, str):
                    request_text = content
                    break
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            request_text = str(item.get("text", ""))
                            break
                    if request_text:
                        break

        if not request_text:
            return state

        task_embedding = _resolve_embed_text()(request_text)
        matching_skills = _resolve_retrieve_matching_skills()(user_id, task_embedding, top_k=3)
        if not matching_skills:
            return state

        markdown_skills: list[str] = []
        for skill in matching_skills:
            file_path = skill.get("file_path")
            if not file_path:
                continue
            try:
                markdown_skills.append(Path(file_path).read_text(encoding="utf-8"))
            except Exception:
                continue

        if markdown_skills:
            state.setdefault("retrieved_procedural_skills", []).extend(markdown_skills)
        return state
    except Exception:
        return state
