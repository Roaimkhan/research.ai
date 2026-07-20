from datetime import datetime
from uuid import UUID

from psycopg.rows import dict_row

from src.logging.db import instrument_connection_pool
from src.persistence.db_pool import raw_pool

pool = instrument_connection_pool(raw_pool, "semantic_store")


def initialize_db():
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS vector;
                 
        CREATE TABLE IF NOT EXISTS active_beliefs (
            fact_id UUID PRIMARY KEY,             
            user_id UUID NOT NULL,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            valid_start TIMESTAMP NOT NULL,
            valid_end TIMESTAMP,
            transaction_start TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            transaction_end TIMESTAMP,
            provenance_uri TEXT NOT NULL,
            confidence_score DOUBLE PRECISION NOT NULL,
            fact_embedding vector(1536)
        );

        CREATE TABLE IF NOT EXISTS belief_audit_trail (
            user_id UUID NOT NULL,
            audit_id SERIAL PRIMARY KEY,
            fact_id UUID NOT NULL,
            subject TEXT,
            predicate TEXT,
            object TEXT,
            transaction_start TIMESTAMP,
            transaction_end TIMESTAMP,
            adjudication_reason TEXT NOT NULL,
            judge_model TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS retrieval_config (
            config_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            w_sem DOUBLE PRECISION NOT NULL DEFAULT 0.4,
            w_key DOUBLE PRECISION NOT NULL DEFAULT 0.3,
            w_graph DOUBLE PRECISION NOT NULL DEFAULT 0.1,
            w_epi DOUBLE PRECISION NOT NULL DEFAULT 0.4,
            lambda_decay DOUBLE PRECISION NOT NULL DEFAULT 0.01,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT NOT NULL DEFAULT 'default_init'
        );

        ALTER TABLE retrieval_config
            ADD COLUMN IF NOT EXISTS w_imp DOUBLE PRECISION NOT NULL DEFAULT 0.4;

        ALTER TABLE retrieval_config
            ADD COLUMN IF NOT EXISTS w_sim DOUBLE PRECISION NOT NULL DEFAULT 0.6;

        INSERT INTO retrieval_config (
            w_sem,
            w_key,
            w_graph,
            w_epi,
            lambda_decay,
            updated_by
        )
        SELECT
            0.4,
            0.3,
            0.1,
            0.4,
            0.01,
            'default_init'
        WHERE NOT EXISTS (
            SELECT 1 FROM retrieval_config
        );

        CREATE TABLE IF NOT EXISTS semantic_eval_cases (
            case_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID,
            query_text TEXT NOT NULL,
            expected_top_fact_id UUID NOT NULL,
            decoy_fact_id UUID,
            case_type TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS episodic_eval_cases (
            case_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID,
            query_text TEXT NOT NULL,
            expected_gist_id UUID,
            forbidden_gist_id UUID,
            case_type TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS baca_diagnostic_audit_log (
            trial_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            run_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            perturbed_param TEXT NOT NULL,
            old_value DOUBLE PRECISION NOT NULL,
            candidate_value DOUBLE PRECISION NOT NULL,
            baseline_semantic_accuracy DOUBLE PRECISION NOT NULL,
            candidate_semantic_accuracy DOUBLE PRECISION NOT NULL,
            baseline_episodic_accuracy DOUBLE PRECISION NOT NULL,
            candidate_episodic_accuracy DOUBLE PRECISION NOT NULL,
            committed BOOLEAN NOT NULL,
            reason TEXT NOT NULL
        );
    """)
            conn.commit()


def retrieve_semantic_candidates(
    user_id: UUID,
    query_embedding: list[float],
    as_of: datetime,
) -> list[dict]:
    candidates: list[dict] = []
    pool_size = 30

    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    fact_id,
                    subject,
                    predicate,
                    object,
                    valid_start,
                    valid_end,
                    transaction_start,
                    confidence_score,
                    fact_embedding,
                    FALSE AS provisional
                FROM active_beliefs
                WHERE user_id = %(user_id)s
                  AND valid_start <= %(as_of)s
                  AND (valid_end IS NULL OR valid_end > %(as_of)s)
                  AND transaction_end IS NULL
                ORDER BY fact_embedding <=> %(query_embedding)s
                LIMIT %(pool_size)s
                """,
                {
                    "user_id": user_id,
                    "as_of": as_of,
                    "query_embedding": query_embedding,
                    "pool_size": pool_size,
                },
            )
            candidates.extend(cursor.fetchall())

            cursor.execute(
                """
                SELECT
                    staging_id AS fact_id,
                    subject,
                    predicate,
                    object,
                    valid_start,
                    valid_end,
                    extracted_at AS transaction_start,
                    confidence_score,
                    NULL AS fact_embedding,
                    TRUE AS provisional
                FROM staging_buffer
                WHERE user_id = %s
                  AND consolidated = FALSE
                  AND valid_start <= %s
                  AND (valid_end IS NULL OR valid_end > %s)
                """,
                (user_id, as_of, as_of),
            )
            candidates.extend(cursor.fetchall())

    return candidates

def get_serg_proximity(
    subject: str,
    predicate: str,
    query_entities: list[str],
) -> float:
    return 0.0


def get_active_baca_weights() -> dict:
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT w_sem, w_key, w_graph, w_epi, lambda_decay, w_imp, w_sim
                FROM retrieval_config
                ORDER BY updated_at DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()

    if row is None:
        raise ValueError("retrieval_config is missing; run the schema migration first")

    return dict(row)


def check_if_superseded(
    subject: str,
    predicate: str,
    as_of_valid_start: datetime,
) -> bool:
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM active_beliefs
                    WHERE subject = %s
                      AND predicate = %s
                      AND transaction_end IS NULL
                      AND valid_start > %s
                )
                """,
                (subject, predicate, as_of_valid_start),
            )
            row = cursor.fetchone()

    return bool(row[0]) if row else False

