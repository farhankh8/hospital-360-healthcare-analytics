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
from api.core.errors import FilterValidationError

DEFAULT_DATE_FROM = "2025-01-01"
DEFAULT_DATE_TO = "2026-12-31"

# Columns that may legally be filtered. Never interpolate raw user strings.
ALLOWED_FILTER_COLUMNS = {
    "date_from_date": {
        "month", "date", "appointment_date", "invoice_date", "claim_date", "shift_date",
        "incident_date", "visit_date", "movement_date", "prescribed_date", "arrival_datetime",
        "snapshot_datetime", "scheduled_start", "ordered_at", "event_date", "payment_date",
        "admission_datetime", "discharge_datetime", "dispensed_date", "result_at",
        "collection_at", "received_date", "expected_date", "resolution_date", "triage_datetime",
    },
    "date_to_date": {
        "month", "date", "appointment_date", "invoice_date", "claim_date", "shift_date",
        "incident_date", "visit_date", "movement_date", "prescribed_date", "arrival_datetime",
        "snapshot_datetime", "scheduled_start", "ordered_at", "event_date", "payment_date",
        "admission_datetime", "discharge_datetime", "dispensed_date", "result_at",
        "collection_at", "received_date", "expected_date", "resolution_date", "triage_datetime",
    },
    "hospital_id": {"hospital_id"},
    "department_id": {"department_id", "ordering_department"},
    "specialty_id": {"specialty_id"},
    "payer_id": {"payer_id"},
    "encounter_type": {"encounter_type"},
    "patient_type": {"patient_type"},
}

# Page-scoped filters requested by the blueprint. Each value is an allowlist of
# possible column names; the first column present on a table is used. Values are
# always bound parameters, never interpolated.
PAGE_FILTER_COLUMNS: dict[str, tuple[str, ...]] = {
    "doctor_id": ("doctor_id", "surgeon_id", "provider_id"),
    "appointment_type": ("appointment_type",),
    "status": ("status",),
    "age_group": ("age_group",),
    "booking_channel": ("booking_channel",),
    "triage_category": ("triage_category",),
    "disposition": ("disposition",),
    "arrival_mode": ("arrival_mode",),
    "ward": ("ward",),
    "bed_type": ("bed_type",),
    "admission_type": ("admission_type",),
    "discharge_type": ("discharge_status", "discharge_disposition"),
    "or_room": ("or_room",),
    "procedure_code": ("procedure_code",),
    "elective_emergency": ("elective_emergency",),
    "ordering_department": ("ordering_department",),
    "test_code": ("test_code",),
    "priority": ("priority",),
    "result_status": ("result_status", "status"),
    "medication_code": ("medication_code",),
    "service_category": ("service_category",),
    "invoice_status": ("invoice_status",),
    "payment_status": ("payment_status",),
    "denial_reason": ("denial_reason",),
    "claim_type": ("claim_type",),
    "role": ("role",),
    "shift_type": ("shift_type",),
    "employment_type": ("employment_type",),
    "category": ("category",),
    "item_id": ("item_id",),
    "supplier_id": ("supplier_id",),
    "movement_type": ("movement_type",),
    "feedback_type": ("feedback_type",),
    "rating": ("rating",),
    "sentiment": ("sentiment_label",),
    "severity": ("severity",),
    "resolution_status": ("resolution_status",),
}

