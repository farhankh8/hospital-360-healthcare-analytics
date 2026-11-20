"""Silver layer — typed, standardised and validated records.

Every canonical table is processed in dependency order so that foreign keys and
cross-table timelines can be checked against already-cleaned parents.  A row is
removed from silver **only** when it violates an ERROR-severity rule; it is
first written to quarantine with its original raw values, the rule id, a human
readable reason, the pipeline run id and the source file.  Nothing is silently
discarded.

Null policy (documented):
* identifier columns, required dates and hospital codes must be present;
* nullable business fields (e.g. ``discharge_datetime``, ``result_at``,
  ``cancellation_reason``, ``payer_id``) keep their nulls -- no fabricated
  "Unknown" or zero values;
* numeric measures keep nulls when the source did not supply them.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from generator import config, schema

# ---------------------------------------------------------------------------
# Rule catalog (ids shared with etl/quality.py)
# ---------------------------------------------------------------------------
RULES: dict[str, dict[str, str]] = {
    "PK_NULL": {"severity": "error", "description": "Primary key is null or empty."},
    "PK_DUPLICATE": {"severity": "error", "description": "Duplicate primary key; first occurrence retained, later copies quarantined."},
    "HOSPITAL_ID_MISSING": {"severity": "error", "description": "Required hospital_id is null."},
    "HOSPITAL_ID_INVALID": {"severity": "error", "description": "hospital_id is not one of the canonical codes H01..H10."},
    "REQUIRED_DATE_INVALID": {"severity": "error", "description": "A required date/timestamp is null or cannot be parsed."},
    "DATE_ORDER_INVALID": {"severity": "error", "description": "Dependent date precedes its parent date (e.g. discharge before admission)."},
    "NEGATIVE_AMOUNT": {"severity": "error", "description": "A monetary amount is negative outside the documented Refund exception."},
    "NEGATIVE_DURATION": {"severity": "error", "description": "A duration/hour measure is negative."},
    "NUMERIC_OUT_OF_RANGE": {"severity": "error", "description": "A numeric value falls outside its documented range (rating 1-5, NPS 0-10, reliability 0-1)."},
    "FK_ORPHAN": {"severity": "error", "description": "Foreign key references a parent record that does not exist in silver."},
    "STATUS_INVALID": {"severity": "warning", "description": "Status value was not in the canonical vocabulary; Title Case normalisation applied."},
    "NULL_FK": {"severity": "warning", "description": "Business-nullable foreign key (e.g. payer_id) is missing; record retained."},
}

PRIMARY_KEYS: dict[str, str] = {
    "dim_hospital": "hospital_id", "dim_specialty": "specialty_id",
    "dim_department": "department_id", "dim_doctor": "doctor_id",
    "dim_staff": "staff_id", "dim_payer": "payer_id",
    "dim_diagnosis": "diagnosis_code", "dim_procedure": "procedure_code",
    "dim_medication": "medication_code", "dim_lab_test": "test_code",
    "dim_service": "service_code", "dim_supplier": "supplier_id",
    "dim_inventory_item": "item_id", "dim_bed": "bed_id",
    "dim_date": "date_key", "dim_time": "time_key",
    "patients": "patient_id", "appointments": "appointment_id",
    "encounters": "encounter_id", "admissions": "admission_id",
    "transfers": "transfer_id", "bed_snapshots": "snapshot_id",
    "procedures": "procedure_id", "lab_orders": "lab_order_id",
    "lab_results": "result_id", "prescriptions": "prescription_id",
    "dispensing": "dispensing_id", "invoices": "invoice_id",
    "invoice_lines": "line_id", "payments": "payment_id",
    "claims": "claim_id", "claim_lines": "claim_line_id",
    "claim_events": "event_id", "shifts": "shift_id",
    "attendance": "attendance_id", "inventory_movements": "movement_id",
    "purchase_orders": "po_id", "feedback": "feedback_id",
    "incidents": "incident_id",
}

# Dimensions before facts; patients before all clinical facts.
PROCESS_ORDER: list[str] = [
    "dim_hospital", "dim_specialty", "dim_payer", "dim_supplier",
    "dim_diagnosis", "dim_lab_test", "dim_service", "dim_medication",
    "dim_department", "dim_doctor", "dim_staff", "dim_bed",
    "dim_procedure", "dim_inventory_item", "dim_date", "dim_time",
    "patients", "appointments", "encounters", "admissions", "transfers",
    "bed_snapshots", "procedures", "lab_orders", "lab_results",
    "prescriptions", "dispensing", "invoices", "invoice_lines", "payments",
    "claims", "claim_lines", "claim_events", "shifts", "attendance",
    "inventory_movements", "purchase_orders", "feedback", "incidents",
]

FOREIGN_KEYS: dict[str, list[tuple[str, str]]] = {
    "dim_department": [("hospital_id", "dim_hospital"), ("specialty_id", "dim_specialty")],
    "dim_doctor": [("hospital_id", "dim_hospital"), ("department_id", "dim_department"), ("specialty_id", "dim_specialty")],
    "dim_staff": [("hospital_id", "dim_hospital"), ("department_id", "dim_department")],
    "dim_bed": [("hospital_id", "dim_hospital")],
    "dim_procedure": [("specialty_id", "dim_specialty")],
    "dim_inventory_item": [("supplier_id", "dim_supplier")],
    "appointments": [("patient_id", "patients"), ("hospital_id", "dim_hospital"), ("department_id", "dim_department"), ("doctor_id", "dim_doctor")],
    "encounters": [("patient_id", "patients"), ("appointment_id", "appointments"), ("hospital_id", "dim_hospital"), ("department_id", "dim_department")],
    "admissions": [("encounter_id", "encounters"), ("patient_id", "patients"), ("hospital_id", "dim_hospital"), ("department_id", "dim_department"), ("bed_id", "dim_bed")],
    "transfers": [("admission_id", "admissions"), ("patient_id", "patients"), ("hospital_id", "dim_hospital")],
    "bed_snapshots": [("hospital_id", "dim_hospital"), ("bed_id", "dim_bed")],
    "procedures": [("patient_id", "patients"), ("encounter_id", "encounters"), ("hospital_id", "dim_hospital"), ("department_id", "dim_department"), ("surgeon_id", "dim_doctor"), ("procedure_code", "dim_procedure")],
    "lab_orders": [("patient_id", "patients"), ("encounter_id", "encounters"), ("hospital_id", "dim_hospital"), ("ordering_department", "dim_department"), ("test_code", "dim_lab_test")],
    "lab_results": [("lab_order_id", "lab_orders"), ("patient_id", "patients"), ("test_code", "dim_lab_test")],
    "prescriptions": [("patient_id", "patients"), ("encounter_id", "encounters"), ("hospital_id", "dim_hospital"), ("medication_code", "dim_medication")],
    "dispensing": [("prescription_id", "prescriptions"), ("hospital_id", "dim_hospital")],
    "invoices": [("encounter_id", "encounters"), ("patient_id", "patients"), ("hospital_id", "dim_hospital"), ("payer_id", "dim_payer")],
    "invoice_lines": [("invoice_id", "invoices"), ("service_code", "dim_service")],
    "payments": [("invoice_id", "invoices"), ("patient_id", "patients")],
    "claims": [("invoice_id", "invoices"), ("patient_id", "patients"), ("hospital_id", "dim_hospital"), ("payer_id", "dim_payer")],
    "claim_lines": [("claim_id", "claims")],
    "claim_events": [("claim_id", "claims")],
    "shifts": [("staff_id", "dim_staff"), ("hospital_id", "dim_hospital"), ("department_id", "dim_department")],
    "attendance": [("shift_id", "shifts"), ("staff_id", "dim_staff")],
    "inventory_movements": [("hospital_id", "dim_hospital"), ("item_id", "dim_inventory_item"), ("supplier_id", "dim_supplier")],
    "purchase_orders": [("hospital_id", "dim_hospital"), ("supplier_id", "dim_supplier")],
    "feedback": [("patient_id", "patients"), ("hospital_id", "dim_hospital"), ("department_id", "dim_department")],
    "incidents": [("hospital_id", "dim_hospital"), ("department_id", "dim_department")],
}

# FKs whose absence is an intentional, documented DQ-injection ("missing_payer")
# or is explicitly nullable in schema.py.  Kept as null with a warning.
NULLABLE_FKS: set[tuple[str, str]] = {
    ("encounters", "appointment_id"),
    ("invoices", "payer_id"),
    ("claims", "payer_id"),
    ("invoices", "encounter_id"),
}

REQUIRED_DATES: dict[str, list[str]] = {
    "patients": ["registration_date"],
    "appointments": ["booking_date", "appointment_date"],
    "encounters": ["arrival_datetime"],
    "admissions": ["admission_datetime"],
    "transfers": ["transfer_datetime"],
    "bed_snapshots": ["snapshot_datetime"],
    "procedures": ["scheduled_start"],
    "lab_orders": ["ordered_at"],
    "prescriptions": ["prescribed_date"],
    # dispensing.dispensed_date is intentionally NULL when status='Pending'
    # (the generator emits no dispensing date for un-dispensed prescriptions).
    "invoices": ["invoice_date"],
    "payments": ["payment_date"],
    "claims": ["claim_date"],
    "claim_events": ["event_date"],
    "shifts": ["shift_date"],
    "attendance": ["attendance_date"],
    "inventory_movements": ["movement_date"],
    "purchase_orders": ["order_date"],
    "feedback": ["visit_date"],
    "incidents": ["incident_date"],
    "dim_date": ["full_date"],
}

# Intra-table date ordering: (left must be >= right, rule reason)
DATE_ORDER_INTRA: dict[str, list[tuple[str, str, str]]] = {
    "appointments": [("appointment_date", "booking_date", "appointment_date before booking_date")],
    "encounters": [
        ("triage_datetime", "arrival_datetime", "triage_datetime before arrival_datetime"),
        ("provider_datetime", "triage_datetime", "provider_datetime before triage_datetime"),
        ("disposition_datetime", "provider_datetime", "disposition_datetime before provider_datetime"),
    ],
    "admissions": [("discharge_datetime", "admission_datetime", "discharge_datetime before admission_datetime")],
    "procedures": [("actual_end", "actual_start", "actual_end before actual_start")],
    "incidents": [("resolution_date", "incident_date", "resolution_date before incident_date")],
    "purchase_orders": [("received_date", "order_date", "received_date before order_date")],
}

# Cross-table date ordering: (child, child_date, parent, parent_date, fk, reason)
DATE_ORDER_CROSS: list[tuple[str, str, str, str, str, str]] = [
    ("payments", "payment_date", "invoices", "invoice_date", "invoice_id", "payment_date before invoice_date"),
    ("lab_results", "result_at", "lab_orders", "ordered_at", "lab_order_id", "result_at before ordered_at"),
    ("transfers", "transfer_datetime", "admissions", "admission_datetime", "admission_id", "transfer_datetime before admission_datetime"),
    ("dispensing", "dispensed_date", "prescriptions", "prescribed_date", "prescription_id", "dispensed_date before prescribed_date"),
    ("claims", "claim_date", "invoices", "invoice_date", "invoice_id", "claim_date before invoice_date"),
    ("claim_events", "event_date", "claims", "claim_date", "claim_id", "event_date before claim_date"),
]

NONNEGATIVE_COLUMNS = {
    "beds", "lead_days", "sla_minutes", "reorder_level", "waiting_minutes", "treatment_minutes", "los_days", "boarding_hours",
    "duration_minutes", "delay_minutes", "tat_minutes", "processing_days",
    "investigation_days", "resolution_days", "scheduled_hours", "actual_hours",
    "overtime_hours", "hours_worked", "quantity_dispensed",
    "gross_amount", "discount_amount", "net_amount", "paid_amount",
    "balance_amount", "amount", "claim_amount", "approved_amount",
    "line_amount", "unit_price", "unit_cost", "hourly_rate", "total_amount",
    "procurement_value", "revenue",
}
DURATION_COLUMNS = {
    "waiting_minutes", "treatment_minutes", "los_days", "boarding_hours",
    "duration_minutes", "delay_minutes", "tat_minutes", "processing_days",
    "investigation_days", "resolution_days", "scheduled_hours", "actual_hours",
    "overtime_hours", "hours_worked", "lead_days",
}

STATUS_MAP: dict[str, str] = {
    "completed": "Completed", "complete": "Completed", "done": "Completed",
    "cancelled": "Cancelled", "canceled": "Cancelled",
    "no-show": "No-show", "no show": "No-show", "noshow": "No-show",
    "scheduled": "Scheduled", "pending": "Pending", "final": "Final",
    "approved": "Approved", "denied": "Denied", "under review": "Under Review",
    "appealed": "Appealed", "paid": "Paid", "partial": "Partial",
    "overdue": "Overdue", "unpaid": "Unpaid", "settled": "Settled",
    "refund": "Refund", "payment": "Payment", "cleared": "Cleared",
    "failed": "Failed", "resolved": "Resolved", "open": "Open",
    "in progress": "In Progress", "investigating": "Investigating",
    "closed": "Closed", "active": "Active", "inactive": "Inactive",
    "on leave": "On Leave", "full-time": "Full-time", "part-time": "Part-time",
    "contract": "Contract", "present": "Present", "absent": "Absent",
    "late": "Late", "leave": "Leave", "received": "Received",
    "delayed": "Delayed", "return": "Return", "waste": "Waste",
    "expiry": "Expiry", "issue": "Issue", "receipt": "Receipt",
    "adjustment": "Adjustment", "transfer": "Transfer", "normal": "Normal",
    "high": "High", "low": "Low", "critical": "Critical", "medium": "Medium",
    "n/a": "N/A", "none": "N/A", "null": "N/A",
}
CANONICAL_STATUSES = set(STATUS_MAP.values()) | {
    "Elective", "Emergency", "Transfer", "Recovered", "Referred", "Deceased",
    "Against Advice", "Discharge", "Admit", "LWBS", "Walk-in", "Ambulance",
    "Referral", "Outpatient", "Inpatient", "New", "Follow-up",
    "Routine", "Urgent", "STAT", "Returning", "Male", "Female", "Other",
    "Consultant", "Specialist", "Resident", "Nurse", "Technician", "Admin",
    "Positive", "Neutral", "Negative", "Survey", "Complaint", "Suggestion",
    "Fall", "Medication", "Infection", "Safety",
}

HOSPITAL_RE = re.compile(r"^H(?:0[1-9]|10)$")


# ---------------------------------------------------------------------------
# Type coercion helpers
# ---------------------------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _as_string(series: pd.Series) -> pd.Series:
    out = series.astype("string").str.strip()
    return out.replace("", pd.NA)


def _as_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def _as_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("float64")


def _as_bool(series: pd.Series) -> pd.Series:
    truthy = {"1", "true", "t", "yes", "y"}
    falsy = {"0", "false", "f", "no", "n"}
    values: list[Any] = []
    for value in series:
        if pd.isna(value) or str(value).strip() == "":
            values.append(pd.NA)
            continue
        token = str(value).strip().lower()
        if token in truthy:
            values.append(True)
        elif token in falsy:
            values.append(False)
        else:
            values.append(pd.NA)
    return pd.Series(values, index=series.index, dtype="boolean")


def _as_datetime(series: pd.Series) -> pd.Series:
    """Parse into datetime64[ns], tolerating mixed ISO representations."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except (ValueError, TypeError):
        return pd.to_datetime(series, errors="coerce")


