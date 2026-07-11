from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from mcp.server.fastmcp import FastMCP

from src.telemetry import summarize


@dataclass
class MemoryRecord:
    memory_id: str
    fact: str
    entity_tags: list[str]
    memory_type: str
    confidence: float
    decay_score: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@runtime_checkable
class MemoryBackend(Protocol):
    def add_memory(self, fact: str, entity_tags: list[str], memory_type: str, confidence: float) -> dict[str, Any]:
        ...

    def search_memory(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        ...

    def update_memory(self, memory_id: str, fact: str, confidence: float) -> dict[str, Any]:
        ...

    def delete_memory(self, memory_id: str, reason: str) -> dict[str, Any]:
        ...

    def recent_memories(self, limit: int = 20) -> list[dict[str, Any]]:
        ...

    def stats(self) -> dict[str, Any]:
        ...

    def memories_for_entity(self, tag: str) -> list[dict[str, Any]]:
        ...


class MemoryBackendABC(ABC):
    @abstractmethod
    def add_memory(self, fact: str, entity_tags: list[str], memory_type: str, confidence: float) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def search_memory(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def update_memory(self, memory_id: str, fact: str, confidence: float) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete_memory(self, memory_id: str, reason: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def recent_memories(self, limit: int = 20) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def memories_for_entity(self, tag: str) -> list[dict[str, Any]]:
        raise NotImplementedError


class MockMemoryBackend(MemoryBackendABC):
    def __init__(self) -> None:
        self._memories: dict[str, MemoryRecord] = {}
        self._counter = 0

    def add_memory(self, fact: str, entity_tags: list[str], memory_type: str, confidence: float) -> dict[str, Any]:
        self._counter += 1
        memory_id = f"mem_{self._counter}"
        record = MemoryRecord(
            memory_id=memory_id,
            fact=fact,
            entity_tags=list(entity_tags),
            memory_type=memory_type,
            confidence=confidence,
            decay_score=max(0.0, 1.0 - confidence),
        )
        self._memories[memory_id] = record
        return self._to_dict(record)

    def search_memory(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        lowered_query = query.lower()
        matches = [
            self._to_dict(record)
            for record in self._memories.values()
            if lowered_query in record.fact.lower()
            or any(lowered_query in tag.lower() for tag in record.entity_tags)
            or lowered_query in record.memory_type.lower()
        ]
        return matches[:top_k]

    def update_memory(self, memory_id: str, fact: str, confidence: float) -> dict[str, Any]:
        record = self._require_memory(memory_id)
        record.fact = fact
        record.confidence = confidence
        record.decay_score = max(0.0, 1.0 - confidence)
        record.updated_at = datetime.now(timezone.utc).isoformat()
        return self._to_dict(record)

    def delete_memory(self, memory_id: str, reason: str) -> dict[str, Any]:
        record = self._require_memory(memory_id)
        deleted = self._to_dict(record)
        deleted["deleted_reason"] = reason
        del self._memories[memory_id]
        return deleted

    def recent_memories(self, limit: int = 20) -> list[dict[str, Any]]:
        records = list(self._memories.values())[-limit:]
        return [self._to_dict(record) for record in records]

    def stats(self) -> dict[str, Any]:
        memories = list(self._memories.values())
        count_by_type: dict[str, int] = {}
        total_decay = 0.0
        for record in memories:
            count_by_type[record.memory_type] = count_by_type.get(record.memory_type, 0) + 1
            total_decay += record.decay_score

        average_decay_score = total_decay / len(memories) if memories else 0.0
        return {
            "total_memories": len(memories),
            "count_by_type": count_by_type,
            "average_decay_score": average_decay_score,
            "healthy": len(memories) > 0,
        }

    def memories_for_entity(self, tag: str) -> list[dict[str, Any]]:
        lowered_tag = tag.lower()
        return [
            self._to_dict(record)
            for record in self._memories.values()
            if any(lowered_tag == entity.lower() for entity in record.entity_tags)
        ]

    def _require_memory(self, memory_id: str) -> MemoryRecord:
        if memory_id not in self._memories:
            raise KeyError(f"Memory '{memory_id}' not found.")
        return self._memories[memory_id]

    def _to_dict(self, record: MemoryRecord) -> dict[str, Any]:
        return {
            "memory_id": record.memory_id,
            "fact": record.fact,
            "entity_tags": list(record.entity_tags),
            "memory_type": record.memory_type,
            "confidence": record.confidence,
            "decay_score": record.decay_score,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }


def create_server(backend: MemoryBackend) -> FastMCP:
    mcp = FastMCP("memory-server")

    @mcp.tool()
    def add_memory(fact: str, entity_tags: list[str], memory_type: str, confidence: float) -> dict[str, Any]:
        """Call when the user states a new fact, preference, or event worth remembering."""
        try:
            return backend.add_memory(fact, entity_tags, memory_type, confidence)
        except Exception as error:
            return {"error": str(error)}

    @mcp.tool()
    def search_memory(query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Call when the user asks to recall or find stored memories relevant to a query."""
        try:
            return backend.search_memory(query, top_k)
        except Exception as error:
            return [{"error": str(error)}]

    @mcp.tool()
    def update_memory(memory_id: str, fact: str, confidence: float) -> dict[str, Any]:
        """Call when an existing memory should be corrected, refined, or superseded with newer information."""
        try:
            return backend.update_memory(memory_id, fact, confidence)
        except Exception as error:
            return {"error": str(error)}

    @mcp.tool()
    def delete_memory(memory_id: str, reason: str) -> dict[str, Any]:
        """Call only when the user explicitly requests removal of a memory or when a memory must be deleted for safety, privacy, or obvious obsolescence."""
        try:
            return backend.delete_memory(memory_id, reason)
        except Exception as error:
            return {"error": str(error)}

    @mcp.resource("memory://recent")
    def recent_memories() -> str:
        """Last 20 memories as JSON."""
        try:
            return json.dumps(backend.recent_memories(limit=20), ensure_ascii=False)
        except Exception as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)

    @mcp.resource("memory://stats")
    def stats() -> str:
        """Counts by memory_type plus average decay_score, as a live health view."""
        try:
            return json.dumps(backend.stats(), ensure_ascii=False)
        except Exception as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)

    @mcp.resource("memory://telemetry")
    def telemetry() -> str:
        """Telemetry summary for live routing and execution health."""
        return json.dumps(summarize(), ensure_ascii=False)

    @mcp.resource("memory://entity/{tag}")
    def entity_memories(tag: str) -> str:
        """All memories linked to the requested entity tag."""
        try:
            return json.dumps(backend.memories_for_entity(tag), ensure_ascii=False)
        except Exception as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)

    return mcp


if __name__ == "__main__":
    create_server(MockMemoryBackend()).run()