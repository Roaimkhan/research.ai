from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import config
from src.prompts import SYSTEM_ADJUDICATION_PROMPT
from src.schemas import AdjudicatedMemoryList, SemanticBufferConsolidatorState, MemoryRecord, MemoryBatch
from src.memory import conn


llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=config.GOOGLE_API_KEY)
structured_llm = llm.with_structured_output(AdjudicatedMemoryList)


def _normalize_adjudication_response(response):
    if response is None:
        return []
    if isinstance(response, AdjudicatedMemoryList):
        return response.memories
    if isinstance(response, list):
        return response
    if hasattr(response, "memories"):
        return list(response.memories)
    raise TypeError("Unexpected adjudication response type: %r" % type(response))


def ajudication_gate(state: SemanticBufferConsolidatorState)->SemanticBufferConsolidatorState:
    user_id = state["snapshot"].user_id

    adjudicated_memories = AdjudicatedMemoryList()
    fresh_memories = MemoryBatch()

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT fact_id, subject, predicate, object,
                   valid_start, valid_end, provenance_uri, confidence_score
            FROM staging_buffer
            WHERE consolidated = FALSE
              AND user_id = %s;
            """,
            (user_id,),
        )

        rows = cursor.fetchall()

        if not rows:
            return {
                "adjudicated_memories": adjudicated_memories,
                "fresh_memories": fresh_memories,
            }

        colnames = [desc[0] for desc in cursor.description]

        staging_memories = [
            MemoryRecord.parse_obj(dict(zip(colnames, row)))
            for row in rows
        ]

        adjudication_candidates = []

        for memory in staging_memories:
            cursor.execute(
                """
                SELECT fact_id, object
                FROM active_beliefs
                WHERE predicate = %s
                  AND subject = %s
                  AND user_id = %s
                  AND transaction_end IS NULL;
                """,
                (
                    memory.predicate,
                    memory.subject,
                    user_id,
                ),
            )

            similar_rows = cursor.fetchall()

            if not similar_rows:
                fresh_memories.memmories.append(memory)
                continue

            belief_columns = [desc[0] for desc in cursor.description]

            similar_memories = [
                dict(zip(belief_columns, row))
                for row in similar_rows
            ]

            adjudication_candidates.append(
                {
                    "new_memory": memory.model_dump(),
                    "existing_memories": similar_memories,
                }
            )

        BATCH_SIZE = 5

        batches = [
            adjudication_candidates[i:i + BATCH_SIZE]
            for i in range(0, len(adjudication_candidates), BATCH_SIZE)
        ]

    for batch in batches:
        response = structured_llm.invoke(
                [
                    SystemMessage(content=SYSTEM_ADJUDICATION_PROMPT),
                    HumanMessage(
                        content=f"""
                        Adjudicate the following memory candidates.
                        {batch}
                        """
                    ),
                ]
            )

        adjudicated_memories.memories.extend(
            _normalize_adjudication_response(response)
        )

    return {
        "fresh_memories": fresh_memories,
        "adjudicated_memories": adjudicated_memories,
    }