def _as_date(series: pd.Series) -> pd.Series:
    parsed = _as_datetime(series)
    return pd.Series([d.date() if pd.notna(d) else None for d in parsed],
                     index=series.index, dtype="object")


def normalise_status(value: Any) -> str | None:
    """Return the canonical status label for a single value.

    Nulls and blank strings return ``None``.  Known aliases (``COMPLETED ``,
    ``No Show``, ``Canceled`` ...) are mapped to their documented canonical
    form; unknown labels are title-cased and left for DQ rules to flag.
    """
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    text = re.sub(r"\s+", " ", str(value).strip())
    if not text:
        return None
    return STATUS_MAP.get(text.lower(), text.title())


def _normalise_status(series: pd.Series) -> tuple[pd.Series, int]:
    values: list[Any] = []
    invalid = 0
    for value in series:
        canon = normalise_status(value)
        if canon is None:
            values.append(pd.NA)
            continue
        values.append(canon)
        if canon not in CANONICAL_STATUSES:
            invalid += 1
    return pd.Series(values, index=series.index, dtype="string"), invalid


def _normalise_hospital(series: pd.Series) -> pd.Series:
    values: list[Any] = []
    for value in series:
        if pd.isna(value) or str(value).strip() == "":
            values.append(pd.NA)
        else:
            values.append(str(value).strip().upper())
    return pd.Series(values, index=series.index, dtype="string")


