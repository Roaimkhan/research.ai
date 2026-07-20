from src.persistence.semantic_store import conn
from src.schemas import SemanticBufferConsolidatorState, MemoryRecord
from src.utils import embed_text
from src.clients.config import settings


JUDGE_MODEL = getattr(settings, "QWEN_MODEL", "qwen")


def consolidate_fresh_memories(state: SemanticBufferConsolidatorState):
    snapshot = state.get("snapshot")
    if snapshot is None:
        raise ValueError("SemanticBufferConsolidatorState missing required 'snapshot' field.")

    fresh_memories = state.get("fresh_memories")
    if fresh_memories is None or not fresh_memories.memmories:
        return state

    user_id = snapshot.user_id
    with conn.cursor() as cursor:
        for memory in fresh_memories.memmories:
            embedding = embed_text(f"{memory.subject} {memory.predicate} {memory.object}")
            _insert_new_belief(cursor, memory, user_id, embedding)
        conn.commit()

    return state


def bitemporal_split(state: SemanticBufferConsolidatorState):
    snapshot = state.get("snapshot")
    if snapshot is None:
        raise ValueError("SemanticBufferConsolidatorState missing required 'snapshot' field.")

    memories_list = state.get("adjudicated_memories")
    if memories_list is None or not memories_list.memories:
        return state

    user_id = snapshot.user_id

    with conn.cursor() as cursor:
        for item in memories_list.memories:
            action = item.action
            record = item.memory

            if action == "IGNORE":
                continue

            embedding = embed_text(f"{record.subject} {record.predicate} {record.object}")

            if action == "ADD":
                _insert_new_belief(cursor, record, user_id, embedding)

            elif action in {"REPLACE", "CONTRADICT"}:
                for old_fact_id in item.target_fact_ids:
                    _retract_and_audit(cursor, fact_id=old_fact_id,
                                        reason=item.adjudication_reason or "Superseded by newer fact.")
                _insert_new_belief(cursor, record, user_id, embedding)

            else:
                raise ValueError(f"Unknown adjudication action: {action}")
        conn.commit()

    return state


def _insert_new_belief(cursor, record: MemoryRecord, user_id: str, embedding: list[float]):
    cursor.execute(
        """
        INSERT INTO active_beliefs
            (fact_id, user_id, subject, predicate, object,
             valid_start, valid_end, transaction_start, transaction_end,
             provenance_uri, confidence_score, fact_embedding)
        VALUES
            (%(fact_id)s, %(user_id)s, %(subject)s, %(predicate)s, %(object)s,
             %(valid_start)s, %(valid_end)s, DEFAULT, NULL,
             %(provenance_uri)s, %(confidence_score)s, %(fact_embedding)s)
        """,
        {
            "fact_id": record.fact_id,
            "user_id": user_id,
            "subject": record.subject,
            "predicate": record.predicate,
            "object": record.object,
            "valid_start": record.valid_start,
            "valid_end": record.valid_end,
            "provenance_uri": record.provenance_uri,
            "confidence_score": record.confidence_score,
            "fact_embedding": embedding,
        },
    )


def _retract_and_audit(cursor, fact_id: str, reason: str):
    """
    Closes transaction-time on the losing fact and moves it atomically
    into belief_audit_trail with a signed judge verdict.
    Must run in a single transaction — audit move without close, or
    close without audit, both break replay consistency.
    """
    cursor.execute("BEGIN")
    try:
        cursor.execute(
            """
            UPDATE active_beliefs
            SET transaction_end = CURRENT_TIMESTAMP
            WHERE fact_id = %(fact_id)s AND transaction_end IS NULL
            RETURNING user_id, subject, predicate, object, transaction_start
            """,
            {"fact_id": fact_id},
        )
        row = cursor.fetchone()

        if row is None:
            cursor.execute("ROLLBACK")
            raise ValueError(f"No active belief found for fact_id={fact_id}")

        user_id, subject, predicate, object_, transaction_start = row

        cursor.execute(
            """
            INSERT INTO belief_audit_trail
                (user_id, fact_id, subject, predicate, object,
                 transaction_start, transaction_end, adjudication_reason, judge_model)
            VALUES
                (%(user_id)s, %(fact_id)s, %(subject)s, %(predicate)s, %(object)s,
                 %(transaction_start)s, CURRENT_TIMESTAMP, %(reason)s, %(judge_model)s)
            """,
            {
                "user_id": user_id,
                "fact_id": fact_id,
                "subject": subject,
                "predicate": predicate,
                "object": object_,
                "transaction_start": transaction_start,
                "reason": reason,
                "judge_model": JUDGE_MODEL,
            },
        )

        cursor.execute("COMMIT")

    except Exception:
        cursor.execute("ROLLBACK")
        raise
