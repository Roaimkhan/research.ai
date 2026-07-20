import asyncio
from psycopg_pool import AsyncConnectionPool
from src.checkpoint.session_state import MemoryPostgresSaver 
from src.persistence import raw_pool

# 1. Define your local PostgreSQL connection string
# Replace placeholders with your actual user/password if necessary
from src.config import config
DB_CONN_STRING = config

def get_postgres_checkpointer():
    """Initializes and returns a persistent LangGraph checkpointer."""
    # Pass the pool directly, NOT an individual connection
    checkpointer = MemoryPostgresSaver(raw_pool)
    
    # Run setup to safely ensure the tables exist 
    checkpointer.setup()
    
    return checkpointer