# Production-Grade Logging, Tracing & Database Observability System

## Overview

This document describes the unified logging and observability system integrated into the LangGraph-based AI agent. The system provides:

- **Centralized run context** via context variables (run_id propagated across graphs, nodes, and background tasks)
- **Structured logging** with JSON output for log aggregation
- **Colored console output** for human-readable development/debugging
- **Automatic graph & node lifecycle logging** via decorators
- **Database observability** via transparent connection wrappers
- **Transparent LLM call tracking** with token counts and latency
- **Embedding operation tracking**
- **End-of-run execution summaries** for comprehensive analysis
- **Future compatibility** with OpenTelemetry, Grafana, Prometheus, ELK, Jaeger

## Configuration

Set environment variables in your `.env` file:

```bash
# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Directory for log files (defaults to ./logs)
LOG_DIR=logs

# Rotating file handler: max bytes per file (10 MB default)
LOG_MAX_BYTES=10485760

# Rotating file handler: number of backup files to keep
LOG_BACKUP_COUNT=5

# Slow query warning threshold in milliseconds
SLOW_QUERY_WARNING_MS=100
```

## Architecture

### Core Components

#### 1. **Context Module** (`src/logging/context.py`)

Manages execution context across async/threaded boundaries using `contextvars`:

```python
from src.logging.context import (
    ensure_run_context,           # Get or create run_id
    bind_run_context,             # Context manager for run_id + metadata
    graph_scope,                  # Track graph entry/exit
    node_scope,                   # Track node entry/exit
    current_summary,              # Get the current ExecutionSummary
    record_database_query,        # Log a database operation
    record_embedding_call,        # Log an embedding operation
    record_llm_call,              # Log an LLM call
    record_retrieval_event,       # Log retrieval stats
    record_memory_event,          # Log memory pipeline events
    spawn_background_task,        # Spawn thread with inherited context
)
```

**ExecutionSummary** accumulates all metrics across a run and formats them into a summary block at completion.

#### 2. **Logger Module** (`src/logging/logger.py`)

Configures the Python logging system:

- Console handler with colored output and compact format
- File handler (JSON) for log aggregation to `logs/latest.log`
- Error handler (JSON) for errors only to `logs/latest-error.log`
- Rotating file handlers with configurable retention

```python
from src.logging import configure_logging, get_logger

configure_logging()  # Call once at startup
logger = get_logger(__name__)
logger.info("Message", extra={"key": "value"})
```

#### 3. **Decorators Module** (`src/logging/decorators.py`)

Automatic lifecycle logging for graphs and nodes:

```python
from src.logging.decorators import log_node, log_graph

# Wrap a node
@log_node(node_name="my_node")
def my_node_func(state):
    return state

# Or wrap nodes when adding to graph
graph.add_node("my_node", log_node(my_node_func, node_name="my_node"))

# Wrap a compiled graph
compiled_graph = log_graph(graph.compile(), graph_name="MyGraph")
```

Each node logs: `started`, `duration`, `finished`, or `failed`.
Each graph logs: `started`, `duration`, `finished`, or `failed`, plus execution summary at completion.

#### 4. **Database Instrumentation Module** (`src/logging/db.py`)

Transparent wrapper around psycopg connections and cursors:

```python
from src.logging.db import instrument_connection, instrument_connection_pool

# Single connection
from src.persistence.semantic_store import conn  # Already instrumented

# Connection pool
from src.persistence.semantic_staging_buffer import pool  # Already instrumented
```

**Automatic logging:**
- SQL operation (SELECT, INSERT, UPDATE, DELETE, UPSERT, BEGIN, COMMIT, ROLLBACK)
- Table name
- Rows returned / affected
- Execution duration
- Slow query warnings (> 100ms by default)
- Transaction lifecycle (BEGIN, COMMIT, ROLLBACK with duration)

## Usage Patterns

### Pattern 1: Simple Request Lifecycle

```python
from src.logging import configure_logging
from src.main_graph.main import run_request

configure_logging()
result = run_request("What do you know about X?")
# Summary is automatically printed at console and logged to file
```

### Pattern 2: Background Worker with Inherited Context

