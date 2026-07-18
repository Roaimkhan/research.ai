from src.memory import conn 
from src.schemas import SemanticBufferConsolidatorState, MemoryRecord
from src.consolidation import embed_text
cursor = conn.cursor()



JUDGE_MODEL = "gemini-2.5-pro"  


def bitemporal_split(state: SemanticBufferConsolidatorState):
    memories_list = state.adjudicated_memories
    user_id = state.snapshot.user_id

    for item in memories_list.memories:
        action = item.action
        record = item.memory

        if action == "IGNORE":
            continue

        embedding = embed_text(f"{record.subject} {record.predicate} {record.object}")

        if action == "ADD":
            _insert_new_belief(record, user_id, embedding)

        elif action == "REPLACE":
            for old_fact_id in item.target_fact_ids:
                _retract_and_audit(
                    fact_id=old_fact_id,
                    reason=item.adjudication_reason or "Superseded by newer fact.",
                )
            _insert_new_belief(record, user_id, embedding)

        elif action == "CONTRADICT":
            for old_fact_id in item.target_fact_ids:
                _retract_and_audit(
                    fact_id=old_fact_id,
                    reason=item.adjudication_reason or "Contradicted by conflicting fact.",
                )
            _insert_new_belief(record, user_id, embedding)

        else:
            raise ValueError(f"Unknown adjudication action: {action}")

    return state


def _insert_new_belief(record: MemoryRecord, user_id: str, embedding: list[float]):
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


def _retract_and_audit(fact_id: str, reason: str):
    """
    Closes transaction-time on the losing fact and moves it atomically
    into belief_audit_trail with a signed judge verdict.
    Must run in a single transaction — audit move without close, or
    close without audit, both break replay consistency.
    """
    cursor.execute("BEGIN")
    try:
        # 1. Close transaction-time on the active row
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
            # Nothing active to retract — already closed or doesn't exist.
            # Don't silently continue; this indicates a race or bad fact_id.
            cursor.execute("ROLLBACK")
            raise ValueError(f"No active belief found for fact_id={fact_id}")

        user_id, subject, predicate, object_, transaction_start = row

        # 2. Write the audit record — this is the permanent verdict log
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
