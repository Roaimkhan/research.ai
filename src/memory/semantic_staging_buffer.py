from src.config import config
from psycopg_pool import ConnectionPool
import psycopg

DB_URL = config.DB_URL

pool = ConnectionPool(DB_URL)

def initialize_db():
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS staging_buffer (
                    staging_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    valid_start TIMESTAMP NOT NULL,
                    valid_end TIMESTAMP,
                    provenance_uri TEXT NOT NULL,
                    confidence_score DOUBLE PRECISION NOT NULL,
                    extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    conversation_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    consolidated BOOLEAN NOT NULL DEFAULT FALSE
                );

            CREATE INDEX IF NOT EXISTS idx_staging_unconsolidated
                ON staging_buffer (user_id, subject, predicate)
                WHERE consolidated = FALSE;
                """)
            conn.commit()
