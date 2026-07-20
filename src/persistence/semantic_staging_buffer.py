from src.config import config
from psycopg_pool import ConnectionPool
import psycopg
from src.logging.db import instrument_connection_pool

DB_URL = config.DB_URL

_raw_pool = ConnectionPool(DB_URL)
pool = instrument_connection_pool(_raw_pool, "semantic_staging_buffer")

def initialize_db():
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("ALTER TABLE staging_buffer ADD COLUMN IF NOT EXISTS fact_embedding vector(384);")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS staging_buffer (
                    staging_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    fact_id UUID NOT NULL,
                    user_id UUID NOT NULL,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    valid_start TIMESTAMP NOT NULL,
                    valid_end TIMESTAMP,
                    provenance_uri TEXT NOT NULL,
                    confidence_score DOUBLE PRECISION NOT NULL,
                    fact_embedding vector(384),
                    extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    conversation_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    consolidated BOOLEAN NOT NULL DEFAULT FALSE
                );

                CREATE INDEX IF NOT EXISTS idx_staging_unconsolidated
                    ON staging_buffer (user_id, subject, predicate)
                    WHERE consolidated = FALSE;

                CREATE INDEX IF NOT EXISTS idx_staging_embedding
                    ON staging_buffer
                    USING hnsw (fact_embedding vector_cosine_ops);
            """)
            conn.commit()
