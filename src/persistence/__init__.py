from .semantic_store import initialize_db as initialize_semantic_store
from .db_pool import raw_pool
from .semantic_staging_buffer import initialize_db as initialize_staging_buffer


def initialize_db():
    initialize_semantic_store()
    initialize_staging_buffer()