def _json_safe(value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if pd.isna(value):
        return None
    return value


# ---------------------------------------------------------------------------
# Silver cleaning for a single table
# ---------------------------------------------------------------------------
def clean_table(
    table: str,
    raw: pd.DataFrame,
    cleaned: dict[str, pd.DataFrame],
    run_id: str,
    quarantine: list[dict[str, Any]],
    source_file: str,
) -> dict[str, Any]:
    """Clean one table, append quarantine records and return its report."""
    columns = schema.columns(table)
    df = raw.copy()
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[columns].copy()

    dtypes = schema.dtypes(table)
    for col, dtype in dtypes.items():
        if dtype == "string":
            df[col] = _as_string(df[col])
        elif dtype == "int64":
            df[col] = _as_int(df[col])
        elif dtype == "float64":
            df[col] = _as_float(df[col])
        elif dtype == "bool":
            df[col] = _as_bool(df[col])
        elif dtype == "datetime64[ns]":
            df[col] = _as_datetime(df[col])
        elif dtype == "date":
            df[col] = _as_date(df[col])

    # --- standardisation --------------------------------------------------
    status_invalid_count = 0
    for col in columns:
        if col == "status" or col.endswith("_status"):
            df[col], n = _normalise_status(df[col])
            status_invalid_count += n
    if "hospital_id" in df.columns:
        df["hospital_id"] = _normalise_hospital(df["hospital_id"])

    raw_snapshot = df.copy(deep=True)
    input_rows = len(df)
    failures: dict[int, list[tuple[str, str]]] = {}
    rule_failures: dict[str, int] = {}

    def fail(mask: pd.Series, rule_id: str, reason_fn: Any) -> None:
        if mask is None or len(mask) != len(df):
            return
        for idx in df.index[mask.fillna(False)]:
            failures.setdefault(idx, []).append((rule_id, reason_fn(idx)))
        rule_failures[rule_id] = rule_failures.get(rule_id, 0) + int(mask.sum())

    # --- primary key ------------------------------------------------------
    pk = PRIMARY_KEYS.get(table)
    if pk and pk in df.columns:
        null_pk = df[pk].isna()
        fail(null_pk, "PK_NULL", lambda i: f"{pk} is null or empty")
        dup = df[pk].duplicated(keep="first") & df[pk].notna()
        fail(dup, "PK_DUPLICATE", lambda i: f"Duplicate {pk}={df.at[i, pk]!r}; first row retained")

    # --- hospital codes ---------------------------------------------------
    if "hospital_id" in df.columns:
        missing = df["hospital_id"].isna()
        fail(missing, "HOSPITAL_ID_MISSING", lambda i: "hospital_id is required")
        invalid = df["hospital_id"].notna() & ~df["hospital_id"].map(
            lambda v: bool(HOSPITAL_RE.fullmatch(str(v))) if pd.notna(v) else True
        )
        fail(invalid, "HOSPITAL_ID_INVALID",
             lambda i: f"hospital_id={df.at[i, 'hospital_id']!r} is not H01..H10")

    # --- required dates ---------------------------------------------------
    for col in REQUIRED_DATES.get(table, []):
        if col in df.columns:
            fail(df[col].isna(), "REQUIRED_DATE_INVALID",
                 lambda i, c=col: f"Required date {c} is null or unparseable")

    # --- intra-table date ordering ---------------------------------------
    for left, right, reason in DATE_ORDER_INTRA.get(table, []):
        if left not in df.columns or right not in df.columns:
            continue
        l = _as_datetime(df[left])
        r = _as_datetime(df[right])
        bad = l.notna() & r.notna() & (l < r)
        fail(bad, "DATE_ORDER_INVALID", lambda i, msg=reason: msg)

    # --- numeric ranges ---------------------------------------------------
    for col, dtype in dtypes.items():
        if dtype not in ("int64", "float64") or col not in df.columns:
            continue
        values = df[col]
        if col == "quantity" and table == "inventory_movements":
            continue  # signed stock movement by design
        if col == "amount" and table == "payments":
            refund = df["payment_type"].astype("string").str.lower().eq("refund") if "payment_type" in df else pd.Series(False, index=df.index)
            bad = values.notna() & (values < 0) & ~refund.fillna(False)
            fail(bad, "NEGATIVE_AMOUNT",
                 lambda i, c=col: f"{c}={df.at[i, c]} is negative but payment_type is not Refund")
            continue
        if col in NONNEGATIVE_COLUMNS:
            rule = "NEGATIVE_DURATION" if col in DURATION_COLUMNS else "NEGATIVE_AMOUNT"
            bad = values.notna() & (values < 0)
            fail(bad, rule, lambda i, c=col: f"{c}={df.at[i, c]} must not be negative")
        if col == "rating":
            bad = values.notna() & ((values < 1) | (values > 5))
            fail(bad, "NUMERIC_OUT_OF_RANGE", lambda i, c=col: f"rating must be 1..5, got {df.at[i, c]}")
        if col == "nps_score":
            bad = values.notna() & ((values < 0) | (values > 10))
            fail(bad, "NUMERIC_OUT_OF_RANGE", lambda i, c=col: f"nps_score must be 0..10, got {df.at[i, c]}")
        if col == "reliability_score":
            bad = values.notna() & ((values < 0) | (values > 1))
            fail(bad, "NUMERIC_OUT_OF_RANGE", lambda i, c=col: f"reliability_score must be 0..1, got {df.at[i, c]}")

    # --- foreign keys (parents were cleaned earlier in PROCESS_ORDER) -----
    for col, parent in FOREIGN_KEYS.get(table, []):
        if col not in df.columns:
            continue
        if parent not in cleaned:
            continue
        parent_pk = PRIMARY_KEYS[parent]
        if parent_pk not in cleaned[parent].columns:
            continue
        valid_keys = set(cleaned[parent][parent_pk].dropna().tolist())
        present = df[col].notna()
        orphan = present & ~df[col].isin(valid_keys)
        fail(orphan, "FK_ORPHAN",
             lambda i, c=col, p=parent: f"{c}={df.at[i, c]!r} has no {p} record")
        if (table, col) in NULLABLE_FKS:
            rule_failures["NULL_FK"] = rule_failures.get("NULL_FK", 0) + int((~present).sum())

    # --- cross-table timelines --------------------------------------------
    for child, child_date, parent, parent_date, fk, reason in DATE_ORDER_CROSS:
        if child != table or child_date not in df.columns or fk not in df.columns:
            continue
        if parent not in cleaned or parent_date not in cleaned[parent].columns:
            continue
        parent_pk = PRIMARY_KEYS[parent]
        lookup = cleaned[parent].set_index(parent_pk)[parent_date]
        parent_values = df[fk].map(lookup)
        c = _as_datetime(df[child_date])
        p = _as_datetime(pd.Series(parent_values, index=df.index))
        bad = c.notna() & p.notna() & (c < p)
        fail(bad, "DATE_ORDER_INVALID", lambda i, msg=reason: msg)

    # --- status warnings (kept, normalised) -------------------------------
    if status_invalid_count:
        rule_failures["STATUS_INVALID"] = rule_failures.get("STATUS_INVALID", 0) + status_invalid_count

    # --- remove failed rows and emit quarantine records -------------------
    failed_idx = list(failures.keys())
    clean = df.drop(index=failed_idx).copy() if failed_idx else df.copy()

    for idx, reasons in failures.items():
        original = raw_snapshot.loc[idx]
        record_json = json.dumps(
            {c: _json_safe(original[c]) for c in columns}, default=str, ensure_ascii=False
        )
        pk_value = df.at[idx, pk] if pk and pk in df.columns else None
        for rule_id, reason in reasons:
            severity = RULES.get(rule_id, {}).get("severity", "error")
            quarantine.append({
                "quarantine_id": f"Q_{run_id}_{table}_{idx}_{rule_id}",
                "rule_id": rule_id,
                "failure_reason": reason,
                "severity": severity,
                "timestamp": _now(),
                "pipeline_run_id": run_id,
                "table": table,
                "source_file": source_file,
                "record_id": str(_json_safe(pk_value)) if pk_value is not None else None,
                "record_json": record_json,
                "original_row": json.loads(record_json),
            })

    out_path = Path(config.SILVER_DIR) / f"{table}.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(out_path, index=False)

    return {
        "table": table,
        "input_rows": input_rows,
        "output_rows": len(clean),
        "quarantined_rows": len(set(failed_idx)),
        "quarantine_records": sum(len(v) for v in failures.values()),
        "rule_failures": rule_failures,
        "source_file": source_file,
        "output_path": str(out_path),
    }


def write_quarantine(
    records: list[dict[str, Any]], run_id: str,
    quarantine_dir: Path | None = None,
) -> dict[str, Any]:
    """Persist quarantine records as both parquet and JSONL."""
    target = Path(quarantine_dir) if quarantine_dir is not None else Path(config.QUARANTINE_DIR)
    target.mkdir(parents=True, exist_ok=True)
    jsonl_path = target / f"quarantine_{run_id}.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")

    if records:
        flat = []
        for record in records:
            flat.append({k: v for k, v in record.items() if k != "original_row"})
        frame = pd.DataFrame(flat)
        for col in ("timestamp",):
            if col in frame.columns:
                frame[col] = pd.to_datetime(frame[col], errors="coerce")
    else:
        frame = pd.DataFrame(columns=[
            "quarantine_id", "rule_id", "failure_reason", "severity", "timestamp",
            "pipeline_run_id", "table", "source_file", "record_id", "record_json",
        ])
    parquet_path = target / f"quarantine_{run_id}.parquet"
    frame.to_parquet(parquet_path, index=False)
    return {
        "records": len(records),
        "rows": len({r["quarantine_id"].rsplit("_", 1)[0] for r in records}) if records else 0,
        "parquet": str(parquet_path),
        "jsonl": str(jsonl_path),
        "by_rule": {r: sum(1 for x in records if x["rule_id"] == r)
                    for r in sorted({x["rule_id"] for x in records})},
        "by_table": {t: sum(1 for x in records if x["table"] == t)
                     for t in sorted({x["table"] for x in records})},
    }


