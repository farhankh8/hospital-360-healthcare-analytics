"""KPI computation: current value, previous period, change and sparkline.

Every KPI is computed by the API from gold/silver tables. The frontend never
calculates business metrics itself.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
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
        cols = cache[spec.table]
        where, params = build_where(f, cols, date_col=spec.date_col)
        prev_where, prev_params = build_where(f, cols, date_col=spec.date_col, use_previous=True)

        value = _clean(query_scalar(conn, f"SELECT {spec.expr} AS v FROM {spec.table}{where}", params))
        previous = _clean(query_scalar(conn, f"SELECT {spec.expr} AS v FROM {spec.table}{prev_where}", prev_params))
        change_pct, direction = _change(value, previous)

        # Favourable polarity (lower-is-better metrics invert the colour).
        favourable = direction
        if direction in {"up", "down"} and not spec.higher_is_better:
            favourable = "down" if direction == "up" else "up"

        sparkline: list[float | int | None] = []
        if spec.date_col in cols:
            spark_rows = query_rows(
                conn,
                f"SELECT CAST({spec.date_col} AS DATE) AS d, {spec.expr} AS v "
                f"FROM {spec.table}{where} GROUP BY 1 ORDER BY 1",
                params,
            )
            sparkline = [_clean(r["v"]) for r in spark_rows][-24:]

        result[spec.id] = {
            "id": spec.id,
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
    return result


def period_metadata(f: Filters) -> dict[str, str]:
    prev_from, prev_to = shift_period(f)
    return {"previous_date_from": prev_from, "previous_date_to": prev_to}
