from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from dataclasses import dataclass, field
from time import perf_counter
from threading import Lock, Thread
from typing import Any, Iterator
from uuid import uuid4


_run_id_var: ContextVar[str | None] = ContextVar("run_id", default=None)
_graph_name_var: ContextVar[str | None] = ContextVar("graph_name", default=None)
_node_name_var: ContextVar[str | None] = ContextVar("node_name", default=None)
_persistence_module_var: ContextVar[str | None] = ContextVar("persistence_module", default=None)
_summary_var: ContextVar["ExecutionSummary | None"] = ContextVar("summary", default=None)
_graph_depth_var: ContextVar[int] = ContextVar("graph_depth", default=0)


@dataclass(slots=True)
class ExecutionSummary:
    run_id: str
    started_at: float
    graphs: set[str] = field(default_factory=set)
    node_counts: Counter[str] = field(default_factory=Counter)
    db_queries: int = 0
    db_operations: Counter[str] = field(default_factory=Counter)
    db_rows_returned: int = 0
    db_rows_affected: int = 0
    db_duration_ms: float = 0.0
    embedding_calls: int = 0
    embedding_duration_ms: float = 0.0
    retrieval_calls: int = 0
    retrieval_duration_ms: float = 0.0
    semantic_candidates: int = 0
    episodic_candidates: int = 0
    semantic_top_k: int = 0
    episodic_top_k: int = 0
    packed_context_size: int = 0
    validated_context_size: int = 0
    llm_calls: int = 0
    llm_latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float | None = None
    semantic_inserted: int = 0
    semantic_updated: int = 0
    semantic_ignored: int = 0
    semantic_merged: int = 0
    semantic_superseded: int = 0
    episodic_inserted: int = 0
    episodic_reactivated: int = 0
    episodic_updated: int = 0
    stag_edges: int = 0
    tombstones: int = 0
    gists_written: int = 0
    scheduler_errors: int = 0
    items_processed: int = 0
    lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    def as_dict(self) -> dict[str, Any]:
        with self.lock:
            return {
                "run_id": self.run_id,
                "runtime_ms": int((perf_counter() - self.started_at) * 1000),
                "graphs": sorted(self.graphs),
                "node_counts": dict(self.node_counts),
                "db_queries": self.db_queries,
                "db_operations": dict(self.db_operations),
                "db_rows_returned": self.db_rows_returned,
                "db_rows_affected": self.db_rows_affected,
                "db_duration_ms": int(self.db_duration_ms),
                "embedding_calls": self.embedding_calls,
                "embedding_duration_ms": int(self.embedding_duration_ms),
                "retrieval_calls": self.retrieval_calls,
                "retrieval_duration_ms": int(self.retrieval_duration_ms),
                "semantic_candidates": self.semantic_candidates,
                "episodic_candidates": self.episodic_candidates,
                "semantic_top_k": self.semantic_top_k,
                "episodic_top_k": self.episodic_top_k,
                "packed_context_size": self.packed_context_size,
                "validated_context_size": self.validated_context_size,
                "llm_calls": self.llm_calls,
                "llm_latency_ms": int(self.llm_latency_ms),
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens,
                "cost_usd": self.cost_usd,
                "semantic_inserted": self.semantic_inserted,
                "semantic_updated": self.semantic_updated,
                "semantic_ignored": self.semantic_ignored,
                "semantic_merged": self.semantic_merged,
                "semantic_superseded": self.semantic_superseded,
                "episodic_inserted": self.episodic_inserted,
                "episodic_reactivated": self.episodic_reactivated,
                "episodic_updated": self.episodic_updated,
                "stag_edges": self.stag_edges,
                "tombstones": self.tombstones,
                "gists_written": self.gists_written,
                "scheduler_errors": self.scheduler_errors,
                "items_processed": self.items_processed,
            }

    def format_block(self) -> str:
        data = self.as_dict()
        graphs = data.get("graphs", [])
        semantic_inserted = data.get("semantic_inserted", 0)
        semantic_updated = data.get("semantic_updated", 0)
        semantic_ignored = data.get("semantic_ignored", 0)
        episodic_inserted = data.get("episodic_inserted", 0)
        episodic_reactivated = data.get("episodic_reactivated", 0)
        episodic_updated = data.get("episodic_updated", 0)
        lines = [
            "================ EXECUTION SUMMARY ================",
            "",
            f"Run ID: {data['run_id']}",
            f"Total Runtime: {data['runtime_ms']} ms",
            "",
            "----------------------------------------",
            "",
            "Graphs Executed",
        ]
        if graphs:
            lines.extend(f"✓ {graph_name}" for graph_name in graphs)
        else:
            lines.append("(none)")
        lines.extend([
            "",
            "----------------------------------------",
            "",
            "Semantic Memory",
            f"Inserted: {semantic_inserted}",
            f"Updated: {semantic_updated}",
            f"Ignored: {semantic_ignored}",
            "",
            "----------------------------------------",
            "",
            "Episodic Memory",
            f"Inserted: {episodic_inserted}",
            f"Reactivated: {episodic_reactivated}",
            f"Updated: {episodic_updated}",
            "",
            "----------------------------------------",
            "",
            "Retrieval",
            f"Semantic Retrieved: {data.get('semantic_candidates', 0)}",
            f"Episodic Retrieved: {data.get('episodic_candidates', 0)}",
            f"Packed Context: {data.get('packed_context_size', 0)}",
            f"Validated Context: {data.get('validated_context_size', 0)}",
            "",
            "----------------------------------------",
            "",
            "LLM",
            f"Calls: {data.get('llm_calls', 0)}",
            f"Latency: {data.get('llm_latency_ms', 0)} ms",
            f"Total Tokens: {data.get('total_tokens', 0)}",
            "",
            "----------------------------------------",
            "",
            "Database",
            f"Queries: {data.get('db_queries', 0)}",
            f"Rows Returned: {data.get('db_rows_returned', 0)}",
            f"Rows Affected: {data.get('db_rows_affected', 0)}",
            f"Total DB Time: {data.get('db_duration_ms', 0)} ms",
            "",
            "===================================================",
        ])
        return "\n".join(lines)


