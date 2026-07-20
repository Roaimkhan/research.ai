from __future__ import annotations

from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from src.config import config
from src.logging.db import instrument_connection

DB_URL = config.DB_URL

DEDUP_SIMILARITY_THRESHOLD = 0.9
RETRIEVAL_SIMILARITY_THRESHOLD = 0.75

_raw_conn = psycopg.connect(DB_URL)
conn = instrument_connection(_raw_conn, "procedural_store")


def initialize_db() -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS procedural_skill_rejections (
            rejection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            task_id TEXT NOT NULL,
            source_task_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            draft_skill_text TEXT NOT NULL,
            rejection_reason TEXT NOT NULL,
            judge_model TEXT NOT NULL,
            rejected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS procedural_skills (
            skill_id UUID PRIMARY KEY,
            user_id UUID NOT NULL,
            workspace_id UUID,
            skill_name TEXT NOT NULL,
            trigger_pattern TEXT NOT NULL,
            trigger_embedding VECTOR(1536),
            file_path TEXT NOT NULL,
            source_task_ids TEXT[] NOT NULL DEFAULT '{}',
            validation_confidence DOUBLE PRECISION NOT NULL,
            success_count INTEGER NOT NULL DEFAULT 0,
            failure_count INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            erasure_tombstone BOOLEAN NOT NULL DEFAULT FALSE
        );
        """
    )
    conn.commit()


cursor = conn.cursor()


def log_skill_rejection(
    user_id: UUID,
    task_id: str,
    source_task_ids: list[str],
    draft_skill_text: str,
    rejection_reason: str,
    judge_model: str,
) -> None:
    """
    Persist a rejected procedural skill for auditing and future analysis.
    """
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            INSERT INTO procedural_skill_rejections (
                user_id,
                task_id,
                source_task_ids,
                draft_skill_text,
                rejection_reason,
                judge_model,
                rejected_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                task_id,
                source_task_ids,
                draft_skill_text,
                rejection_reason,
                judge_model,
                datetime.utcnow(),
            ),
        )
        conn.commit()


def find_similar_skill(
    trigger_embedding: list[float],
    user_id: UUID,
) -> UUID | None:
    """Find the nearest active skill for the user using pgvector similarity."""
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT skill_id, trigger_embedding <=> %s AS distance
            FROM procedural_skills
            WHERE user_id = %s
              AND is_active = TRUE
            ORDER BY trigger_embedding <=> %s
            LIMIT 1
            """,
            (trigger_embedding, user_id, trigger_embedding),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    similarity = 1 - float(row["distance"])
    if similarity >= DEDUP_SIMILARITY_THRESHOLD:
        return UUID(str(row["skill_id"]))
    return None


def append_source_task(
    skill_id: UUID,
    task_id: str,
) -> None:
    """Append a task identifier to the source_task_ids array for a skill."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE procedural_skills
            SET source_task_ids = array_append(source_task_ids, %s)
            WHERE skill_id = %s;
            """,
            (task_id, skill_id),
        )
        conn.commit()


def retrieve_matching_skills(
    user_id: UUID,
    task_embedding: list[float],
    top_k: int = 3,
) -> list[dict]:
    """Retrieve active procedural skills for a user and rank them by similarity and success rate."""
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT
                skill_id,
                skill_name,
                file_path,
                success_count,
                failure_count,
                trigger_embedding <=> %(task_embedding)s AS distance
            FROM procedural_skills
            WHERE user_id = %(user_id)s
              AND is_active = TRUE
            ORDER BY trigger_embedding <=> %(task_embedding)s
            LIMIT %(top_k)s;
            """,
            {
                "user_id": user_id,
                "task_embedding": task_embedding,
                "top_k": top_k,
            },
        )
        rows = cursor.fetchall()

    ranked_rows: list[dict] = []
    for row in rows:
        similarity = 1.0 - float(row["distance"])
        if similarity < RETRIEVAL_SIMILARITY_THRESHOLD:
            continue

        success_count = int(row.get("success_count", 0) or 0)
        failure_count = int(row.get("failure_count", 0) or 0)
        tie_breaker = success_count / (success_count + failure_count + 1)
        ranked_rows.append(
            {
                **dict(row),
                "similarity": similarity,
                "tie_breaker": tie_breaker,
            }
        )

    ranked_rows.sort(
        key=lambda row: (
            -float(row["similarity"]),
            -float(row["tie_breaker"]),
            str(row.get("skill_name", "")),
        )
    )
    return ranked_rows


def write_skill(
    skill_id: UUID,
    user_id: UUID,
    workspace_id: UUID | None,
    skill_name: str,
    trigger_pattern: str,
    trigger_embedding: list[float],
    file_path: str,
    source_task_ids: list[str],
    validation_confidence: float,
) -> None:
    """Persist a new procedural skill row using the supplied skill_id."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO procedural_skills (
                skill_id,
                user_id,
                workspace_id,
                skill_name,
                trigger_pattern,
                trigger_embedding,
                file_path,
                source_task_ids,
                validation_confidence,
                success_count,
                failure_count,
                is_active,
                created_at,
                erasure_tombstone
            )
            VALUES (
                %(skill_id)s,
                %(user_id)s,
                %(workspace_id)s,
                %(skill_name)s,
                %(trigger_pattern)s,
                %(trigger_embedding)s,
                %(file_path)s,
                %(source_task_ids)s,
                %(validation_confidence)s,
                0,
                0,
                TRUE,
                CURRENT_TIMESTAMP,
                FALSE
            );
            """,
            {
                "skill_id": skill_id,
                "user_id": user_id,
                "workspace_id": workspace_id,
                "skill_name": skill_name,
                "trigger_pattern": trigger_pattern,
                "trigger_embedding": trigger_embedding,
                "file_path": file_path,
                "source_task_ids": source_task_ids,
                "validation_confidence": validation_confidence,
            },
        )
        conn.commit()


def delete_skill(skill_id: UUID) -> None:
    """Remove a procedural skill row by skill_id."""
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM procedural_skills WHERE skill_id = %s;",
            (skill_id,),
        )
        conn.commit()