NUMERIC_FILTER_TYPES = ("INTEGER", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT", "REAL")
# Page-scoped filters whose values are always numeric regardless of table schema.
NUMERIC_PAGE_FILTERS = {"rating"}

# Query keys recognised by the shared filter contract. Route-specific keys are
# listed separately so that, for example, ``?by=department`` is not rejected.
SUPPORTED_QUERY_PARAMS = {
    "date_from", "date_to", "hospital_id", "department_id", "specialty_id",
    "payer_id", "encounter_type", "patient_type", "page", "page_size", "search",
    "sort_by", "sort_dir", "previous", "numeric_column", "numeric_min",
    "numeric_max", *PAGE_FILTER_COLUMNS,
}
ROUTE_QUERY_PARAMS = {"by", "metric", "run_a", "run_b", "patient_id", "encounter_id", "admission_id", "event_type", "rank_sort"}
BOOLEAN_VALUES = {
    "1": True, "true": True, "yes": True,
    "0": False, "false": False, "no": False,
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
    page_filters: dict[str, str] = field(default_factory=dict)
    numeric_column: str | None = None
    numeric_min: str | None = None
    numeric_max: str | None = None

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
            "page_filters": self.page_filters,
            "numeric_column": self.numeric_column,
            "numeric_min": self.numeric_min,
            "numeric_max": self.numeric_max,
            "search": self.search,
        }


def parse_filters(request: Request) -> Filters:
    """Parse and validate all supported query parameters.

    Invalid or unsupported parameters raise ``FilterValidationError`` so the
    global handler returns the structured ``VALIDATION_ERROR`` envelope with a
    stable machine-readable code instead of silently coercing the request.
    """
    q = request.query_params
    allowed = SUPPORTED_QUERY_PARAMS | ROUTE_QUERY_PARAMS
    unsupported = sorted(set(q.keys()) - allowed)
    if unsupported:
        raise FilterValidationError(
            f"Unsupported query parameter(s): {', '.join(unsupported)}",
            {"parameters": unsupported},
        )

    page = _positive_int(q.get("page"), 1, "page")
    page_size = _positive_int(q.get("page_size"), DEFAULT_PAGE_SIZE, "page_size")
    if page_size > MAX_PAGE_SIZE:
        raise FilterValidationError(
            f"page_size must be between 1 and {MAX_PAGE_SIZE}",
            {"parameter": "page_size", "value": q.get("page_size"), "maximum": MAX_PAGE_SIZE},
        )

    sort_dir = (q.get("sort_dir") or "asc").lower()
    if sort_dir not in {"asc", "desc"}:
        raise FilterValidationError(
            "sort_dir must be 'asc' or 'desc'",
            {"parameter": "sort_dir", "value": q.get("sort_dir")},
        )

    date_from = q.get("date_from") or DEFAULT_DATE_FROM
    date_to = q.get("date_to") or DEFAULT_DATE_TO
    _date(date_from, "date_from")
    _date(date_to, "date_to")
    if date_from > date_to:
        raise FilterValidationError(
            "date_from must not be later than date_to",
            {"parameter": "date_from", "value": date_from, "date_to": date_to},
        )

    hospital_ids = [_text(v, "hospital_id") for v in q.getlist("hospital_id") if v]
    previous = _boolean(q.get("previous"), "previous")

    numeric_column = q.get("numeric_column") or None
    if numeric_column is not None:
        _identifier(numeric_column, "numeric_column")
    numeric_min = _number(q.get("numeric_min"), "numeric_min")
    numeric_max = _number(q.get("numeric_max"), "numeric_max")
    if (
        numeric_min is not None
        and numeric_max is not None
        and float(numeric_min) > float(numeric_max)
    ):
        raise FilterValidationError(
            "numeric_min must not be greater than numeric_max",
            {"parameter": "numeric_min", "value": numeric_min, "numeric_max": numeric_max},
        )

    page_filters: dict[str, str] = {}
    for name in PAGE_FILTER_COLUMNS:
        value = q.get(name)
        if value is None or value == "":
            continue
        checked = _text(value, name)
        assert checked is not None
        if name in NUMERIC_PAGE_FILTERS:
            _number(checked, name)
        page_filters[name] = checked

    parsed = Filters(
        date_from=date_from,
        date_to=date_to,
        hospital_ids=hospital_ids,
        department_id=_text(q.get("department_id"), "department_id"),
        specialty_id=_text(q.get("specialty_id"), "specialty_id"),
        payer_id=_text(q.get("payer_id"), "payer_id"),
        encounter_type=_text(q.get("encounter_type"), "encounter_type"),
        patient_type=_text(q.get("patient_type"), "patient_type"),
        page=page,
        page_size=page_size,
        search=_text(q.get("search"), "search"),
        sort_by=_identifier(q.get("sort_by"), "sort_by"),
        sort_dir=sort_dir,
        previous=previous,
        page_filters=page_filters,
        numeric_column=numeric_column,
        numeric_min=numeric_min,
        numeric_max=numeric_max,
    )
    _validate_filter_values(parsed)
    return parsed


def _invalid(parameter: str, value: Any, reason: str) -> FilterValidationError:
    return FilterValidationError(
        f"Invalid {parameter}: {reason}",
        {"parameter": parameter, "value": value, "reason": reason},
    )


def _positive_int(value: str | None, default: int, parameter: str) -> int:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise _invalid(parameter, value, "must be a whole number") from exc
    if parsed < 1:
        raise _invalid(parameter, value, "must be greater than zero")
    return parsed


def _date(value: str, parameter: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _invalid(parameter, value, "must use YYYY-MM-DD") from exc


def _boolean(value: str | None, parameter: str) -> bool:
    if value is None or value == "":
        return False
    parsed = BOOLEAN_VALUES.get(value.lower())
    if parsed is None:
        raise _invalid(parameter, value, "must be true or false")
    return parsed


def _text(value: str | None, parameter: str) -> str | None:
    if value is None or value == "":
        return None
    if len(value) > 200 or any(ord(ch) < 32 for ch in value):
        raise _invalid(parameter, value, "must be at most 200 characters without control characters")
    return value


def _identifier(value: str | None, parameter: str) -> str | None:
    value = _text(value, parameter)
    if value and not value.replace("_", "").isalnum():
        raise _invalid(parameter, value, "must contain only letters, digits and underscores")
    return value


def _number(value: str | None, parameter: str) -> str | None:
    if value is None or value == "":
        return None
    try:
        float(value)
    except (TypeError, ValueError) as exc:
        raise _invalid(parameter, value, "must be a number") from exc
    return value


_ALLOWED_ID_CACHE: dict[tuple[str, str, str], set[str]] = {}


def _load_allowed_ids(column: str, table: str) -> set[str]:
    """Load and cache allowed ID values from a dimension table."""
    try:
        from api.core.config import DATABASE_PATH
        cache_key = (str(DATABASE_PATH), column, table)
    except Exception:  # noqa: BLE001 - config import failure should not block filter validation
        cache_key = ("", column, table)
    if cache_key in _ALLOWED_ID_CACHE:
        return _ALLOWED_ID_CACHE[cache_key]
    try:
        from api.core.db import get_conn  # local import to avoid circular deps
        with get_conn() as conn:
            rows = conn.execute(f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL").fetchall()
        values = {str(r[0]) for r in rows if r[0] is not None}
    except Exception:  # noqa: BLE001 - DB unavailable during startup; downstream reports DB-not-ready
        return set()
    _ALLOWED_ID_CACHE[cache_key] = values
    return values


_ID_FILTER_ALLOWLISTS: dict[str, tuple[str, str]] = {
    "hospital_id": ("hospital_id", "dim_hospital"),
    "department_id": ("department_id", "dim_department"),
    "specialty_id": ("specialty_id", "dim_specialty"),
    "payer_id": ("payer_id", "dim_payer"),
}

_PAGE_FILTER_ID_ALLOWLISTS: dict[str, tuple[str, str]] = {
    "doctor_id": ("doctor_id", "dim_doctor"),
    "supplier_id": ("supplier_id", "dim_supplier"),
    "item_id": ("item_id", "dim_inventory_item"),
}


def _validate_filter_values(f: Filters) -> None:
    """Reject filter ID values not present in known dimension allowlists."""
    allowed_hospitals = _load_allowed_ids("hospital_id", "dim_hospital")
    if allowed_hospitals:
        for hid in f.hospital_ids:
            if hid not in allowed_hospitals:
                raise FilterValidationError(
                    f"Invalid hospital_id: '{hid}' is not a known hospital",
                    {"parameter": "hospital_id", "value": hid, "allowed": sorted(allowed_hospitals)},
                )

    for param, (column, table) in _ID_FILTER_ALLOWLISTS.items():
        if param == "hospital_id":
            continue
        value = getattr(f, param, None)
        if value is None:
            continue
        allowed = _load_allowed_ids(column, table)
        if allowed and value not in allowed:
            raise FilterValidationError(
                f"Invalid {param}: '{value}' is not a known value",
                {"parameter": param, "value": value},
            )

    for param, (column, table) in _PAGE_FILTER_ID_ALLOWLISTS.items():
        value = f.page_filters.get(param)
        if value is None:
            continue
        allowed = _load_allowed_ids(column, table)
        if allowed and value not in allowed:
            raise FilterValidationError(
                f"Invalid {param}: '{value}' is not a known value",
                {"parameter": param, "value": value},
            )


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
    date_col_sql: str | None = None,
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
        sql_col = date_col_sql or date_col
        clauses.append(f"CAST({sql_col} AS DATE) >= CAST($date_from AS DATE)")
        clauses.append(f"CAST({sql_col} AS DATE) <= CAST($date_to AS DATE)")
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

    for name, value in f.page_filters.items():
        candidates = [c for c in PAGE_FILTER_COLUMNS.get(name, ()) if c in available_columns]
        if not candidates:
            continue
        key = f"pf_{name}"
        clauses.append(f"{candidates[0]} = ${key}")
        params[key] = value

    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return where, params
