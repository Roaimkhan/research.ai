from __future__ import annotations

import re
import time
from contextlib import contextmanager
from typing import Any, Iterator

from .context import record_database_query
from .logger import get_logger
from src.config import config


logger = get_logger(__name__)

_SQL_OPERATION_RE = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|BEGIN|COMMIT|ROLLBACK|CREATE|ALTER|DROP|TRUNCATE|WITH)\b", re.IGNORECASE)
_INSERT_TABLE_RE = re.compile(r"INSERT\s+INTO\s+([\w\.\"]+)", re.IGNORECASE)
_UPDATE_TABLE_RE = re.compile(r"UPDATE\s+([\w\.\"]+)", re.IGNORECASE)
_DELETE_TABLE_RE = re.compile(r"DELETE\s+FROM\s+([\w\.\"]+)", re.IGNORECASE)
_SELECT_TABLE_RE = re.compile(r"FROM\s+([\w\.\"]+)", re.IGNORECASE)


def _operation(sql: str) -> str:
    match = _SQL_OPERATION_RE.match(sql or "")
    if not match:
        return "OTHER"
    operation = match.group(1).upper()
    if operation == "INSERT" and "ON CONFLICT" in sql.upper():
        return "UPSERT"
    return operation


def _table(sql: str) -> str | None:
    if not sql:
        return None
    for regex in (_INSERT_TABLE_RE, _UPDATE_TABLE_RE, _DELETE_TABLE_RE, _SELECT_TABLE_RE):
        match = regex.search(sql)
        if match:
            return match.group(1).strip('"')
    return None


class ObservedCursor:
    def __init__(self, cursor: Any, persistence_module: str) -> None:
        self._cursor = cursor
        self._persistence_module = persistence_module
        self._last_sql = ""
        self._last_operation = "OTHER"
        self._last_table: str | None = None

    def execute(self, sql: str, params: Any = None) -> Any:
        started_at = time.perf_counter()
        self._last_sql = sql or ""
        self._last_operation = _operation(self._last_sql)
        self._last_table = _table(self._last_sql)
        try:
            result = self._cursor.execute(sql, params)
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            rows_affected = getattr(self._cursor, "rowcount", None)
            status = "SUCCESS"
            if self._last_operation in {"INSERT", "UPDATE", "DELETE", "UPSERT"} and rows_affected == 0:
                status = "SKIPPED"
            self._log_query(duration_ms=duration_ms, rows_affected=rows_affected, rows_returned=None, success=True, status=status)
            return result
        except Exception:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            self._log_query(duration_ms=duration_ms, rows_affected=None, rows_returned=None, success=False, status="FAILED")
            raise

    def fetchall(self) -> list[Any]:
        started_at = time.perf_counter()
        rows = self._cursor.fetchall()
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        self._log_query(duration_ms=duration_ms, rows_returned=len(rows), rows_affected=None, success=True, status="SUCCESS")
        return rows

    def fetchone(self) -> Any:
        started_at = time.perf_counter()
        row = self._cursor.fetchone()
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        self._log_query(duration_ms=duration_ms, rows_returned=1 if row is not None else 0, rows_affected=None, success=True, status="SUCCESS")
        return row

    def fetchmany(self, size: int | None = None) -> list[Any]:
        started_at = time.perf_counter()
        rows = self._cursor.fetchmany(size)
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        self._log_query(duration_ms=duration_ms, rows_returned=len(rows), rows_affected=None, success=True, status="SUCCESS")
        return rows

    def __iter__(self):
        count = 0
        for row in self._cursor:
            count += 1
            yield row
        self._log_query(duration_ms=0, rows_returned=count, rows_affected=None, success=True, status="SUCCESS")

    def __enter__(self) -> "ObservedCursor":
        self._cursor.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> Any:
        return self._cursor.__exit__(exc_type, exc, tb)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._cursor, item)

    def _log_query(
        self,
        *,
        duration_ms: int,
        rows_returned: int | None,
        rows_affected: int | None,
        success: bool,
        status: str,
    ) -> None:
        operation = self._last_operation
        table = self._last_table
        record_database_query(
            operation=operation,
            table=table,
            duration_ms=duration_ms,
            rows_returned=rows_returned,
            rows_affected=rows_affected,
            success=success,
            persistence_module=self._persistence_module,
            status=status,
        )
        extra = {
            "persistence_module": self._persistence_module,
            "sql_operation": operation,
            "table": table,
            "rows_returned": rows_returned,
            "rows_affected": rows_affected,
            "duration_ms": duration_ms,
            "status": status,
        }
        message = f"{operation} {table or 'query'}"
        if rows_returned is not None:
            message += f" | rows_returned={rows_returned}"
        if rows_affected is not None:
            message += f" | rows_affected={rows_affected}"
        logger.info(message, extra=extra)
        if duration_ms >= config.SLOW_QUERY_WARNING_MS:
            logger.warning("SLOW QUERY", extra={**extra, "duration_ms": duration_ms})


