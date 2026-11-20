"""Generic, safe query helpers shared by all route modules."""
from __future__ import annotations

from typing import Any

import duckdb

from api.core.filters import Filters, build_where


def columns(conn: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    rows = conn.execute(f"DESCRIBE {table}").fetchall()
    return {r[0] for r in rows}


def query_rows(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    cur = conn.execute(sql, params or {})
    if cur.description is None:
        return []
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def query_scalar(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: dict[str, Any] | None = None,
) -> Any:
    row = conn.execute(sql, params or {}).fetchone()
    return row[0] if row else None


def filtered_rows(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    f: Filters,
    date_col: str = "month",
    select: str = "*",
    extra_where: str = "",
    extra_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    cols = columns(conn, table)
    where, params = build_where(f, cols, date_col=date_col)
    if extra_where:
        where = (where + f" AND {extra_where}") if where else f" WHERE {extra_where}"
    params.update(extra_params or {})
    return query_rows(conn, f"SELECT {select} FROM {table}{where}", params)


def paginated_rows(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    f: Filters,
    date_col: str = "month",
    allowlist: set[str] | None = None,
    force_filters: str = "",
    force_params: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Return (rows, total_records) with safe sorting, search and pagination."""
    cols = columns(conn, table)
    where, params = build_where(f, cols, date_col=date_col)
    if force_filters:
        where = (where + f" AND {force_filters}") if where else f" WHERE {force_filters}"
    params.update(force_params or {})

    # Search across allowlisted string columns only.
    if f.search:
        text_cols = [c for c in cols if c in (allowlist or cols) and not c.lower().endswith(("_id", "_date", "_at"))]
        if text_cols:
            parts = []
            for i, c in enumerate(text_cols):
                key = f"search_{i}"
                parts.append(f"CAST({c} AS VARCHAR) ILIKE :{key}")
                params[key] = f"%{f.search}%"
            where += (" AND " if where else " WHERE ") + "(" + " OR ".join(parts) + ")"

    count_sql = f"SELECT COUNT(*) FROM {table}{where}"
    total = int(query_scalar(conn, count_sql, params) or 0)

    order = ""
    if f.sort_by and (allowlist is None or f.sort_by in allowlist) and f.sort_by in cols:
        order = f" ORDER BY {f.sort_by} {f.sort_dir.upper()}"
    else:
        # Stable default: most recent first when a date column exists.
        if date_col in cols:
            order = f" ORDER BY {date_col} DESC"
        else:
            first = sorted(cols)[0] if cols else "1"
            order = f" ORDER BY {first} ASC"

    sql = f"SELECT * FROM {table}{where}{order} LIMIT :limit OFFSET :offset"
    params["limit"] = f.page_size
    params["offset"] = (f.page - 1) * f.page_size
    return query_rows(conn, sql, params), total
