from __future__ import annotations

import inspect
import time
from functools import wraps
from typing import Any, Callable, Mapping

from .context import (
    ensure_run_context,
    emit_execution_summary,
    graph_scope,
    node_scope,
)
from .logger import get_logger


logger = get_logger(__name__)


def _summarize_state(state: Any) -> Any:
    if not isinstance(state, Mapping):
        return type(state).__name__

    summary: dict[str, Any] = {"keys": sorted(state.keys())[:12]}
    for key in ("messages", "validated_context", "packed_context", "semantic_results", "episodic_results", "errors", "written_gist_ids"):
        value = state.get(key)
        if hasattr(value, "__len__"):
            summary[key] = len(value)  # type: ignore[arg-type]
    return summary


def log_node(function: Callable[..., Any] | None = None, *, node_name: str | None = None) -> Callable[..., Any]:
    def decorator(target: Callable[..., Any]) -> Callable[..., Any]:
        resolved_name = node_name or getattr(target, "__name__", "node")

        if inspect.iscoroutinefunction(target):

            @wraps(target)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                ensure_run_context()
                state = args[0] if args else kwargs.get("state")
                started_at = time.perf_counter()
                with node_scope(resolved_name):
                    logger.info("Node started", extra={"state_summary": _summarize_state(state)})
                    try:
                        result = await target(*args, **kwargs)
                    except Exception:
                        logger.exception("Node failed", extra={"state_summary": _summarize_state(state)})
                        raise
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                logger.info("Node finished", extra={"duration_ms": duration_ms, "state_summary": _summarize_state(result)})
                return result

            return async_wrapper

        @wraps(target)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            ensure_run_context()
            state = args[0] if args else kwargs.get("state")
            started_at = time.perf_counter()
            with node_scope(resolved_name):
                try:
                    logger.debug("Node started", extra={"state_summary": _summarize_state(state)})
                except Exception:
                    pass  # Never let logging crash the node
                try:
                    result = target(*args, **kwargs)
                except Exception:
                    duration_ms = int((time.perf_counter() - started_at) * 1000)
                    try:
                        logger.error("Node failed", extra={"duration_ms": duration_ms, "state_summary": _summarize_state(state)}, exc_info=True)
                    except Exception:
                        pass  # Never let logging crash the error handler
                    raise
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            try:
                logger.info("✓ %s: %d ms", resolved_name, duration_ms, extra={"duration_ms": duration_ms})
            except Exception:
                pass  # Never let logging crash the node finish
            return result

        return sync_wrapper

    if function is not None:
        return decorator(function)
    return decorator


class _ObservedGraph:
    def __init__(self, graph: Any, graph_name: str) -> None:
        self._graph = graph
        self._graph_name = graph_name

    def invoke(self, state: Any, *args: Any, **kwargs: Any) -> Any:
        run_id = ensure_run_context(getattr(getattr(state, "get", lambda *_: None)("requestcontext", None), "run_id", None))
        started_at = time.perf_counter()
        try:
            logger.info("Graph '%s' starting", self._graph_name)
        except Exception:
            pass  # Never let logging crash the graph
        with graph_scope(self._graph_name, run_id=run_id):
            try:
                result = self._graph.invoke(state, *args, **kwargs)
            except Exception:
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                try:
                    logger.error("Graph '%s' FAILED after %d ms", self._graph_name, duration_ms, exc_info=True)
                except Exception:
                    pass  # Never let logging crash the error handler
                raise
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        try:
            logger.info("✓ Graph '%s' completed in %d ms", self._graph_name, duration_ms)
        except Exception:
            pass  # Never let logging crash the finish
        try:
            emit_execution_summary(logger)
        except Exception:
            pass  # Never let summary crash the graph
        return result

    async def ainvoke(self, state: Any, *args: Any, **kwargs: Any) -> Any:
        run_id = ensure_run_context(getattr(getattr(state, "get", lambda *_: None)("requestcontext", None), "run_id", None))
        started_at = time.perf_counter()
        logger.info("Graph started", extra={"graph_name": self._graph_name, "state_summary": _summarize_state(state)})
        with graph_scope(self._graph_name, run_id=run_id):
            try:
                result = await self._graph.ainvoke(state, *args, **kwargs)
            except Exception:
                logger.exception("Graph failed", extra={"graph_name": self._graph_name, "state_summary": _summarize_state(state)})
                raise
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info("Graph finished", extra={"graph_name": self._graph_name, "duration_ms": duration_ms, "state_summary": _summarize_state(result)})
        emit_execution_summary(logger)
        return result

    def __getattr__(self, item: str) -> Any:
        return getattr(self._graph, item)


def log_graph(graph: Any | None = None, *, graph_name: str | None = None) -> Any:
    if graph is None:
        return lambda target: log_graph(target, graph_name=graph_name)
    resolved_name = graph_name or getattr(graph, "name", None) or getattr(graph, "__class__", type(graph)).__name__
    return _ObservedGraph(graph, resolved_name)


def track_call(call_type: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(function):

            @wraps(function)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                ensure_run_context()
                started_at = time.perf_counter()
                try:
                    return await function(*args, **kwargs)
                finally:
                    logger.info(call_type, extra={"duration_ms": int((time.perf_counter() - started_at) * 1000)})

            return async_wrapper

        @wraps(function)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            ensure_run_context()
            started_at = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                logger.info(call_type, extra={"duration_ms": int((time.perf_counter() - started_at) * 1000)})

        return sync_wrapper

    return decorator