def clean_all(
    raw_frames: dict[str, pd.DataFrame],
    bronze_manifest: dict[str, Any],
    run_id: str,
    quarantine_dir: Path | None = None,
    silver_dir: Path | None = None,
) -> dict[str, Any]:
    """Clean every table in dependency order and return silver outputs."""
    silver_path = Path(silver_dir) if silver_dir is not None else Path(config.SILVER_DIR)
    silver_path.mkdir(parents=True, exist_ok=True)
    quarantine_records: list[dict[str, Any]] = []
    cleaned: dict[str, pd.DataFrame] = {}
    reports: list[dict[str, Any]] = []
    table_entries = bronze_manifest.get("tables", {})

    for table in PROCESS_ORDER:
        raw = raw_frames.get(table)
        if raw is None:
            # Build an empty canonical frame so every silver_* table exists.
            raw = pd.DataFrame({c: pd.Series(dtype="string") for c in schema.columns(table)})
        entry = table_entries.get(table, {})
        source_file = entry.get("file_name") or f"(missing:{table}.csv)"
        report = clean_table(table, raw, cleaned, run_id, quarantine_records, source_file)
        cleaned[table] = pd.read_parquet(report["output_path"])
        reports.append(report)

    quarantine_summary = write_quarantine(quarantine_records, run_id, quarantine_dir)
    source_rows = sum(r["input_rows"] for r in reports)
    valid_rows = sum(r["output_rows"] for r in reports)
    quarantined_rows = sum(r["quarantined_rows"] for r in reports)

    return {
        "tables": cleaned,
        "reports": reports,
        "quarantine_records": quarantine_records,
        "quarantine_summary": quarantine_summary,
        "source_rows": source_rows,
        "valid_rows": valid_rows,
        "quarantined_rows": quarantined_rows,
    }