class ObservedTransaction:
    def __init__(self, connection: Any, persistence_module: str) -> None:
        self._connection = connection
        self._transaction = connection.transaction()
        self._persistence_module = persistence_module
        self._started_at = 0.0

    def __enter__(self) -> "ObservedTransaction":
        self._started_at = time.perf_counter()
        logger.info("BEGIN", extra={"persistence_module": self._persistence_module, "sql_operation": "BEGIN"})
        self._transaction.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> Any:
        if exc_type is None:
            duration_ms = int((time.perf_counter() - self._started_at) * 1000)
            logger.info("COMMIT", extra={"persistence_module": self._persistence_module, "sql_operation": "COMMIT", "duration_ms": duration_ms, "status": "SUCCESS"})
        else:
            duration_ms = int((time.perf_counter() - self._started_at) * 1000)
            logger.error("ROLLBACK", extra={"persistence_module": self._persistence_module, "sql_operation": "ROLLBACK", "duration_ms": duration_ms, "status": "FAILED"}, exc_info=(exc_type, exc, tb))
        return self._transaction.__exit__(exc_type, exc, tb)


class ObservedConnection:
    def __init__(self, connection: Any, persistence_module: str) -> None:
        self._connection = connection
        self._persistence_module = persistence_module

    def cursor(self, *args: Any, **kwargs: Any) -> ObservedCursor:
        return ObservedCursor(self._connection.cursor(*args, **kwargs), self._persistence_module)

    def transaction(self) -> ObservedTransaction:
        return ObservedTransaction(self._connection, self._persistence_module)

    def execute(self, sql: str, params: Any = None) -> Any:
        with self.cursor() as cursor:
            return cursor.execute(sql, params)

    def commit(self) -> Any:
        logger.info("COMMIT", extra={"persistence_module": self._persistence_module, "sql_operation": "COMMIT", "status": "SUCCESS"})
        return self._connection.commit()

    def rollback(self) -> Any:
        logger.warning("ROLLBACK", extra={"persistence_module": self._persistence_module, "sql_operation": "ROLLBACK", "status": "FAILED"})
        return self._connection.rollback()

    def __getattr__(self, item: str) -> Any:
        return getattr(self._connection, item)


def instrument_connection(connection: Any, persistence_module: str) -> ObservedConnection:
    return ObservedConnection(connection, persistence_module)


def instrument_connection_pool(pool: Any, persistence_module: str):
    class ObservedPool:
        def __init__(self, wrapped_pool: Any) -> None:
            self._pool = wrapped_pool

        @contextmanager
        def connection(self) -> Iterator[ObservedConnection]:
            with self._pool.connection() as connection:
                yield instrument_connection(connection, persistence_module)

        def __getattr__(self, item: str) -> Any:
            return getattr(self._pool, item)

    return ObservedPool(pool)
