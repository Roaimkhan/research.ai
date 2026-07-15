# placeholder
import sqlite3
import sqlite_vec
import time
import numpy as np
from src.memory.utils import embed_text
from src.schemas import SemanticMemoryUnit

conn = sqlite3.connect("database.db")
conn.enable_load_extension(True)
sqlite_vec.load(conn)

cursor = conn.cursor()


cursor.execute("""
    CREATE TABLE IF NOT EXISTS semantic_store (
    id INTEGER PRIMARY KEY,
    concept TEXT NOT NULL,
    fact_value TEXT NOT NULL,
    serial INTEGER NOT NULL,
    confidence REAL NOT NULL,
    source_type TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    session_id TEXT NOT NULL
)
""")


cursor.execute("""
CREATE VIRTUAL TABLE IF NOT EXISTS semantic_embeddings
USING vec0(
    embedding FLOAT[384]
)
""")

# 1. store_semantic_fact(concept, fact_value, confidence, source_type, session_id, embedding) -> 
#    queries MAX(serial) WHERE concept = X, inserts a new row with serial+1. Never updates or deletes existing rows. Returns the new row i


def store_semantic_fact(MemoryUnit:SemanticMemoryUnit):

    timestamp = int(time.time())

    cursor.execute(f"SELECT MAX(serial) FROM semantic_store WHERE concept = ? ", (MemoryUnit["concept"],))
    result = cursor.fetchone()
    max_serial = result[0] if result[0] is not None else 0 
    serial = max_serial+1

    cursor.execute(
        "INSERT INTO semantic_store (serial, concept, fact_value, confidence, source_type, session_id, timestamp) VALUES (?,?,?,?,?,?,?)", (serial,MemoryUnit["concept"], MemoryUnit["fact_value"], MemoryUnit["confidence"], MemoryUnit["source_type"], MemoryUnit["session_id"],timestamp)
    )

    row_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO semantic_embeddings (rowid, embedding) VALUES (?,?)" , (row_id,np.array(MemoryUnit["embedding"], dtype=np.float32).tobytes())
    )
    conn.commit()
    return row_id

def find_relevant_concepts(query_embedding:list, top_k=5) -> list[str]:

    embedding_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
    cursor.execute(
        """SELECT s.concept
           FROM semantic_embeddings e
           JOIN semantic_store s ON e.rowid = s.rowid
           WHERE e.embedding MATCH ? AND k = ?
           ORDER BY e.distance
            """,
            (embedding_bytes,top_k)
    )
    concepts = cursor.fetchall()
    concepts = [i[0] for i in concepts]
    unique_concepts = list(dict.fromkeys(concepts))
    return unique_concepts
    
    


def car_resolve(concept: str)->SemanticMemoryUnit|None:
    cursor.execute(
        """
        SELECT * FROM semantic_store
        WHERE concept = ? 
        """,
        (concept,)
    )
    rows = cursor.fetchall()
    if not rows:
        return None
    
    colnames = [description[0] for description in cursor.description]
    rows_as_dicts =  [dict(zip(colnames,row)) for row in rows]
    latest_row = max(rows_as_dicts, key = lambda r: r["serial"] )

    return latest_row

def semantic_retrieve(query_text: str = None, query_embedding: list[float] = None) -> list[SemanticMemoryUnit]:
    # Now BOTH are optional, so the function won't complain if you only pass one
    if query_text and not query_embedding:
        query_embedding = embed_text(query_text)
        
    if query_embedding is None:
        raise ValueError("Either query_embedding or query_text must be provided.")
    
    concepts = find_relevant_concepts(query_embedding)
    semantic_facts = []
    for con in concepts:
        semantic_facts.append(car_resolve(con))
    
    return semantic_facts











    # --- END-TO-END INTEGRATION TEST ---
if __name__ == "__main__":
    print("Running end-to-end pipeline test...")
    # Reset
    cursor.execute("DELETE FROM semantic_store"); cursor.execute("DELETE FROM semantic_embeddings")
    
    # Pipeline: Store 3 versions of the same concept
# These are simple dictionary literals. 
# They are "Typed" because you assign them to the type: SemanticMemoryUnit

    MockMemory1: SemanticMemoryUnit = {
        "concept": "user employer",
        "fact_value": "stripe",
        "confidence": 1.0,
        "source_type": "test",
        "session_id": "sess1",
        "embedding": embed_text("stripe")
    }

    MockMemory2: SemanticMemoryUnit = {
        "concept": "user employer",
        "fact_value": "OpenAI",
        "confidence": 1.0,
        "source_type": "test",
        "session_id": "sess1",
        "embedding": embed_text("OpenAI")
    }

    MockMemory3: SemanticMemoryUnit = {
        "concept": "user employer",
        "fact_value": "Anthropic",
        "confidence": 1.0,
        "source_type": "test",
        "session_id": "sess1",
        "embedding": embed_text("Anthropic")
    }
        
    store_semantic_fact(MockMemory1)
    store_semantic_fact(MockMemory2)
    store_semantic_fact(MockMemory3)
    
    # Pipeline: Retrieve via text query
    results = semantic_retrieve(query_text="Where do I work?")
    
    # Verification
    latest = car_resolve(MockMemory3["concept"])
    if results and latest["fact_value"] == "Anthropic":
        print(f"SUCCESS: Pipeline retrieved '{results[0]['fact_value']}'. Latest is '{latest['fact_value']}' (Serial: {latest['serial']})")
    else:
        print(f"FAILED: Expected Anthropic, got {results}")