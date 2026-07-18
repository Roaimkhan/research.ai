import datetime
import uuid

import pytest
import os
import sys

# Make local `src` package importable when running tests from `unit_tests/`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dataclasses import dataclass

import importlib.util
from pathlib import Path

# Load consolidation modules directly to avoid package-level side-effects from `src` imports
base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
adjudication_path = str(Path(base) / "src" / "consolidation" / "adjudication.py")
bitemporal_path = str(Path(base) / "src" / "consolidation" / "bitemporal_split.py")

import types

# Insert lightweight stubs for external dependencies the modules import at top-level.
messages_mod = types.ModuleType("langchain_core.messages")
class _H:
    def __init__(self, content=None):
        self.content = content
class _S:
    def __init__(self, content=None):
        self.content = content
setattr(messages_mod, "HumanMessage", _H)
setattr(messages_mod, "SystemMessage", _S)
sys.modules["langchain_core.messages"] = messages_mod

lg_mod = types.ModuleType("langchain_google_genai")
class DummyLLM:
    def __init__(self, *a, **k):
        pass
    def with_structured_output(self, *a, **k):
        return self
    def invoke(self, *a, **k):
        return None
setattr(lg_mod, "ChatGoogleGenerativeAI", DummyLLM)
sys.modules["langchain_google_genai"] = lg_mod

cfg_mod = types.ModuleType("src.config")
cfg_mod.config = types.SimpleNamespace(GOOGLE_API_KEY=None, DB_URL="")
sys.modules["src.config"] = cfg_mod

mem_mod = types.ModuleType("src.memory")
mem_mod.conn = None
sys.modules["src.memory"] = mem_mod

# Minimal stub for src.schemas used by adjudication module
schemas_mod = types.ModuleType("src.schemas")
class _AML:
    def __init__(self, memories=None):
        self.memories = memories or []
class _MB:
    def __init__(self, memmories=None):
        self.memmories = memmories or []
class _MR:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    @classmethod
    def parse_obj(cls, d: dict):
        return cls(**d)
    def model_dump(self):
        return {k: getattr(self, k) for k in self.__dict__.keys()}

setattr(schemas_mod, "AdjudicatedMemoryList", _AML)
setattr(schemas_mod, "MemoryBatch", _MB)
setattr(schemas_mod, "MemoryRecord", _MR)
setattr(schemas_mod, "SemanticBufferConsolidatorState", dict)
sys.modules["src.schemas"] = schemas_mod

# Stub src.consolidation.utils to avoid importing heavy external embedding libs
cons_utils = types.ModuleType("src.consolidation.utils")
def _embed_text(t):
    return [0.0] * 1536
setattr(cons_utils, "embed_text", _embed_text)
sys.modules["src.consolidation.utils"] = cons_utils
cons_pkg = types.ModuleType("src.consolidation")
setattr(cons_pkg, "utils", cons_utils)
sys.modules["src.consolidation"] = cons_pkg

spec = importlib.util.spec_from_file_location("adjudication", adjudication_path)
adjudication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adjudication)

spec2 = importlib.util.spec_from_file_location("bitemporal_split", bitemporal_path)
bitemporal_split = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(bitemporal_split)


@dataclass
class MemoryRecord:
    fact_id: object
    subject: str
    predicate: str
    object: str
    temporal_start_expression: object
    temporal_end_expression: object
    is_ongoing: bool
    valid_start: object
    valid_end: object
    confidence_score: float
    provenance_uri: str


class AdjudicatedMemoryItem:
    def __init__(self, memory, action, target_fact_ids=None, adjudication_reason=None):
        self.memory = memory
        self.action = action
        self.target_fact_ids = target_fact_ids or []
        self.adjudication_reason = adjudication_reason


class AdjudicatedMemoryList:
    def __init__(self, memories=None):
        self.memories = memories or []


class MemoryBatch:
    def __init__(self, memmories=None):
        self.memmories = memmories or []


