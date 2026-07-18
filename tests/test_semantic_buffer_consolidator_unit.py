import datetime
import uuid

import pytest

from src.schemas import MemoryRecord, AdjudicatedMemoryItem, AdjudicatedMemoryList, SemanticBufferConsolidatorState, MemoryBatch
from src.consolidation import adjudication, bitemporal_split


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

    # cursor for staging: returns the single row, description matches colnames
    staging_cursor = DummyCursor(rows=[row], desc=[(c,) for c in colnames])
    # After checking active_beliefs, similar_rows empty -> second cursor used returns []
    # We'll implement cursor() to return staging_cursor first, then a cursor with empty rows

    class TwoStageConn:
        def __init__(self):
            self._calls = 0

        def cursor(self):
            self._calls += 1
            if self._calls == 1:
                return staging_cursor
            return DummyCursor(rows=[], desc=[("fact_id", "object")])

    monkeypatch.setattr(adjudication, "conn", TwoStageConn())

    # structured_llm should never be invoked in this path, but ensure it's well-behaved
    monkeypatch.setattr(adjudication, "structured_llm", lambda *args, **kwargs: AdjudicatedMemoryList())

    state = {"snapshot": type("S", (), {"user_id": str(uuid.uuid4())})()}
    out = adjudication.ajudication_gate(state)

    assert isinstance(out["fresh_memories"], MemoryBatch)
    assert len(out["fresh_memories"].memmories) == 1
    assert out["adjudicated_memories"].memories == []


def test_bitemporal_split_applies_add_and_replace(monkeypatch):
    # Prepare a fake conn that records inserts and retractions
    actions = {"inserts": [], "retracts": []}

    class RecordingCursor(DummyCursor):
        def execute(self, query, params=None):
            q = query.strip().upper()
            if q.startswith("INSERT INTO ACTIVE_BELIEFS"):
                actions["inserts"].append(params)
            if q.startswith("UPDATE ACTIVE_BELIEFS"):
                actions["retracts"].append(params)

    monkeypatch.setattr(bitemporal_split, "conn", DummyConn(RecordingCursor()))
    monkeypatch.setattr(bitemporal_split, "embed_text", lambda t: [0.0])

    user_id = str(uuid.uuid4())

    # ADD action
    add_item = AdjudicatedMemoryItem(memory=make_memory(object_="A"), action="ADD", target_fact_ids=[], adjudication_reason="")

    # REPLACE action: includes one target_fact_id
    replace_item = AdjudicatedMemoryItem(memory=make_memory(object_="B"), action="REPLACE", target_fact_ids=[str(uuid.uuid4())], adjudication_reason="repl")

    state = {"snapshot": type("S", (), {"user_id": user_id})(), "adjudicated_memories": AdjudicatedMemoryList(memories=[add_item, replace_item])}

    out = bitemporal_split.bitemporal_split(state)

    # ensure inserts recorded for both ADD and REPLACE
    assert len(actions["inserts"]) == 2
    # ensure retract recorded once for REPLACE
    assert len(actions["retracts"]) == 1
