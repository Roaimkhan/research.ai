from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.schemas import WriterAgentState
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=config.GOOGLE_API_KEY)
structured_llm = llm.with_structured_output(AdjudicatedMemoryItem)

def ajudication_gate(state:WriterAgentState):

    user_id = state.snapshot.user_id
    memories = state.snapshot.raw_semantic_memories

    adjudicated_memories :list[AdjudicatedMemoryItem] = []
    simple_memories:list[MemoryItemEx] = []

    for memory in memories:
        pred = memory.get("predicate")
        sub = memory.get("subject")

        cursor.execute("""
            SELECT * FROM active_beliefs
            WHERE user_id = %s AND subject = %s AND predicate = %s
                       
        """, (user_id,sub,pred))
        rows = cursor.fetchall()

        if rows:
            colnames = [description[0] for description in cursor.description]
            rows_as_dicts =  [dict(zip(colnames,row)) for row in rows]
            for row in rows_as_dicts:
                row.pop("fact_embedding",None)
                
            if rows_as_dicts:
                response = structured_llm.invoke([SystemMessage(content=SYSTEM_ADJUDICATION_PROMPT),
                            HumanMessage(content=f"""
                                    Incoming Fact:{memory} 
                                    Candidate Facts:{rows_as_dicts} """)])
                
                adjudicated_memories.append(response)


        else:
            simple_memories.append(memory)
            
        return {
            "adjudicated_memories":adjudicated_memories,
            "semantic_memories_processed":simple_memories
        }

def bitemporal_split(state:WriterAgentState):
    memories = state.adjudicated_memories

    for memory in memories:
        action = memory.get("action","")
        if not action:
            return "mamita"
        subject = memory.subject
        object = memory.object
        user_id = state.snapshot.user_id
        predicate = predicate.subject
        if action == "ADD":
            cursor.execute("""
                    INSERT TO active_beliefs
                    (fact_id,user_id,subject,predicate,object,valid_start,valid_end,transaction_start,transaction_end,provenance_uri,confidence_score,fact_embedding)
                    VALUES ('') 
                           """)


    
    
    # structured_llm = llm.with_structured_output(response)
    # response : Memmorieslisted = structured_llm.invoke(
    #     [SystemMessage(content=SYSTEM_EXTRACTION_PROMPT),
    #      HumanMessage(content=f"Latest User Message :{query.content}" )]
    #     )
    




















# placeholder
# import sqlite3
# import sqlite_vec
# import time
# import numpy as np
# from src.memory.utils import embed_text
# conn = sqlite3.connect("database.db")
# conn.enable_load_extension(True)
# sqlite_vec.load(conn)

# cursor = conn.cursor()


# cursor.execute("""
#     CREATE TABLE IF NOT EXISTS semantic_store (
#     id INTEGER PRIMARY KEY,
#     concept TEXT NOT NULL,
#     fact_value TEXT NOT NULL,
#     serial INTEGER NOT NULL,
#     confidence REAL NOT NULL,
#     source_type TEXT NOT NULL,
#     timestamp INTEGER NOT NULL,
#     session_id TEXT NOT NULL
# )
# """)


# cursor.execute("""
# CREATE VIRTUAL TABLE IF NOT EXISTS semantic_embeddings
# USING vec0(
#     embedding FLOAT[384]
# )
# """)

# # 1. store_semantic_fact(concept, fact_value, confidence, source_type, session_id, embedding) -> 
# #    queries MAX(serial) WHERE concept = X, inserts a new row with serial+1. Never updates or deletes existing rows. Returns the new row i


# def store_semantic_fact(
#         concept,
#         fact_value,
#         confidence,
#         source_type,
#         session_id,
#         embedding
#     ):

#     timestamp = int(time.time())

#     cursor.execute(f"SELECT MAX(serial) FROM semantic_store WHERE concept = ? ", (concept,))
#     result = cursor.fetchone()
#     max_serial = result[0] if result[0] is not None else 0 
#     serial = max_serial+1

#     cursor.execute(
#         "INSERT INTO semantic_store (serial, concept, fact_value, confidence, source_type, session_id, timestamp) VALUES (?,?,?,?,?,?,?)", (serial,concept, fact_value, confidence, source_type, session_id,timestamp)
#     )

#     row_id = cursor.lastrowid
#     cursor.execute(
#         "INSERT INTO semantic_embeddings (rowid, embedding) VALUES (?,?)" , (row_id,np.array(embedding, dtype=np.float32).tobytes())
#     )
#     conn.commit()
#     return row_id

# def find_relevant_concepts(query_embedding, top_k=5) -> list[str]:

#     embedding_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
#     cursor.execute(
#         """SELECT s.concept
#            FROM semantic_embeddings e
#            JOIN semantic_store s ON e.rowid = s.rowid
#            WHERE e.embedding MATCH ? AND k = ?
#            ORDER BY e.distance
#             """,
#             (embedding_bytes,top_k)
#     )
#     concepts = cursor.fetchall()
#     concepts = [i[0] for i in concepts]
#     unique_concepts = list(dict.fromkeys(concepts))
#     return unique_concepts
    
    


# def car_resolve(concept: str)->dict|None:
#     cursor.execute(
#         """
#         SELECT * FROM semantic_store
#         WHERE concept = ? 
#         """,
#         (concept,)
#     )
#     rows = cursor.fetchall()
#     if not rows:
#         return None
    
#     colnames = [description[0] for description in cursor.description]
#     rows_as_dicts =  [dict(zip(colnames,row)) for row in rows]
#     latest_row = max(rows_as_dicts, key = lambda r: r["serial"] )

#     return latest_row

# def semantic_retrieve(query_text: str = None, query_embedding: list[float] = None) -> list[dict]:
#     # Now BOTH are optional, so the function won't complain if you only pass one
#     if query_text and not query_embedding:pic, got {results}")
#         query_embedding = embed_text(query_text)
        
#     if query_embedding is None:
#         raise ValueError("Either query_embedding or query_text must be provided.")
    
#     concepts = find_relevant_concepts(query_embedding)
#     semantic_facts = []
#     for con in concepts:
#         semantic_facts.append(car_resolve(con))
        
#     return semantic_facts

#     # --- END-TO-END INTEGRATION TEST ---
# if __name__ == "__main__":
#     print("Running end-to-end pipeline test...")
#     # Reset
#     cursor.execute("DELETE FROM semantic_store"); cursor.execute("DELETE FROM semantic_embeddings")
    
#     # Pipeline: Store 3 versions of the same concept
#     concept = "user_employer"
#     for val in ["Stripe", "OpenAI", "Anthropic"]:
#         store_semantic_fact(concept, val, 1.0, "test", "sess1", embed_text(val))
    
#     # Pipeline: Retrieve via text query
#     results = semantic_retrieve(query_text="Where do I work?")
    
#     # Verification
#     latest = car_resolve(concept)
#     if results and latest["fact_value"] == "Anthropic":
#         print(f"SUCCESS: Pipeline retrieved '{results[0]['fact_value']}'. Latest is '{latest['fact_value']}' (Serial: {latest['serial']})")
#     else:
#         print(f"FAILED: Expected Anthropic, got {results}")