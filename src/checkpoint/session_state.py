"""
checkpointer.py
---------------
Extends the default PostgresSaver with extra public helpers:

  list_thread_ids()          -> list[str]
      Returns every unique thread_id currently stored in the
      checkpoints table, sorted alphabetically.  Returns [] when
      the store is empty.

  iter_thread_ids(limit, offset) -> Iterator[str]
      Paginated variant – yields thread_ids one by one so that
      callers can enumerate very large stores without loading every
      id into memory at once.

Both methods rely on a single, efficient SQL query that uses
database-side DISTINCT deduplication and never deserializes any
checkpoint payloads.
"""

from __future__ import annotations

from typing import Generator

import psycopg
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

_LIST_THREAD_IDS_SQL = """
    SELECT DISTINCT thread_id
    FROM checkpoints
    ORDER BY thread_id;
"""

_PAGINATED_THREAD_IDS_SQL = """
    SELECT DISTINCT thread_id
    FROM checkpoints
    ORDER BY thread_id
    LIMIT %s OFFSET %s;
"""


class MemoryPostgresSaver(PostgresSaver):
    """
    A drop-in replacement for :class:`PostgresSaver` that adds
    ``list_thread_ids()`` and ``iter_thread_ids()`` to the public API.

    Usage
    -----
    Use exactly like ``PostgresSaver`` – via the ``from_conn_string``
    context manager::

        with MemoryPostgresSaver.from_conn_string(DB_URI) as checkpointer:
            checkpointer.setup()
            thread_ids = checkpointer.list_thread_ids()
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_thread_ids(self) -> list[str]:
        """
        Return every unique ``thread_id`` stored in the checkpoint
        backend, sorted alphabetically.

        * Returns ``[]`` when the store contains no checkpoints.
        * Uses ``DISTINCT`` server-side – no payload data is loaded.
        * Safe to call before or after agent invocations as long as
          the connection is still open (i.e. inside the ``with`` block).

        Returns
        -------
        list[str]
            Sorted list of unique thread ids.
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(_LIST_THREAD_IDS_SQL)
            rows = cur.fetchall()
        return [row["thread_id"] for row in rows]

    def iter_thread_ids(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> Generator[str, None, None]:
        """
        Yield ``thread_id`` values from the checkpoint store in pages.

        This is the preferred approach when the number of stored
        threads can be very large, because it never loads the full
        list into memory.

        Parameters
        ----------
        limit:
            Maximum number of thread ids to return per page (default 100).
        offset:
            Number of thread ids to skip before the first result
            (default 0).  Increment by ``limit`` to walk through pages.

        Yields
        ------
        str
            Unique thread ids, sorted alphabetically.

        Example
        -------
        ::

            # Walk every thread, 50 at a time
            offset = 0
            while True:
                batch = list(checkpointer.iter_thread_ids(limit=50, offset=offset))
                if not batch:
                    break
                for tid in batch:
                    print(tid)
                offset += 50
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(_PAGINATED_THREAD_IDS_SQL, (limit, offset))
            for row in cur:
                yield row["thread_id"]
