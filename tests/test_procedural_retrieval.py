from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from types import SimpleNamespace

from src.atsc.nodes.procedural_retrieval import procedural_retrieval_node
from src.schemas.agent import AgentState


def test_procedural_retrieval_node_collects_matching_skills(monkeypatch):
    captured = {}

    def fake_embed_text(text: str):
        captured["text"] = text
        return [0.1, 0.2, 0.3]

    def fake_retrieve_matching_skills(user_id, task_embedding, top_k=3):
        captured["user_id"] = user_id
        captured["top_k"] = top_k
        return [
            {"skill_name": "format_email", "file_path": skill_path},
        ]

    monkeypatch.setattr("src.atsc.nodes.procedural_retrieval.embed_text", fake_embed_text)
    monkeypatch.setattr("src.atsc.nodes.procedural_retrieval.retrieve_matching_skills", fake_retrieve_matching_skills)

    with NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("# skill\n")
        skill_path = handle.name

    try:
        state: AgentState = {
            "requestcontext": SimpleNamespace(user_id="user-123"),
            "messages": [SimpleNamespace(content="draft a concise response")],
        }

        updated_state = procedural_retrieval_node(state)

        assert captured["text"] == "draft a concise response"
        assert captured["user_id"] == "user-123"
        assert captured["top_k"] == 3
        assert updated_state["retrieved_procedural_skills"] == ["# skill\n"]
    finally:
        Path(skill_path).unlink(missing_ok=True)
