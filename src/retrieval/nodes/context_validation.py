from __future__ import annotations

import logging

from src.persistence import semantic_store
from src.schemas import RetrievalState
from src.retrieval.config import CONTEXT_TOKEN_BUDGET
from src.retrieval.token_utils import approximate_token_count
from src.logging import get_logger

logger = get_logger(__name__)


def _item_identity(item: dict) -> tuple[str, object] | None:
    source = item.get("source")
    if source == "semantic" and item.get("fact_id") is not None:
        return "semantic", item["fact_id"]
    if source == "episodic" and item.get("gist_id") is not None:
        return "episodic", item["gist_id"]

    # Defensive fallback if source tag is missing.
    if item.get("fact_id") is not None:
        return "semantic", item["fact_id"]
    if item.get("gist_id") is not None:
        return "episodic", item["gist_id"]
    return None


def context_validation_node(state: RetrievalState) -> RetrievalState:
    try:
        packed_context = state.get("packed_context", [])

        # 1) DEDUPE by IDs only, preserving original order.
        seen_ids: set[tuple[str, object]] = set()
        deduped_results: list[dict] = []
        for item in packed_context:
            identity = _item_identity(item)
            if identity is None:
                logger.warning(
                    "Context validation received an item with no fact_id or gist_id. "
                    "This violates retrieval invariants."
                )

                state.setdefault("errors", []).append(
                    {
                        "stage": "context_validation",
                        "message": "Retrieved item missing both fact_id and gist_id.",
                    }
                )

                deduped_results.append(item)
                continue
            
            if identity in seen_ids:
                continue
            seen_ids.add(identity)
            deduped_results.append(item)

        # 2) FILTER SUPERSEDED PROVISIONAL SEMANTIC FACTS
        after_supersede_filter: list[dict] = []
        for item in deduped_results:
            try:
                if (
                    item.get("source") == "semantic"
                    and item.get("provisional") is True
                ):
                    if semantic_store.check_if_superseded(
                        subject=item["subject"],
                        predicate=item["predicate"],
                        as_of_valid_start=item["valid_start"],
                    ):
                        continue

                after_supersede_filter.append(item)

            except Exception as exc:
                logger.exception(
                    "Failed validating semantic item: fact_id=%s",
                    item.get("fact_id"),
                )

                state.setdefault("errors", []).append(
                    {
                        "stage": "context_validation",
                        "fact_id": item.get("fact_id"),
                        "message": str(exc),
                    }
                )

        # 3) DEFENSIVE EPISODIC VALIDATION
        validated_results: list[dict] = []
        for item in after_supersede_filter:
            try:
                if item.get("source") == "episodic":
                    if item.get("is_active") is False or item.get("gist_embedding") is None:
                        logger.warning(
                            "Dropping episodic item during context validation due to invalid retrieval invariants: gist_id=%s",
                            item.get("gist_id"),
                        )
                        continue
                validated_results.append(item)
            except Exception as exc:
                logger.exception(
                    "Failed validating semantic item: fact_id=%s",
                    item.get("fact_id"),
                )

                state.setdefault("errors", []).append(
                    {
                        "stage": "context_validation",
                        "fact_id": item.get("fact_id"),
                        "message": str(exc),
                    }
                )

        # 4) CONTRADICTION CHECK (semantic items only)
        semantic_objects_by_key: dict[tuple[str, str], set[str]] = {}
        for item in validated_results:
            if item.get("source") != "semantic":
                continue
            key = (str(item.get("subject")), str(item.get("predicate")))
            semantic_objects_by_key.setdefault(key, set()).add(str(item.get("object")))

        context_notes: list[str] = []
        for (subject, predicate), objects in semantic_objects_by_key.items():
            if len(objects) > 1:
                context_notes.append(
                    f"Conflicting information exists for (subject='{subject}', predicate='{predicate}')."
                )
        state["context_notes"] = context_notes

        # 5) FINAL TOKEN-BUDGET ASSERTION
        #
        # The Context Packer is the single source of truth for token counting.
        # If it has already populated packed_token_count, verify it stayed within
        # the configured budget. This should normally never fail.

        packed_token_count = state.get("packed_token_count")

        if packed_token_count is not None:
            from src.retrieval.config import CONTEXT_TOKEN_BUDGET

            if packed_token_count > CONTEXT_TOKEN_BUDGET:
                logger.warning(
                    "Context Packer exceeded CONTEXT_TOKEN_BUDGET "
                    "(packed=%s, budget=%s). "
                    "This indicates a bug in the packing logic.",
                    packed_token_count,
                    CONTEXT_TOKEN_BUDGET,
                )

                state.setdefault("errors", []).append(
                    {
                        "stage": "context_validation",
                        "message": (
                            "Context Packer exceeded CONTEXT_TOKEN_BUDGET."
                        ),
                    }
                )

        # 6) OUTPUT
        state["validated_context"] = validated_results
        
        # Log dropout metrics for demo
        try:
            packed_size = len(state.get("packed_context", []))
            logger.info(
                "Context validation: %d packed → %d validated",
                packed_size,
                len(validated_results),
                extra={"packed": packed_size, "validated": len(validated_results)}
            )
        except Exception:
            pass
        return state

    except Exception as exc:
        state.setdefault("errors", []).append(
            {
                "stage": "context_validation",
                "message": str(exc),
            }
        )
        state["validated_context"] = []
        return state
