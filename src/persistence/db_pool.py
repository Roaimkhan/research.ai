from psycopg_pool import ConnectionPool

from src.config import config

DB_URL = config.DB_URL


raw_pool = ConnectionPool(DB_URL)
