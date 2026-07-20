from __future__ import annotations

from src.config import config
import psycopg
from uuid import UUID

from psycopg.rows import dict_row
from src.logging.db import instrument_connection

DB_URL = config.DB_URL

_raw_conn = psycopg.connect(DB_URL)
conn = instrument_connection(_raw_conn, "episodic_store")

def initialize_db():
    conn.execute("""
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS vector;

        CREATE TABLE episodic_sessions (
            session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL,
            session_start TIMESTAMP NOT NULL,
            session_end TIMESTAMP,
            interaction_count INT NOT NULL DEFAULT 0,
            peak_emotional_state TEXT,
            system_execution_success_rate DOUBLE PRECISION DEFAULT 1.0,
            session_summary TEXT,
            session_summary_embedding vector(384),
            metadata JSONB DEFAULT '{}'::jsonb
        );
                 
    
    CREATE TABLE episodic_gists (
            gist_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            session_id UUID NOT NULL REFERENCES episodic_sessions(session_id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            recorded_at TIMESTAMP NOT NULL,
            gist_text TEXT,
            gist_embedding vector(384),
            
            -- Biological & Operational Scoring Elements
            importance_score_initial DOUBLE PRECISION NOT NULL,
            importance_score_current DOUBLE PRECISION NOT NULL,
            frequency_count INT NOT NULL DEFAULT 1,
            bayesian_surprise_score DOUBLE PRECISION NOT NULL,
            entity_salience_score DOUBLE PRECISION NOT NULL,
            outcome_score DOUBLE PRECISION NOT NULL,
            
       
            last_accessed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            time_to_live_hours INT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            erasure_tombstone BOOLEAN NOT NULL DEFAULT FALSE,
            
            referenced_fact_id UUID,
            
            metadata JSONB DEFAULT '{}'::jsonb
            );
        CREATE INDEX idx_episodic_gists_active_score ON episodic_gists (user_id, is_active, importance_score_current DESC);
        CREATE INDEX idx_episodic_gists_time ON episodic_gists (recorded_at DESC);
        CREATE INDEX idx_episodic_gists_vector ON episodic_gists USING hnsw (gist_embedding vector_cosine_ops);
        CREATE INDEX idx_episodic_gists_session ON episodic_gists (session_id);

        CREATE TABLE user_episodic_centroid (
            user_id UUID PRIMARY KEY,
            centroid_embedding vector(1024) NOT NULL,
            embedding_count INT NOT NULL DEFAULT 0,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE session_temporal_adjacency_graph (
            edge_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            source_gist_id UUID NOT NULL REFERENCES episodic_gists(gist_id) ON DELETE CASCADE,
            target_gist_id UUID NOT NULL REFERENCES episodic_gists(gist_id) ON DELETE CASCADE,
            transition_type TEXT NOT NULL,
            weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            CONSTRAINT chk_different_gists CHECK (source_gist_id <> target_gist_id)
        );

        CREATE INDEX idx_stag_adjacency ON session_temporal_adjacency_graph (source_gist_id, target_gist_id);
    """)
    conn.commit()
    
cursor = conn.cursor()

"""Episodic persistence helpers.

Only contains PostgreSQL read/write helper functions. Helpers accept a
psycopg cursor so callers control transactions.

Transaction ownership: callers must manage commit/rollback; these helpers
never commit or roll back.
"""

import uuid
import json
from typing import Dict

from src.persistence.semantic_store import conn


DEFAULT_TTL_HOURS = 720