def ensure_run_context(run_id: str | None = None) -> str:
    existing = _run_id_var.get()
    if existing:
        return existing

    generated = run_id or str(uuid4())
    _run_id_var.set(generated)
    if _summary_var.get() is None:
        _summary_var.set(ExecutionSummary(run_id=generated, started_at=perf_counter()))
    return generated


def get_run_context() -> dict[str, Any]:
    summary = _summary_var.get()
    return {
        "run_id": _run_id_var.get(),
        "graph_name": _graph_name_var.get(),
        "node_name": _node_name_var.get(),
        "persistence_module": _persistence_module_var.get(),
        "graph_depth": _graph_depth_var.get(),
        "summary": summary.as_dict() if summary else None,
    }


@contextmanager
def bind_run_context(
    *,
    run_id: str | None = None,
    graph_name: str | None = None,
    node_name: str | None = None,
    persistence_module: str | None = None,
) -> Iterator[str]:
    bound_run_id = ensure_run_context(run_id)
    run_token = _run_id_var.set(bound_run_id)
    graph_token = _graph_name_var.set(graph_name)
    node_token = _node_name_var.set(node_name)
    module_token = _persistence_module_var.set(persistence_module)
    try:
        yield bound_run_id
    finally:
        _persistence_module_var.reset(module_token)
        _node_name_var.reset(node_token)
        _graph_name_var.reset(graph_token)
        _run_id_var.reset(run_token)


@contextmanager
def graph_scope(graph_name: str, *, run_id: str | None = None) -> Iterator[str]:
    summary = _summary_var.get()
    if summary is None:
        summary = ExecutionSummary(run_id=ensure_run_context(run_id), started_at=perf_counter())
        _summary_var.set(summary)

    if run_id is not None:
        _run_id_var.set(run_id)
        summary.run_id = run_id
    else:
        ensure_run_context()

    graph_token = _graph_name_var.set(graph_name)
    depth_token = _graph_depth_var.set(_graph_depth_var.get() + 1)
    summary.graphs.add(graph_name)
    try:
        yield summary.run_id
    finally:
        _graph_depth_var.reset(depth_token)
        _graph_name_var.reset(graph_token)


