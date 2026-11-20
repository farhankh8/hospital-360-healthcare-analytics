"""DuckDB access helpers.

A fresh read-only connection is opened per request (DuckDB connections are not
thread-safe). If the analytical database has not been built yet, callers receive
a clear ApiError instead of an opaque failure.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import duckdb

from api.core.config import DATABASE_PATH


class DatabaseNotReadyError(RuntimeError):
    """Raised when the DuckDB database has not been generated yet."""

    def __init__(self) -> None:
        super().__init__(
            "Analytical database is not available. Run `python -m generator.generate` "
            "then `python -m etl.pipeline` before starting the API."
        )


def database_exists() -> bool:
    return DATABASE_PATH.exists() and DATABASE_PATH.stat().st_size > 0


@contextmanager
def get_conn() -> Iterator[duckdb.DuckDBPyConnection]:
    if not database_exists():
        raise DatabaseNotReadyError()
    conn = duckdb.connect(str(DATABASE_PATH), read_only=True)
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.execute(sql, params or {})
        if cur.description is None:
            return []
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_one(sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def table_exists(name: str) -> bool:
    if not database_exists():
        return False
    row = fetch_one(
        "SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_name = $name",
        {"name": name},
    )
    return bool(row and row["n"])


def safe_table(table: str, allowed: set[str]) -> str:
    """Return an allowlisted table name or raise ValueError (no arbitrary SQL)."""
    if table not in allowed:
        raise ValueError(f"Unknown dataset: {table}")
    return table