def ensure_session_upsert(cursor, gist: Dict[str, object]) -> None:
    """Ensure an episodic_sessions row exists for the provided session.

    Args:
        cursor: a psycopg cursor obtained from the project's `conn`.
        gist: dict containing at least `session_id`, `user_id`, and optionally
              `session_start_candidate`.

    SQL operation performed:
        Performs an atomic INSERT of a session row using `ON CONFLICT (session_id)
        DO NOTHING` to avoid a prior SELECT. This guarantees the insert is
        safe under concurrent writers.

    Return value:
        None.

    Transaction ownership:
        The caller manages the transaction (commit/rollback); this helper does
        not commit or roll back.
    """
    session_id = gist["session_id"]
    user_id = gist["user_id"]
    session_start = gist.get("session_start_candidate")

    cursor.execute(
        """
        INSERT INTO episodic_sessions (
            session_id, user_id, session_start, session_end, interaction_count,
            peak_emotional_state, system_execution_success_rate, session_summary,
            session_summary_embedding, metadata
        ) VALUES (%s, %s, %s, NULL, 0, NULL, DEFAULT, NULL, NULL, '{}'::jsonb)
        ON CONFLICT (session_id) DO NOTHING
        """,
        (session_id, user_id, session_start),
    )


def increment_interaction_count(cursor, session_id: str, increment: int) -> None:
    """Increment `interaction_count` for a session.

    Args:
        cursor: a psycopg cursor from the project's `conn`.
        session_id: UUID string of the session to update.
        increment: integer number to add to `interaction_count`.

    SQL operation performed:
        Executes an UPDATE that adds `increment` to `interaction_count` for the
        provided `session_id`.

    Return value:
        None.

    Transaction ownership:
        Caller manages commit/rollback.
    """
    cursor.execute(
        "UPDATE episodic_sessions SET interaction_count = interaction_count + %s WHERE session_id = %s",
        (increment, session_id),
    )


def insert_gist(cursor, gist: Dict[str, object]) -> str:
    """Insert a new episodic_gists row and return the generated gist_id.

    Args:
        cursor: a psycopg cursor from the project's `conn`.
        gist: dict with keys required to populate the gist row:
            - session_id, user_id, recorded_at, gist_text, gist_embedding,
            - importance_score_initial, bayesian_surprise_score,
            - entity_salience_score, outcome_score,
            - dominant_emotion_label, source_entry_ids (iterable)

    SQL operation performed:
        Executes an INSERT into `episodic_gists`. `gist_id` is generated in
        Python with `uuid.uuid4()` and used in the INSERT.

    Return value:
        The generated `gist_id` string (UUID).

    Transaction ownership:
        Caller manages commit/rollback.
    """
    gist_id = str(uuid.uuid4())

    metadata = {
        "dominant_emotion_label": gist.get("dominant_emotion_label"),
        "source_entry_ids": list(gist.get("source_entry_ids", [])),
    }

    cursor.execute(
        """
        INSERT INTO episodic_gists (
            gist_id, session_id, user_id, recorded_at, gist_text, gist_embedding,
            importance_score_initial, importance_score_current, bayesian_surprise_score,
            entity_salience_score, outcome_score, last_accessed_at, time_to_live_hours,
            is_active, erasure_tombstone, referenced_fact_id, metadata
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, TRUE, FALSE, NULL, %s)
        """,
        (
            gist_id,
            gist["session_id"],
            gist["user_id"],
            gist["recorded_at"],
            gist["gist_text"],
            gist["gist_embedding"],
            gist["importance_score_initial"],
            gist["importance_score_initial"],
            gist["bayesian_surprise_score"],
            gist["entity_salience_score"],
            gist["outcome_score"],
            DEFAULT_TTL_HOURS,
            json.dumps(metadata),
        ),
    )

    return gist_id