```python
from src.logging import spawn_background_task, bind_run_context

# Main thread
with bind_run_context(run_id=my_run_id, graph_name="MainGraph"):
    # Background task inherits run_id and graph_name
    spawn_background_task(background_worker, arg1, arg2)
```

Background task logs will include the same `run_id` as the parent context.

### Pattern 3: Record Memory Pipeline Events

```python
from src.logging import record_memory_event

# When consolidating semantic memories
record_memory_event(
    semantic_inserted=4,
    semantic_updated=2,
    semantic_ignored=1,
    semantic_merged=0,
    semantic_superseded=0,
)

# When consolidating episodic memories
record_memory_event(
    episodic_inserted=2,
    episodic_reactivated=5,
    episodic_updated=7,
    stag_edges=3,
)
```

### Pattern 4: Record Retrieval Events

```python
from src.logging import record_retrieval_event
import time

start = time.perf_counter()
semantic_candidates = retrieve_semantic(query_embedding)
episodic_candidates = retrieve_episodic(query_embedding)
packed = pack_context(semantic_candidates + episodic_candidates)
validated = validate_context(packed)
duration_ms = int((time.perf_counter() - start) * 1000)

record_retrieval_event(
    duration_ms=duration_ms,
    semantic_candidates=len(semantic_candidates),
    episodic_candidates=len(episodic_candidates),
    semantic_top_k=len(semantic_candidates[:SEMANTIC_TOP_K]),
    episodic_top_k=len(episodic_candidates[:EPISODIC_TOP_K]),
    packed_context_size=len(packed),
    validated_context_size=len(validated),
)
```

## Log Output Examples

### Console Output (Colored, Compact)

```
14:23:45 | INFO | run=e3a1c2d0-4f... | graph=Main Graph | node=unifiedextractor | Graph started
14:23:45 | INFO | run=e3a1c2d0-4f... | graph=Main Graph | node=unifiedextractor | Node started
14:23:46 | INFO | run=e3a1c2d0-4f... | graph=Main Graph | node=unifiedextractor | Node finished
14:23:46 | INFO | run=e3a1c2d0-4f... | graph=Main Graph | node=memory_dispatcher | Node started
14:23:46 | INFO | run=e3a1c2d0-4f... | graph=Retrieval Graph | node=query_router | Node started
14:23:46 | INFO | run=e3a1c2d0-4f... | graph=Retrieval Graph | node=semantic_retrieval | SELECT active_beliefs | rows_returned=27
14:23:47 | INFO | run=e3a1c2d0-4f... | graph=Main Graph | node=main_llm | LLM request completed

================ EXECUTION SUMMARY ================

Run ID: e3a1c2d0-4f8a-43b1-9c2a-7f8d9e0c1b2a

Total Runtime: 1247 ms

----------------------------------------

Graphs Executed

✓ Main Graph
✓ Retrieval Graph

----------------------------------------

Semantic Memory

Inserted: 4
Updated: 2
Ignored: 1

----------------------------------------

Episodic Memory

Inserted: 2
Reactivated: 5
Updated: 7

----------------------------------------

Retrieval

Semantic Retrieved: 27
Episodic Retrieved: 12
Packed Context: 8
Validated Context: 7

----------------------------------------

LLM

Calls: 1
Latency: 1234 ms
Total Tokens: 245

----------------------------------------

Database

Queries: 62
Rows Returned: 156
Rows Affected: 7
Total DB Time: 315 ms

===================================================
```

### JSON File Output (logs/latest.log)

```json
{"timestamp":"2026-07-20T14:23:45.123Z","run_id":"e3a1c2d0-4f8a-43b1-9c2a-7f8d9e0c1b2a","graph_name":"Main Graph","node_name":"unifiedextractor","level":"INFO","message":"Node started","duration_ms":null,"thread_name":"MainThread","process_id":1234,"extra":{}}
{"timestamp":"2026-07-20T14:23:46.234Z","run_id":"e3a1c2d0-4f8a-43b1-9c2a-7f8d9e0c1b2a","graph_name":"Retrieval Graph","node_name":"semantic_retrieval","level":"INFO","message":"SELECT active_beliefs","duration_ms":7,"thread_name":"MainThread","process_id":1234,"persistence_module":"semantic_store","sql_operation":"SELECT","table":"active_beliefs","rows_returned":27,"rows_affected":null,"extra":{}}
```

