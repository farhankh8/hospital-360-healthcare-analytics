"""Reusable route factories."""
from __future__ import annotations

from typing import Any, Callable

from fastapi import Request

from api.core.db import get_conn
from api.core.filters import Filters, parse_filters
from api.core.responses import envelope
from api.services.kpi_specs import SPECS
from api.services.metrics import build_kpis, period_metadata
from api.services.query import columns, query_rows


def make_kpis_route(module: str) -> Callable[[Request], dict[str, Any]]:
    def endpoint(request: Request) -> dict[str, Any]:
        f = parse_filters(request)
        with get_conn() as conn:
            data = build_kpis(conn, f, SPECS[module])
        return envelope(data, f.date_from, f.date_to, f.hospital_ids, **period_metadata(f))

    endpoint.__name__ = f"kpis_{module}"
    return endpoint


def series(
    table: str,
    date_col: str,
    expr: str,
    alias: str = "value",
    group_col: str | None = None,
    extra_where: str = "",
    order_asc: bool = True,
    limit: int | None = None,
) -> Callable[[Request], dict[str, Any]]:
    """Build a time-series or grouped endpoint from a single SQL expression."""

    def endpoint(request: Request) -> dict[str, Any]:
        f = parse_filters(request)
        with get_conn() as conn:
            cols = columns(conn, table)
            from api.core.filters import build_where

            where, params = build_where(f, cols, date_col=date_col)
            if extra_where:
                where = (where + f" AND {extra_where}") if where else f" WHERE {extra_where}"
            select = f"CAST({date_col} AS DATE) AS period"
            group = "period"
            if group_col and group_col in cols:
                select += f", {group_col}"
                group += f", {group_col}"
            sql = (
                f"SELECT {select}, {expr} AS {alias} FROM {table}{where} "
                f"GROUP BY {group} ORDER BY period {'ASC' if order_asc else 'DESC'}"
            )
            if group_col and group_col in cols:
                sql += f", {group_col}"
            if limit:
                sql += f" LIMIT {limit}"
            rows = query_rows(conn, sql, params)
        return envelope(rows, f.date_from, f.date_to, f.hospital_ids, grain="month" if date_col == "month" else date_col)

    endpoint.__name__ = f"series_{table}_{alias}"
    return endpoint


def multi_series(table: str, date_col: str, expressions: dict[str, str]) -> Callable[[Request], dict[str, Any]]:
    """Return one row per period with several named series."""

    def endpoint(request: Request) -> dict[str, Any]:
        f = parse_filters(request)
        with get_conn() as conn:
            from api.core.filters import build_where

            cols = columns(conn, table)
            where, params = build_where(f, cols, date_col=date_col)
            selects = ", ".join(f"{expr} AS {alias}" for alias, expr in expressions.items())
            sql = (
                f"SELECT CAST({date_col} AS DATE) AS period, {selects} "
                f"FROM {table}{where} GROUP BY 1 ORDER BY 1"
            )
            rows = query_rows(conn, sql, params)
        return envelope(rows, f.date_from, f.date_to, f.hospital_ids, series=list(expressions))

    endpoint.__name__ = f"multi_series_{table}"
    return endpoint


def grouped(table: str, group_col: str, expr: str, alias: str = "value", limit: int | None = 10, date_col: str = "month") -> Callable[[Request], dict[str, Any]]:
    def endpoint(request: Request) -> dict[str, Any]:
        f = parse_filters(request)
        with get_conn() as conn:
            from api.core.filters import build_where

            cols = columns(conn, table)
            where, params = build_where(f, cols, date_col=date_col)
            sql = (
                f"SELECT {group_col} AS label, {expr} AS {alias} FROM {table}{where} "
                f"GROUP BY {group_col} ORDER BY {alias} DESC"
            )
            if limit:
                sql += f" LIMIT {limit}"
            rows = query_rows(conn, sql, params)
        return envelope(rows, f.date_from, f.date_to, f.hospital_ids)

    endpoint.__name__ = f"grouped_{table}_{group_col}"
    return endpoint


def rows_endpoint(
    table: str,
    date_col: str = "month",
    force_filters: str = "",
    force_params: dict[str, Any] | None = None,
) -> Callable[[Request], dict[str, Any]]:
    def endpoint(request: Request) -> dict[str, Any]:
        from api.core.responses import table_envelope
        from api.services.query import paginated_rows

        f = parse_filters(request)
        with get_conn() as conn:
            rows, total = paginated_rows(
                conn, table, f, date_col=date_col,
                force_filters=force_filters, force_params=force_params,
            )
        return table_envelope(rows, total, f.page, f.page_size, f.applied())

    endpoint.__name__ = f"rows_{table}"
    return endpoint
