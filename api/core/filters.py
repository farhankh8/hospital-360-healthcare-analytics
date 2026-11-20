"""Global filter parsing and safe WHERE-clause construction.

All filter column names are allowlisted; all values are passed as bound
parameters. User input can never become SQL text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from fastapi import Request

from api.core.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

DEFAULT_DATE_FROM = "2025-01-01"
DEFAULT_DATE_TO = "2026-12-31"

# Columns that may legally be filtered. Never interpolate raw user strings.
ALLOWED_FILTER_COLUMNS = {
    "date_from_date": {
        "month", "date", "appointment_date", "invoice_date", "claim_date", "shift_date",
        "incident_date", "visit_date", "movement_date", "prescribed_date", "arrival_datetime",
        "snapshot_datetime", "scheduled_start", "ordered_at", "event_date", "payment_date",
    },
    "date_to_date": {
        "month", "date", "appointment_date", "invoice_date", "claim_date", "shift_date",
        "incident_date", "visit_date", "movement_date", "prescribed_date", "arrival_datetime",
        "snapshot_datetime", "scheduled_start", "ordered_at", "event_date", "payment_date",
    },
    "hospital_id": {"hospital_id"},
    "department_id": {"department_id", "ordering_department"},
    "specialty_id": {"specialty_id"},
    "payer_id": {"payer_id"},
    "encounter_type": {"encounter_type"},
    "patient_type": {"patient_type"},
}


@dataclass
class Filters:
    date_from: str = DEFAULT_DATE_FROM
    date_to: str = DEFAULT_DATE_TO
    hospital_ids: list[str] = field(default_factory=list)
    department_id: str | None = None
    specialty_id: str | None = None
    payer_id: str | None = None
    encounter_type: str | None = None
    patient_type: str | None = None
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    search: str | None = None
    sort_by: str | None = None
    sort_dir: str = "asc"
    previous: bool = False

    def applied(self) -> dict[str, Any]:
        return {
            "date_from": self.date_from,
            "date_to": self.date_to,
            "hospital_ids": self.hospital_ids,
            "department_id": self.department_id,
            "specialty_id": self.specialty_id,
            "payer_id": self.payer_id,
            "encounter_type": self.encounter_type,
            "patient_type": self.patient_type,
            "search": self.search,
        }


def parse_filters(request: Request) -> Filters:
    q = request.query_params
    page = _positive_int(q.get("page"), 1)
    page_size = _positive_int(q.get("page_size"), DEFAULT_PAGE_SIZE)
    page_size = min(page_size, MAX_PAGE_SIZE)
    sort_dir = (q.get("sort_dir", "asc") or "asc").lower()
    if sort_dir not in {"asc", "desc"}:
        sort_dir = "asc"
    date_from = q.get("date_from") or DEFAULT_DATE_FROM
    date_to = q.get("date_to") or DEFAULT_DATE_TO
    for value in (date_from, date_to):
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Invalid date '{value}'. Use YYYY-MM-DD.") from exc
    return Filters(
        date_from=date_from,
        date_to=date_to,
        hospital_ids=[v for v in q.getlist("hospital_id") if v],
        department_id=q.get("department_id") or None,
        specialty_id=q.get("specialty_id") or None,
        payer_id=q.get("payer_id") or None,
        encounter_type=q.get("encounter_type") or None,
        patient_type=q.get("patient_type") or None,
        page=page,
        page_size=page_size,
        search=q.get("search") or None,
        sort_by=q.get("sort_by") or None,
        sort_dir=sort_dir,
        previous=(q.get("previous") or "").lower() in {"1", "true", "yes"},
    )


def _positive_int(value: str | None, default: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def shift_period(f: Filters) -> tuple[str, str]:
    """Return the immediately preceding period of equal length."""
    from datetime import date, timedelta

    try:
        start = date.fromisoformat(f.date_from)
        end = date.fromisoformat(f.date_to)
    except ValueError:
        return f.date_from, f.date_to
    days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return prev_start.isoformat(), prev_end.isoformat()


def build_where(
    f: Filters,
    available_columns: set[str],
    date_col: str = "month",
    hospital_col: str = "hospital_id",
    use_previous: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Build an allowlisted, parameterised WHERE clause.

    `available_columns` is the set of columns the target table actually has, so
    irrelevant filters (e.g. payer on a bed-occupancy chart) are ignored rather
    than producing SQL errors.
    """
    clauses: list[str] = []
    params: dict[str, Any] = {}

    if date_col in available_columns and date_col in ALLOWED_FILTER_COLUMNS["date_from_date"]:
        date_from, date_to = shift_period(f) if use_previous else (f.date_from, f.date_to)
        clauses.append(f"CAST({date_col} AS DATE) >= CAST($date_from AS DATE)")
        clauses.append(f"CAST({date_col} AS DATE) <= CAST($date_to AS DATE)")
        params["date_from"] = date_from
        params["date_to"] = date_to

    if hospital_col in available_columns and f.hospital_ids:
        placeholders = []
        for i, hid in enumerate(f.hospital_ids):
            key = f"hospital_{i}"
            placeholders.append(f"${key}")
            params[key] = hid
        clauses.append(f"{hospital_col} IN ({', '.join(placeholders)})")

    simple = {
        "department_id": f.department_id,
        "specialty_id": f.specialty_id,
        "payer_id": f.payer_id,
        "encounter_type": f.encounter_type,
        "patient_type": f.patient_type,
    }
    for name, value in simple.items():
        if value is None:
            continue
        candidates = ALLOWED_FILTER_COLUMNS[name] & available_columns
        if candidates:
            col = min(candidates)
            clauses.append(f"{col} = ${name}")
            params[name] = value

    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return where, params