### Error File Output (logs/latest-error.log)

Only ERROR and CRITICAL level logs with full exception traceback.

## Database Observability Features

### 1. Automatic Query Logging

All SQL queries are automatically logged with:
- Operation (SELECT, INSERT, UPDATE, etc.)
- Table name (extracted from SQL)
- Rows returned / affected
- Execution time
- Status (SUCCESS, SKIPPED, FAILED)

### 2. Slow Query Warnings

Queries exceeding `SLOW_QUERY_WARNING_MS` automatically log a WARNING:

```
14:23:47 | WARNING | run=... | graph=... | node=... | SLOW QUERY | table=episodic_gists | duration=284 ms
```

### 3. Transaction Lifecycle

Transactions log BEGIN, COMMIT, or ROLLBACK with duration:

```
BEGIN (persistence_module=semantic_store)
INSERT active_beliefs (rows_affected=5)
COMMIT (duration=12 ms)
```

### 4. Write Verification

Every write operation records rows_affected and status:

```
INSERT episodic_gists | rows_affected=2 | duration=8 ms | status=SUCCESS
UPDATE beliefs | rows_affected=0 | duration=5 ms | status=SKIPPED
```

### 5. No Silent Failures

DB errors are never silently ignored:

```python
try:
    with conn.transaction():
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO beliefs ...")
    # Logged: COMMIT (status=SUCCESS)
except IntegrityError:
    # Logged: ROLLBACK (status=FAILED) with exception traceback
    raise
```

## Running the System

### Initialize at Startup

```python
from src.logging import configure_logging
from src.persistence import initialize_db

# Call once at the start of your application
configure_logging()
initialize_db()

# Then dispatch requests
from src.main_graph.main import run_request
result = run_request("User message here")
```

### Check Logs

```bash
# Real-time console output (already shown)
# Check logs directory
tail -f logs/latest.log          # All logs (JSON)
tail -f logs/latest-error.log    # Error logs only (JSON)
```

## OpenTelemetry Integration (Future)

The system is designed to integrate with OpenTelemetry with minimal changes:

```python
# Future: instrument execution summary export
from opentelemetry import trace, metrics

tracer = trace.get_tracer("langgraph-agent")
meter = metrics.get_meter("langgraph-agent")

# With minor modifications, ExecutionSummary can export to:
# - Jaeger (distributed tracing)
# - Prometheus (metrics)
# - Grafana (dashboards)
# - ELK (centralized logging + visualization)
```

## Best Practices

1. **Always call `configure_logging()` once at startup** before any logging occurs.

2. **Use `log_node` and `log_graph` decorators** instead of manual logging in node entry/exit.

3. **Use `record_*` functions** for domain-level events (memory pipeline, retrieval, LLM).

4. **Use `bind_run_context()` for background workers** to inherit parent context:

   ```python
   spawn_background_task(worker, arg, inherit_context=True)
   ```

5. **Never log secrets, API keys, or sensitive data** in extra fields.

6. **Check `logs/latest-error.log` regularly** for production monitoring.

7. **Export execution summary JSON** for analytics and performance monitoring.

## Troubleshooting

### Logs Not Appearing

- Verify `LOG_LEVEL` in `.env` is not too high (should be INFO or DEBUG).
- Ensure `LOG_DIR` directory exists and is writable.
- Check that `configure_logging()` was called before logging.

### Too Many Slow Query Warnings

- Increase `SLOW_QUERY_WARNING_MS` in `.env` (default 100 ms).
- Add database indexes to slow queries.

### High Memory Usage from Summary

- ExecutionSummary uses thread-safe dataclasses, not accumulating full state objects.
- For long-running sessions, periodically call `emit_execution_summary()` to flush and reset.

## File Rotation

Log files rotate automatically when they exceed `LOG_MAX_BYTES` (default 10 MB). Old logs are renamed with a sequence number:

```
logs/latest.log       (active)
logs/latest.log.1     (rotated)
logs/latest.log.2     (rotated)
...
```

Kept for `LOG_BACKUP_COUNT` rotations (default 5).
