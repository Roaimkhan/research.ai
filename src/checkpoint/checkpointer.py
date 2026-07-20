import asyncio
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 1. Define your local PostgreSQL connection string
# Replace placeholders with your actual user/password if necessary
from src.config import config

DB_CONN_STRING = config.DB_URL

async def get_postgres_checkpointer():
    """Initializes the database connection pool and sets up the LangGraph checkpointer."""
    # Create an asynchronous connection pool
    pool = AsyncConnectionPool(conninfo=DB_CONN_STRING, max_size=10, open=False)
    await pool.open()
    
    # Wrap it with the Postgres checkpointer saver
    checkpointer = AsyncPostgresSaver(pool)
    
    # Automatically creates the internal LangGraph state tracking tables if missing
    await checkpointer.setup()
    
    return checkpointer, pool