import importlib.util
import json
import os
import sys
import types
from types import SimpleNamespace

import pytest

# Ensure local repo root is importable and stub out missing modules used by the target file.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

src_mod = types.ModuleType("src")
sys.modules["src"] = src_mod
schemas_mod = types.ModuleType("src.schemas")
schemas_mod.AgentState = dict
sys.modules["src.schemas"] = schemas_mod

pydantic_mod = types.ModuleType("pydantic")
class BaseModel:
    pass
setattr(pydantic_mod, "BaseModel", BaseModel)
sys.modules["pydantic"] = pydantic_mod

redis_mod = types.ModuleType("redis")
setattr(redis_mod, "xadd", lambda *args, **kwargs: None)
sys.modules["redis"] = redis_mod

MODULE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "sub_graphs", "episodic_cache_stage.py"))

spec = importlib.util.spec_from_file_location("episodic_cache_stage", MODULE_PATH)
episodic_cache_stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(episodic_cache_stage)


def test_episodic_buffer_ingest_serializes_request_context_as_json(monkeypatch):
    captured = {}

    def fake_xadd(stream, payload):
        captured["stream"] = stream
        captured["payload"] = payload
        return "1-0"

    monkeypatch.setattr(episodic_cache_stage.redis, "xadd", fake_xadd)

    state = {
        "unified_extraction": SimpleNamespace(
            episodic_markers=SimpleNamespace(model_dump_json=lambda: '{"foo": "bar"}')
        ),
        "RequestContext": {
            "user_id": "11111111-1111-1111-1111-111111111111",
            "thread_id": "22222222-2222-2222-2222-222222222222",
            "session_id": "33333333-3333-3333-3333-333333333333",
            "timestamp": "2026-07-19T00:00:00Z",
        },
        "query": SimpleNamespace(content="test message"),
    }

    result_state = episodic_cache_stage.EpisodicBufferIngest(state)

    assert result_state is state
    assert captured["stream"] == "episodic_stream"
    assert captured["payload"]["payload"] == '{"foo": "bar"}'
    assert captured["payload"]["raw_message_text"] == "test message"

    context_json = captured["payload"]["context"]
    loaded = json.loads(context_json)
    assert loaded["user_id"] == state["RequestContext"]["user_id"]
    assert loaded["thread_id"] == state["RequestContext"]["thread_id"]
    assert loaded["session_id"] == state["RequestContext"]["session_id"]
    assert loaded["timestamp"] == state["RequestContext"]["timestamp"]
