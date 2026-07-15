"""
memory.py — SQLite-backed semantic + episodic memory for the demo.

Tables:
  semantic_memory: concept, fact_value, serial, timestamp, session_id
  episodic_memory: content, timestamp, session_id

CAR (Conflict-Aware Retrieval):
  For any concept, max(serial) always wins — no LLM judgment needed.
"""

import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "demo_memory.db")

def _conn():
    """Return a connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create tables if they don't exist."""
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS semantic_memory (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            concept     TEXT    NOT NULL,
            fact_value  TEXT    NOT NULL,
            serial      INTEGER NOT NULL,
            timestamp   TEXT    NOT NULL,
            session_id  TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            content     TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'user',
            timestamp   TEXT    NOT NULL,
            session_id  TEXT    NOT NULL
        );
    """)
    conn.commit()
    conn.close()


# ── Semantic Memory ──────────────────────────────────────────────────────────

def store_semantic(concept: str, fact_value: str, session_id: str) -> dict:
    """
    Store a semantic fact. Automatically assigns the next serial for this concept.
    Returns a dict describing what was stored (for UI logging).
    """
    concept = concept.strip().lower().replace(" ", "_")
    conn = _conn()

    # Get current max serial for this concept
    row = conn.execute(
        "SELECT MAX(serial) as max_serial FROM semantic_memory WHERE concept = ?",
        (concept,)
    ).fetchone()
    next_serial = (row["max_serial"] or 0) + 1

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO semantic_memory (concept, fact_value, serial, timestamp, session_id) VALUES (?, ?, ?, ?, ?)",
        (concept, fact_value, next_serial, now, session_id)
    )
    conn.commit()
    conn.close()

    return {
        "concept": concept,
        "fact_value": fact_value,
        "serial": next_serial,
        "session_id": session_id,
    }


def retrieve_semantic(query: str) -> list[dict]:
    """
    Keyword-match concepts against the query text.
    For each matched concept, return only the row with max(serial) — CAR resolution.
    Returns a list of dicts with concept, fact_value, serial, session_id.
    """
    conn = _conn()
    all_concepts = conn.execute(
        "SELECT DISTINCT concept FROM semantic_memory"
    ).fetchall()

    query_lower = query.lower().replace(" ", "_")
    matched_concepts = []
    for row in all_concepts:
        concept = row["concept"]
        # Match if the concept appears in the query OR any word of the query appears in the concept
        concept_words = concept.split("_")
        query_words = query.lower().split()
        if concept in query_lower or any(w in concept for w in query_words if len(w) > 2):
            matched_concepts.append(concept)

    results = []
    for concept in matched_concepts:
        row = conn.execute(
            """SELECT concept, fact_value, serial, session_id, timestamp
               FROM semantic_memory
               WHERE concept = ?
               ORDER BY serial DESC
               LIMIT 1""",
            (concept,)
        ).fetchone()
        if row:
            results.append(dict(row))

    conn.close()
    return results


def get_all_semantic() -> list[dict]:
    """Get all semantic memories (for debug/display)."""
    conn = _conn()
    rows = conn.execute(
        "SELECT concept, fact_value, serial, session_id, timestamp FROM semantic_memory ORDER BY concept, serial"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Episodic Memory ──────────────────────────────────────────────────────────

def store_episodic(content: str, session_id: str, role: str = "user"):
    """Store a conversation turn as an episodic memory."""
    conn = _conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO episodic_memory (content, role, timestamp, session_id) VALUES (?, ?, ?, ?)",
        (content, role, now, session_id)
    )
    conn.commit()
    conn.close()


def retrieve_episodic(query: str, limit: int = 5) -> list[dict]:
    """
    Keyword-match against recent episodic memories.
    Returns up to `limit` rows, ordered by recency.
    """
    conn = _conn()
    query_words = [w for w in query.lower().split() if len(w) > 2]

    if not query_words:
        conn.close()
        return []

    # Build a WHERE clause that matches any query word in the content
    conditions = " OR ".join(["LOWER(content) LIKE ?" for _ in query_words])
    params = [f"%{w}%" for w in query_words]

    rows = conn.execute(
        f"""SELECT content, role, timestamp, session_id
            FROM episodic_memory
            WHERE {conditions}
            ORDER BY timestamp DESC
            LIMIT ?""",
        params + [limit]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def reset_db():
    """Nuke everything — for full resets during development only."""
    conn = _conn()
    conn.executescript("DELETE FROM semantic_memory; DELETE FROM episodic_memory;")
    conn.commit()
    conn.close()
