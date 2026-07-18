from pydantic import BaseModel, Field
from .extraction_schemas import MemoryRecord
from typing import Literal

class AdjudicatedMemoryItem(BaseModel):
    memory: MemoryRecord

    action: Literal["ADD", "REPLACE", "IGNORE", "CONTRADICT"] = Field(
        description=(
            "The adjudication decision for the incoming memory. "
            "'ADD' if it is a new fact,"
            " 'REPLACE' if it supersedes existing fact(s), "
            "'IGNORE' if it duplicates an existing fact, "
            "'CONTRADICT' if it conflicts "
            "with existing fact(s) without replacing them."
        )
    )

    target_fact_ids: list[str] = Field(
        default_factory=list,
        description=(
            "The fact_id(s) of the existing memory records affected by this decision. "
            "Populate this field for REPLACE, IGNORE, and CONTRADICT by listing the relevant "
            "existing fact_id(s). Leave it empty for ADD."
        )
    )

class AdjudicatedMemoryList(BaseModel):
    memories: list[AdjudicatedMemoryItem] = Field(
        description="A list of adjudicated memory items. Each item contains the incoming memory, the adjudication action, and any affected existing fact IDs."
    )