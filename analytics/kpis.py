"""Small, dependency-free KPI helpers shared by the API and the test suite.

These helpers implement the formula and validation rule documented for each
KPI in ``analytics/kpi_definitions/kpis.json``.  They work on in-memory rows
so the definitions remain testable without a running DuckDB instance.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from etl.silver import normalise_status

COMPLETED = "Completed"
NO_SHOW = "No-show"


def no_show_rate(rows: Iterable[dict[str, Any] | Any]) -> float | None:
    """Return no-show appointments as a percentage of completed + no-show.

    Cancelled (and any other status) is excluded from both numerator and
    denominator, matching ``kpis.json`` -> ``no_show_rate``.  A zero
    denominator returns ``None`` rather than raising or guessing.
    """
    completed = 0
    no_shows = 0
    for row in rows:
        status = row.get("status") if isinstance(row, dict) else getattr(row, "status", None)
        canonical = normalise_status(status)
        if canonical == COMPLETED:
            completed += 1
        elif canonical == NO_SHOW:
            no_shows += 1
    denominator = completed + no_shows
    if denominator == 0:
        return None
    return round(no_shows * 100.0 / denominator, 6)


__all__ = ["no_show_rate"]
