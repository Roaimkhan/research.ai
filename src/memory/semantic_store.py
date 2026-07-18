from src.config import config
import psycopg

DB_URL = config.DB_URL

conn = psycopg.connect(DB_URL)

def initialize_db():
    conn.execute("""
        CREATE EXTENSION IF NOT EXISTS vector
                 
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
    """)
    conn.commit()
    
cursor = conn.cursor()