def get_gist_metadata(cursor, gist_id: str):
    """Fetch minimal metadata for a gist.

    Args:
        cursor: a psycopg cursor from the project's `conn`.
        gist_id: UUID string of the gist to query.

    SQL operation performed:
        SELECT user_id, recorded_at FROM episodic_gists WHERE gist_id = %s

    Return value:
        Tuple `(user_id, recorded_at)` if found, otherwise `None`.

    Transaction ownership:
        Caller manages commit/rollback.
    """
    cursor.execute(
        "SELECT user_id, recorded_at FROM episodic_gists WHERE gist_id = %s",
        (gist_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return row[0], row[1]


def get_previous_gist_id(cursor, user_id: str, recorded_at) -> str | None:
    """Find the immediately preceding gist_id for a user.

    Args:
        cursor: a psycopg cursor from the project's `conn`.
        user_id: UUID string of the user.
        recorded_at: timestamp of the current gist.

    SQL operation performed:
        SELECT gist_id FROM episodic_gists WHERE user_id = %s AND recorded_at < %s
        ORDER BY recorded_at DESC LIMIT 1

    Return value:
        The preceding `gist_id` string or `None` if none exists.

    Transaction ownership:
        Caller manages commit/rollback.
    """
    cursor.execute(
        "SELECT gist_id FROM episodic_gists WHERE user_id = %s AND recorded_at < %s ORDER BY recorded_at DESC LIMIT 1",
        (user_id, recorded_at),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return row[0]


def insert_stag_edge(cursor, source_gist_id: str, target_gist_id: str, transition_type: str = "temporal_sequence", weight: float = 1.0) -> str:
    """Insert an edge into `session_temporal_adjacency_graph`.

    Args:
        cursor: a psycopg cursor from the project's `conn`.
        source_gist_id: UUID string for the source gist.
        target_gist_id: UUID string for the target gist.
        transition_type: textual label for the transition.
        weight: numeric weight for the edge.

    SQL operation performed:
        INSERT INTO session_temporal_adjacency_graph (edge_id, source_gist_id, target_gist_id, transition_type, weight)
        VALUES (%s, %s, %s, %s, %s)

    Return value:
        The generated `edge_id` string (UUID).

    Transaction ownership:
        Caller manages commit/rollback. This helper does not swallow SQL errors;
        callers should catch and handle exceptions as appropriate.
    """
    edge_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO session_temporal_adjacency_graph (edge_id, source_gist_id, target_gist_id, transition_type, weight) VALUES (%s, %s, %s, %s, %s)",
        (edge_id, source_gist_id, target_gist_id, transition_type, weight),
    )
    return edge_id


def get_recent_session_ids(cursor, user_id: str, limit: int = 10) -> list:
    """Return up to `limit` most recent session_id UUIDs for the user.

    Transaction ownership: caller manages commit/rollback.
    """
    cursor.execute(
        """
        SELECT session_id
        FROM episodic_sessions
        WHERE user_id = %s
        ORDER BY session_start DESC
        LIMIT %s
        """,
        (user_id, limit),
    )
    rows = cursor.fetchall()
    return [row[0] for row in rows] if rows else []


def count_similar_recent_gists(cursor, session_ids: list, current_embedding: list, threshold: float) -> int:
    """Count recent gists (in session_ids) whose cosine similarity with
    current_embedding exceeds `threshold`.

    Uses pgvector `<=>` distance operator and the vector cosine mapping used
    elsewhere in the project. Returns integer count. Caller manages
    transaction commit/rollback.
    """
    if not session_ids:
        return 0

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM episodic_gists
        WHERE session_id = ANY(%(session_ids)s)
          AND gist_embedding IS NOT NULL
          AND (1 - (gist_embedding <=> %(current_embedding)s)) > %(threshold)s
        """,
        {
            "session_ids": session_ids,
            "current_embedding": current_embedding,
            "threshold": threshold,
        },
    )
    row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def get_user_centroid(cursor, user_id: str):
    """Return (centroid_embedding, embedding_count) or None if absent.

    Transaction ownership: caller manages commit/rollback.
    """
    cursor.execute(
        """
        SELECT centroid_embedding, embedding_count
        FROM user_episodic_centroid
        WHERE user_id = %s
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return row[0], row[1]


def get_user_centroid_similarity(cursor, user_id: str, current_embedding: list) -> float | None:
    """Return cosine similarity between stored centroid and current_embedding,
    using pgvector operators. Returns None if no centroid exists.

    Transaction ownership: caller manages commit/rollback.
    """
    cursor.execute(
        """
        SELECT 1 - (centroid_embedding <=> %(current_embedding)s) AS cosine_sim
        FROM user_episodic_centroid
        WHERE user_id = %s
        """,
        {"current_embedding": current_embedding, "user_id": user_id},
    )
    row = cursor.fetchone()
    if not row or row[0] is None:
        return None
    return float(row[0])


def upsert_user_centroid(cursor, user_id: str, centroid_embedding: list, embedding_count: int) -> None:
    """Insert or update the user's centroid row using ON CONFLICT.

    Caller manages transaction commit/rollback.
    """
    cursor.execute(
        """
        INSERT INTO user_episodic_centroid (user_id, centroid_embedding, embedding_count)
        VALUES (%(user_id)s, %(centroid_embedding)s, %(embedding_count)s)
        ON CONFLICT (user_id) DO UPDATE
          SET centroid_embedding = EXCLUDED.centroid_embedding,
              embedding_count = EXCLUDED.embedding_count,
              updated_at = CURRENT_TIMESTAMP
        """,
        {
            "user_id": user_id,
            "centroid_embedding": centroid_embedding,
            "embedding_count": embedding_count,
        },
    )


def retrieve_episodic_candidates(
    user_id: UUID,
    min_importance: float = 0.0,
) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT
                gist_id,
                session_id,
                user_id,
                recorded_at,
                gist_text,
                gist_embedding,
                importance_score_current,
                frequency_count,
                metadata
            FROM episodic_gists
            WHERE user_id = %s
              AND is_active = TRUE
              AND erasure_tombstone = FALSE
              AND gist_embedding IS NOT NULL
              AND importance_score_current >= %s
            ORDER BY recorded_at DESC
            LIMIT 200
            """,
            (user_id, min_importance),
        )
        return cursor.fetchall()


def get_stag_neighbors(
    gist_id: UUID,
    direction: str = "both",
) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cursor:
        if direction == "before":
            cursor.execute(
                """
                SELECT
                    source_gist_id AS neighbor_gist_id,
                    transition_type,
                    weight
                FROM session_temporal_adjacency_graph
                WHERE target_gist_id = %s
                """,
                (gist_id,),
            )
            return cursor.fetchall()

        if direction == "after":
            cursor.execute(
                """
                SELECT
                    target_gist_id AS neighbor_gist_id,
                    transition_type,
                    weight
                FROM session_temporal_adjacency_graph
                WHERE source_gist_id = %s
                """,
                (gist_id,),
            )
            return cursor.fetchall()

        if direction == "both":
            cursor.execute(
                """
                SELECT
                    source_gist_id AS neighbor_gist_id,
                    transition_type,
                    weight
                FROM session_temporal_adjacency_graph
                WHERE target_gist_id = %s
                """,
                (gist_id,),
            )
            before_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    target_gist_id AS neighbor_gist_id,
                    transition_type,
                    weight
                FROM session_temporal_adjacency_graph
                WHERE source_gist_id = %s
                """,
                (gist_id,),
            )
            after_rows = cursor.fetchall()
            return before_rows + after_rows

        raise ValueError(f"invalid direction: {direction}")


def reactivate_gists(
    gist_ids: list[UUID],
) -> None:
    if not gist_ids:
        return

    with conn.transaction():
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE episodic_gists
                SET
                    last_accessed_at = CURRENT_TIMESTAMP,
                    frequency_count = frequency_count + 1,
                    importance_score_current = importance_score_initial
                WHERE gist_id = ANY(%s)
                """,
                (gist_ids,),
            )


def get_session_summary(
    session_id: UUID,
) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT
                session_summary,
                peak_emotional_state,
                session_start,
                session_end
            FROM episodic_sessions
            WHERE session_id = %s
            """,
            (session_id,),
        )
        row = cursor.fetchone()
        if row is None or row["session_summary"] is None:
            return None
        return row


def get_gist_texts_by_ids(
    gist_ids: list[UUID],
) -> list[str]:
    if not gist_ids:
        return []

    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT gist_id, gist_text
            FROM episodic_gists
            WHERE gist_id = ANY(%s)
              AND gist_text IS NOT NULL
            """,
            (gist_ids,),
        )
        rows = cursor.fetchall()

    text_by_id = {row["gist_id"]: row["gist_text"] for row in rows}
    return [text_by_id[gist_id] for gist_id in gist_ids if gist_id in text_by_id]

