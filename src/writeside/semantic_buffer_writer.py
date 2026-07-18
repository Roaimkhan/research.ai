from src.schemas import SemanticMemoryStagerState
from src.memory import conn

def semantic_buffer_writer(state: SemanticMemoryStagerState) -> dict:
    snapshot = state.get("snapshot")
    if not snapshot:
        raise ValueError("SemanticMemoryStagerState missing required 'snapshot' field.")

    user_id = snapshot.user_id
    conversation_id = snapshot.conversation_id
    message_id = snapshot.message_id
    
    memory_batch = state.get("memory_batch")
    
    if memory_batch and memory_batch.memmories:
        # Create a new cursor for this invocation to prevent race conditions
        with conn.cursor() as cursor:
            for memory in memory_batch.memmories:
                cursor.execute(
                    """
                    INSERT INTO staging_buffer
                        (user_id,
                        subject,
                        predicate,
                        object,
                        valid_start,
                        valid_end,
                        provenance_uri,
                        confidence_score,
                        conversation_id,
                        message_id)
                    VALUES
                        (%(user_id)s,
                        %(subject)s,
                        %(predicate)s,
                        %(object)s,
                        %(valid_start)s,
                        %(valid_end)s,
                        %(provenance_uri)s,
                        %(confidence_score)s,
                        %(conversation_id)s,
                        %(message_id)s)
                    """,
                    {
                        "user_id": str(user_id),
                        "subject": memory.subject,
                        "predicate": memory.predicate,
                        "object": memory.object,
                        "valid_start": memory.valid_start,
                        "valid_end": memory.valid_end,
                        "provenance_uri": memory.provenance_uri,
                        "confidence_score": memory.confidence_score,
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                    },
                )
            # Commit the transaction
            conn.commit()

    return {}