@contextmanager
def node_scope(node_name: str) -> Iterator[str | None]:
    node_token = _node_name_var.set(node_name)
    summary = _summary_var.get()
    if summary is not None:
        with summary.lock:
            summary.node_counts[node_name] += 1
    try:
        yield node_name
    finally:
        _node_name_var.reset(node_token)


def current_summary() -> ExecutionSummary | None:
    return _summary_var.get()


def reset_run_summary() -> None:
    _summary_var.set(None)


def emit_execution_summary(logger: Any) -> None:
    summary = _summary_var.get()
    if summary is None:
        return

    payload = summary.as_dict()
    logger.info(
        summary.format_block(),
        extra={"summary": payload, "summary_display": summary.format_block()},
    )
    reset_run_summary()


def _update_summary(mutator: Any) -> None:
    summary = _summary_var.get()
    if summary is None:
        return
    with summary.lock:
        mutator(summary)


def record_database_query(
    *,
    operation: str,
    table: str | None,
    duration_ms: int,
    rows_returned: int | None = None,
    rows_affected: int | None = None,
    success: bool = True,
    persistence_module: str | None = None,
    status: str | None = None,
) -> None:
    def mutator(summary: ExecutionSummary) -> None:
        summary.db_queries += 1
        summary.db_operations[operation] += 1
        summary.db_duration_ms += duration_ms
        if rows_returned is not None:
            summary.db_rows_returned += max(rows_returned, 0)
        if rows_affected is not None:
            summary.db_rows_affected += max(rows_affected, 0)

    _update_summary(mutator)


def record_embedding_call(*, duration_ms: int) -> None:
    def mutator(summary: ExecutionSummary) -> None:
        summary.embedding_calls += 1
        summary.embedding_duration_ms += duration_ms

    _update_summary(mutator)


def record_llm_call(
    *,
    duration_ms: int,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    cost_usd: float | None = None,
) -> None:
    def mutator(summary: ExecutionSummary) -> None:
        summary.llm_calls += 1
        summary.llm_latency_ms += duration_ms
        if prompt_tokens is not None:
            summary.prompt_tokens += prompt_tokens
        if completion_tokens is not None:
            summary.completion_tokens += completion_tokens
        if total_tokens is not None:
            summary.total_tokens += total_tokens
        if cost_usd is not None:
            summary.cost_usd = (summary.cost_usd or 0.0) + cost_usd

    _update_summary(mutator)


def record_retrieval_event(
    *,
    duration_ms: int,
    semantic_candidates: int = 0,
    episodic_candidates: int = 0,
    semantic_top_k: int = 0,
    episodic_top_k: int = 0,
    packed_context_size: int = 0,
    validated_context_size: int = 0,
) -> None:
    def mutator(summary: ExecutionSummary) -> None:
        summary.retrieval_calls += 1
        summary.retrieval_duration_ms += duration_ms
        summary.semantic_candidates += semantic_candidates
        summary.episodic_candidates += episodic_candidates
        summary.semantic_top_k += semantic_top_k
        summary.episodic_top_k += episodic_top_k
        summary.packed_context_size += packed_context_size
        summary.validated_context_size += validated_context_size

    _update_summary(mutator)


def record_memory_event(**values: int) -> None:
    def mutator(summary: ExecutionSummary) -> None:
        for key, value in values.items():
            if hasattr(summary, key):
                current_value = getattr(summary, key)
                if isinstance(current_value, int):
                    setattr(summary, key, current_value + int(value))

    _update_summary(mutator)


def spawn_background_task(target: Any, *args: Any, name: str | None = None, daemon: bool = True, inherit_context: bool = True, **kwargs: Any) -> Thread:
    ctx = copy_context() if inherit_context else None

    def runner() -> None:
        if ctx is None:
            target(*args, **kwargs)
        else:
            ctx.run(target, *args, **kwargs)

    thread = Thread(target=runner, name=name, daemon=daemon)
    thread.start()
    return thread


def run_id_or_new() -> str:
    return ensure_run_context()