class DummyCursor:
    def __init__(self, rows=None, desc=None, fetchone=None):
        self._rows = rows or []
        self.description = desc
        self._fetchone = fetchone

    def execute(self, *args, **kwargs):
        return None

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._fetchone

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def commit(self):
        return None

    def cursor(self):
        return self._cursor


def make_memory(subject="User", predicate="likes", object_="Pizza"):
    return MemoryRecord(
        fact_id=uuid.uuid4(),
        subject=subject,
        predicate=predicate,
        object=object_,
        temporal_start_expression=None,
        temporal_end_expression=None,
        is_ongoing=False,
        valid_start=datetime.datetime.utcnow(),
        valid_end=None,
        confidence_score=0.9,
        provenance_uri="test://unit",
    )


def test_ajudication_gate_returns_fresh_when_no_similar(monkeypatch):
    # staging query returns one row, active_beliefs returns empty
    colnames = ["fact_id", "subject", "predicate", "object", "valid_start", "valid_end", "provenance_uri", "confidence_score"]
    row = (str(uuid.uuid4()), "User", "likes", "Pizza", datetime.datetime.utcnow(), None, "test://unit", 0.9)

    class StagingCursor(DummyCursor):
        def __init__(self, rows=None, desc=None):
            super().__init__(rows=rows, desc=desc)
            self._served_staging = False

        def execute(self, query, params=None):
            q = str(query).upper()
            if "FROM STAGING_BUFFER" in q:
                # keep initial rows for staging select
                self._served_staging = True
            elif "FROM ACTIVE_BELIEFS" in q:
                # subsequent active_beliefs select -> no similar rows
                self._rows = []

    staging_cursor = StagingCursor(rows=[row], desc=[(c,) for c in colnames])

    class TwoStageConn:
        def __init__(self):
            self._calls = 0

        def cursor(self):
            self._calls += 1
            if self._calls == 1:
                return staging_cursor
            return DummyCursor(rows=[], desc=[("fact_id", "object")])

    monkeypatch.setattr(adjudication, "conn", TwoStageConn())
    monkeypatch.setattr(adjudication, "structured_llm", type("S", (), {"invoke": staticmethod(lambda *a, **k: AdjudicatedMemoryList())})())

    state = {"snapshot": type("S", (), {"user_id": str(uuid.uuid4())})()}
    out = adjudication.ajudication_gate(state)

    assert hasattr(out["fresh_memories"], "memmories")
    assert len(out["fresh_memories"].memmories) == 1
    assert out["adjudicated_memories"].memories == []


def test_bitemporal_split_applies_add_and_replace(monkeypatch):
    actions = {"inserts": [], "retracts": []}

    class RecordingCursor(DummyCursor):
        def execute(self, query, params=None):
            q = query.strip().upper()
            if q.startswith("INSERT INTO ACTIVE_BELIEFS"):
                actions["inserts"].append(params)
            if q.startswith("UPDATE ACTIVE_BELIEFS"):
                actions["retracts"].append(params)
                # Simulate RETURNING row for the UPDATE so fetchone() returns a value
                self._fetchone = (params.get("fact_id"), "User", "pred", "obj", datetime.datetime.utcnow())

    monkeypatch.setattr(bitemporal_split, "conn", DummyConn(RecordingCursor()))
    monkeypatch.setattr(bitemporal_split, "embed_text", lambda t: [0.0])

    user_id = str(uuid.uuid4())

    add_item = AdjudicatedMemoryItem(memory=make_memory(object_="A"), action="ADD", target_fact_ids=[], adjudication_reason="")
    replace_item = AdjudicatedMemoryItem(memory=make_memory(object_="B"), action="REPLACE", target_fact_ids=[str(uuid.uuid4())], adjudication_reason="repl")

    state = {"snapshot": type("S", (), {"user_id": user_id})(), "adjudicated_memories": AdjudicatedMemoryList(memories=[add_item, replace_item])}

    out = bitemporal_split.bitemporal_split(state)

    assert len(actions["inserts"]) == 2
    assert len(actions["retracts"]) == 1
