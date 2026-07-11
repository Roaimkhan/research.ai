"""
test_checkpointer.py
--------------------
Tests for MemoryPostgresSaver.list_thread_ids() and .iter_thread_ids().

Run with:
    pytest test_checkpointer.py -v

Requirements:
    - A reachable PostgreSQL instance (set DB_URI below or via the
      CHECKPOINT_DB_URI environment variable).
    - `langgraph[checkpoint-postgres]` and `psycopg[binary]` installed.
"""

from __future__ import annotations

import os
import uuid
from typing import Generator

import pytest
from langchain_core.messages import HumanMessage

from src.checkpoint.session_state import MemoryPostgresSaver

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_URI = os.getenv(
    "CHECKPOINT_DB_URI",
    "postgresql://postgres:roaim123@localhost:5432/research_agent",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def saver() -> Generator[MemoryPostgresSaver, None, None]:
    """
    Yields a fresh MemoryPostgresSaver with an empty checkpoints table
    for each test, then tears it down afterwards.
    """
    with MemoryPostgresSaver.from_conn_string(DB_URI) as cp:
        cp.setup()
        # Wipe any pre-existing rows so each test starts clean
        with cp.conn.cursor() as cur:
            cur.execute("DELETE FROM checkpoint_blobs;")
            cur.execute("DELETE FROM checkpoint_writes;")
            cur.execute("DELETE FROM checkpoints;")
        cp.conn.commit()
        yield cp


def _write_checkpoint(saver: MemoryPostgresSaver, thread_id: str) -> None:
    """Helper: store a minimal checkpoint for *thread_id*."""
    from langgraph.checkpoint.base import empty_checkpoint

    config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
    checkpoint = empty_checkpoint()
    metadata: dict = {}
    new_versions: dict = {}
    saver.put(config, checkpoint, metadata, new_versions)


# ---------------------------------------------------------------------------
# Tests – list_thread_ids
# ---------------------------------------------------------------------------


class TestListThreadIds:
    def test_empty_store(self, saver: MemoryPostgresSaver) -> None:
        """Returns [] when no checkpoints exist."""
        assert saver.list_thread_ids() == []

    def test_single_thread(self, saver: MemoryPostgresSaver) -> None:
        """Returns the one thread id when only one thread is stored."""
        tid = str(uuid.uuid4())
        _write_checkpoint(saver, tid)

        result = saver.list_thread_ids()
        assert result == [tid]

    def test_multiple_distinct_threads(self, saver: MemoryPostgresSaver) -> None:
        """Returns all thread ids when multiple distinct threads exist."""
        tids = sorted([str(uuid.uuid4()) for _ in range(5)])
        for tid in tids:
            _write_checkpoint(saver, tid)

        result = saver.list_thread_ids()
        assert result == tids  # must be sorted & de-duped

    def test_no_duplicates_for_same_thread(self, saver: MemoryPostgresSaver) -> None:
        """
        When a single thread has multiple checkpoints, list_thread_ids
        must only return that thread_id once.
        """
        tid = str(uuid.uuid4())
        # Write three checkpoints for the same thread
        _write_checkpoint(saver, tid)
        _write_checkpoint(saver, tid)
        _write_checkpoint(saver, tid)

        result = saver.list_thread_ids()
        assert result == [tid]
        assert len(result) == 1

    def test_result_is_sorted(self, saver: MemoryPostgresSaver) -> None:
        """Results are returned in alphabetical order."""
        tids = [str(uuid.uuid4()) for _ in range(10)]
        for tid in tids:
            _write_checkpoint(saver, tid)

        result = saver.list_thread_ids()
        assert result == sorted(result)

    def test_large_dataset(self, saver: MemoryPostgresSaver) -> None:
        """Correctly handles a large number of threads (performance smoke-test)."""
        n = 200
        tids = sorted([str(uuid.uuid4()) for _ in range(n)])
        for tid in tids:
            _write_checkpoint(saver, tid)

        result = saver.list_thread_ids()
        assert len(result) == n
        assert result == tids


# ---------------------------------------------------------------------------
# Tests – iter_thread_ids (paginated)
# ---------------------------------------------------------------------------


class TestIterThreadIds:
    def test_empty_store(self, saver: MemoryPostgresSaver) -> None:
        """Yields nothing when no checkpoints exist."""
        assert list(saver.iter_thread_ids()) == []

    def test_single_page(self, saver: MemoryPostgresSaver) -> None:
        """Yields all ids when total < limit."""
        tids = sorted([str(uuid.uuid4()) for _ in range(5)])
        for tid in tids:
            _write_checkpoint(saver, tid)

        result = list(saver.iter_thread_ids(limit=10, offset=0))
        assert result == tids

    def test_pagination_walks_all(self, saver: MemoryPostgresSaver) -> None:
        """Walking pages with offset retrieves every thread exactly once."""
        n = 25
        tids = sorted([str(uuid.uuid4()) for _ in range(n)])
        for tid in tids:
            _write_checkpoint(saver, tid)

        collected: list[str] = []
        page_size = 10
        offset = 0
        while True:
            page = list(saver.iter_thread_ids(limit=page_size, offset=offset))
            if not page:
                break
            collected.extend(page)
            offset += page_size

        assert collected == tids
        assert len(collected) == n

    def test_no_duplicates(self, saver: MemoryPostgresSaver) -> None:
        """Paginated iteration never returns duplicates."""
        tid = str(uuid.uuid4())
        for _ in range(5):
            _write_checkpoint(saver, tid)

        result = list(saver.iter_thread_ids(limit=100, offset=0))
        assert result == [tid]
