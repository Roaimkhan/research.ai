from src.schemas import SemanticMemoryStagerState
from src.persistence.semantic_store import conn
from src.utils import embed_text


def semantic_buffer_writer(state: SemanticMemoryStagerState) -> dict:
    snapshot = state.get("snapshot")
    if not snapshot:
        raise ValueError("SemanticMemoryStagerState missing required 'snapshot' field.")

    user_id = snapshot.user_id
    conversation_id = snapshot.conversation_id
    message_id = snapshot.message_id

    memory_batch = state.get("memory_batch")

    if memory_batch and memory_batch.memmories:
        with conn.cursor() as cursor:
            for memory in memory_batch.memmories:

                # Create embedding from final semantic representation
                embedding_text = (
                    f"{memory.subject} "
                    f"{memory.predicate} "
                    f"{memory.object}"
                )

                fact_embedding = embed_text(embedding_text)

                cursor.execute(
                    """
                    INSERT INTO staging_buffer
                        (
                        fact_id,
                        user_id,
                        subject,
                        predicate,
                        object,
                        valid_start,
                        valid_end,
                        provenance_uri,
                        confidence_score,
                        fact_embedding,
                        conversation_id,
                        message_id
                        )
                    VALUES
                        (
                        %(fact_id)s,
                        %(user_id)s,
                        %(subject)s,
                        %(predicate)s,
                        %(object)s,
                        %(valid_start)s,
                        %(valid_end)s,
                        %(provenance_uri)s,
                        %(confidence_score)s,
                        %(fact_embedding)s,
                        %(conversation_id)s,
                        %(message_id)s
                        )
                    """,
                    {
                        "fact_id": str(memory.fact_id),
                        "user_id": str(user_id),
                        "subject": memory.subject,
                        "predicate": memory.predicate,
                        "object": memory.object,
                        "valid_start": memory.valid_start,
                        "valid_end": memory.valid_end,
                        "provenance_uri": memory.provenance_uri,
                        "confidence_score": memory.confidence_score,
                        "fact_embedding": fact_embedding,
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                    },
                )

            conn.commit()

    return {}