"""KPI computation: current value, previous period, change and sparkline.

Every KPI is computed by the API from gold/silver tables. The frontend never
calculates business metrics itself.

A KpiSpec may declare:
  * aliases      - additional response keys for the same calculation, so the
                   canonical blueprint names and legacy short names coexist.
  * join_sql     - an optional allowlisted join for derived metrics.
  * extra_where  - an optional fixed predicate appended to the safe WHERE.
  * source_columns - extra columns made visible to the allowlisted filter
                   builder (e.g. a joined table's date column).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import duckdb

from api.core.filters import Filters, build_where, shift_period
from api.services.query import columns, query_rows, query_scalar


@dataclass(frozen=True)
class KpiSpec:
    id: str
    label: str
    table: str
    expr: str
    date_col: str = "month"
    unit: str = "count"
    higher_is_better: bool = True
    precision: int = 2
    description: str = ""
    aliases: tuple[str, ...] = ()
    join_sql: str = ""
    extra_where: str = ""
    source_columns: tuple[str, ...] = field(default_factory=tuple)
    date_col_sql: str = ""


def _clean(value: Any) -> float | int | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, 2)


def _change(current: Any, previous: Any) -> tuple[float | None, str]:
    c = None if current is None else float(current)
    p = None if previous is None else float(previous)
    if c is None or p is None or p == 0:
        return None, "flat"
    pct = (c - p) / abs(p) * 100
    return round(pct, 2), "up" if pct > 0 else ("down" if pct < 0 else "flat")


def _sql(spec: KpiSpec, where: str) -> str:
    """Combine the parameterised filter WHERE with a fixed derived predicate."""
    if spec.extra_where:
        where = (where + f" AND {spec.extra_where}") if where else f" WHERE {spec.extra_where}"
    return f"FROM {spec.table} {spec.join_sql}{where}".strip()


def build_kpis(
    conn: duckdb.DuckDBPyConnection,
    f: Filters,
    specs: list[KpiSpec],
) -> dict[str, dict[str, Any]]:
    """Compute all KPI cards for the given filters."""
    result: dict[str, dict[str, Any]] = {}
    cache: dict[str, set[str]] = {}

    for spec in specs:
        if spec.table not in cache:
            cache[spec.table] = columns(conn, spec.table)
        cols = cache[spec.table] | set(spec.source_columns)
        date_sql = spec.date_col_sql or spec.date_col
        where, params = build_where(f, cols, date_col=spec.date_col, date_col_sql=date_sql)
        prev_where, prev_params = build_where(
            f, cols, date_col=spec.date_col, date_col_sql=date_sql, use_previous=True
        )
        source = _sql(spec, where)
        previous_source = _sql(spec, prev_where)

        value = _clean(query_scalar(conn, f"SELECT {spec.expr} AS v {source}", params))
        previous = _clean(query_scalar(conn, f"SELECT {spec.expr} AS v {previous_source}", prev_params))
        change_pct, direction = _change(value, previous)

        # Favourable polarity (lower-is-better metrics invert the colour).
        favourable = direction
        if direction in {"up", "down"} and not spec.higher_is_better:
            favourable = "down" if direction == "up" else "up"

        sparkline: list[float | int | None] = []
        if spec.date_col in cols:
            spark_rows = query_rows(
                conn,
                f"SELECT CAST({date_sql} AS DATE) AS d, {spec.expr} AS v "
                f"{source} GROUP BY 1 ORDER BY 1",
                params,
            )
            sparkline = [_clean(r["v"]) for r in spark_rows][-24:]

        card = {
            "label": spec.label,
            "value": value,
            "previous": previous,
            "change_pct": change_pct,
            "trend": direction,
            "favourable": favourable,
            "unit": spec.unit,
            "precision": spec.precision,
            "sparkline": sparkline,
            "definition": spec.description,
        }
        if not spec.date_col:
            card["date_filter_available"] = False
            card["date_filter_note"] = "Date filter unavailable: this is a snapshot KPI with no date field."
        for key in (spec.id, *spec.aliases):
            result[key] = {"id": key, **card}
    return result


def period_metadata(f: Filters) -> dict[str, str]:
    prev_from, prev_to = shift_period(f)
    return {"previous_date_from": prev_from, "previous_date_to": prev_to}
