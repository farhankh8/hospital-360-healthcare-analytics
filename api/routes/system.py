"""Data quality, pipeline, explorer, glossary and metadata endpoints."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from api.core.config import DATA_PATH, ROOT
from api.core.db import get_conn, table_exists
from api.core.errors import FilterValidationError
from api.core.filters import parse_filters
from api.core.responses import envelope, table_envelope
from api.services.exports import (
    MAX_EXPORT_ROWS,
    csv_response,
    export_rows,
    invoke_export_route,
    resolve_export_route,
)
from api.services.query import columns, paginated_rows, query_rows

router = APIRouter(tags=["system"])

SNAPSHOT_KPI_IDS = {"hospitals_selected", "total_beds", "active_employees"}

EXPLORER_DATASETS = {
    "patients": "silver_patients",
    "appointments": "silver_appointments",
    "encounters": "silver_encounters",
    "admissions": "silver_admissions",
    "transfers": "silver_transfers",
    "bed-snapshots": "silver_bed_snapshots",
    "procedures": "silver_procedures",
    "lab-orders": "silver_lab_orders",
    "lab-results": "silver_lab_results",
    "prescriptions": "silver_prescriptions",
    "dispensing": "silver_dispensing",
    "invoices": "silver_invoices",
    "invoice-lines": "silver_invoice_lines",
    "payments": "silver_payments",
    "claims": "silver_claims",
    "claim-lines": "silver_claim_lines",
    "claim-events": "silver_claim_events",
    "shifts": "silver_shifts",
    "attendance": "silver_attendance",
    "inventory-movements": "silver_inventory_movements",
    "purchase-orders": "silver_purchase_orders",
    "feedback": "silver_feedback",
    "incidents": "silver_incidents",
    "hospitals": "dim_hospital",
    "departments": "silver_dim_department",
    "doctors": "silver_dim_doctor",
    "staff": "silver_dim_staff",
}


def _empty(data: Any, request: Request, **extra: Any) -> dict[str, Any]:
    f = parse_filters(request)
    return envelope(data, f.date_from, f.date_to, f.hospital_ids, **extra)


def _card(kpi_id: str, label: str, value: Any, unit: str = "count",
          definition: str = "", higher: bool = True) -> dict[str, Any]:
    """Build a KPI card in the same shape as build_kpis for system pages."""
    return {
        "id": kpi_id, "label": label, "value": value, "previous": None,
        "change_pct": None, "trend": "flat", "favourable": "flat", "unit": unit,
        "precision": 2 if isinstance(value, float) else 0, "sparkline": [],
        "definition": definition, "higher_is_better": higher,
    }


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------
OPTION_SOURCES: dict[str, tuple[str, str, str, str | None]] = {
    "doctors": ("dim_doctor", "doctor_id", "doctor_name", None),
    "appointment_types": ("silver_appointments", "appointment_type", "appointment_type", None),
    "booking_channels": ("silver_appointments", "booking_channel", "booking_channel", None),
    "statuses": ("silver_appointments", "status", "status", None),
    "triage_categories": ("silver_encounters", "triage_category", "triage_category", None),
    "dispositions": ("silver_encounters", "disposition", "disposition", None),
    "arrival_modes": ("silver_encounters", "arrival_mode", "arrival_mode", None),
    "wards": ("silver_admissions", "ward", "ward", None),
    "bed_types": ("silver_bed_snapshots", "bed_type", "bed_type", None),
    "admission_types": ("silver_admissions", "admission_type", "admission_type", None),
    "discharge_types": ("silver_admissions", "discharge_status", "discharge_status", None),
    "or_rooms": ("silver_procedures", "or_room", "or_room", None),
    "procedure_codes": ("silver_procedures", "procedure_code", "procedure_code", None),
    "elective_emergency": ("silver_procedures", "elective_emergency", "elective_emergency", None),
    "priorities": ("silver_lab_orders", "priority", "priority", None),
    "test_codes": ("silver_lab_orders", "test_code", "test_code", None),
    "medication_codes": ("silver_prescriptions", "medication_code", "medication_code", None),
    "service_categories": ("silver_invoice_lines", "service_category", "service_category", None),
    "invoice_statuses": ("silver_invoices", "invoice_status", "invoice_status", None),
    "payment_statuses": ("silver_invoices", "payment_status", "payment_status", None),
    "claim_types": ("silver_claims", "claim_type", "claim_type", None),
    "denial_reasons": ("silver_claims", "denial_reason", "denial_reason", None),
    "shift_types": ("silver_shifts", "shift_type", "shift_type", None),
    "categories": ("silver_incidents", "category", "category", None),
    "severities": ("silver_incidents", "severity", "severity", None),
    "resolution_statuses": ("silver_feedback", "resolution_status", "resolution_status", None),
    "feedback_types": ("silver_feedback", "feedback_type", "feedback_type", None),
    "sentiments": ("silver_feedback", "sentiment_label", "sentiment_label", None),
    "movement_types": ("silver_inventory_movements", "movement_type", "movement_type", None),
    "item_ids": ("silver_inventory_movements", "item_id", "item_id", None),
    "suppliers": ("silver_inventory_movements", "supplier_id", "supplier_id", None),
    "age_groups": ("silver_patients", "age_group", "age_group", None),
    "datasets": ("dq_rules", "table_name", "table_name", None),
    "dq_severities": ("dq_rules", "severity", "severity", None),
    "dq_categories": ("dq_rules", "category", "category", None),
    "pipeline_layers": ("lineage", "layer", "layer", None),
    "run_statuses": ("pipeline_runs", "status", "status", None),
    "roles": ("dim_staff", "role", "role", None),
    "employment_types": ("dim_staff", "employment_type", "employment_type", None),
}


@router.get("/filters/options")
def filter_options(request: Request):
    """Distinct, data-driven option lists for page-specific filters."""
    result: dict[str, Any] = {}
    with get_conn() as conn:
        for name, (table, value_col, label_col, predicate) in OPTION_SOURCES.items():
            if not table_exists(table):
                result[name] = []
                continue
            cols = columns(conn, table)
            if value_col not in cols:
                result[name] = []
                continue
            # Doctors/wards are labelled; all other options use the raw value.
            select = (
                f"DISTINCT {value_col} AS value, {label_col} AS label"
                if label_col in cols and label_col != value_col
                else f"DISTINCT {value_col} AS value, {value_col} AS label"
            )
            sql = f"SELECT {select} FROM {table}"
            if predicate:
                sql += f" WHERE {predicate}"
            sql += " ORDER BY value LIMIT 200"
            rows = query_rows(conn, sql)
            result[name] = [
                {"value": str(r["value"]), "label": str(r["label"])} for r in rows if r["value"] is not None
            ]
    return _empty(result, request)


@router.get("/data-quality/summary")
def dq_summary(request: Request):
    with get_conn() as conn:
        if not table_exists("dq_rules"):
            return _empty({"overall_score": None, "categories": [], "rules_total": 0,
                           "rules_passed": 0, "total_failures": 0}, request,
                          status="not_available")
        rows = query_rows(conn, "SELECT * FROM dq_rules")
    categories: dict[str, dict[str, Any]] = {}
    for r in rows:
        cat = r.get("category") or "Other"
        bucket = categories.setdefault(cat, {"category": cat, "rules": 0, "passed": 0, "failures": 0, "score": 0.0})
        bucket["rules"] += 1
        bucket["passed"] += 1 if r.get("passed") else 0
        checked = int(r.get("checked_count") or 0)
        failed = int(r.get("failed_count") or 0)
        score = 100.0 * (1 - failed / checked) if checked else (100.0 if r.get("passed") else 0.0)
        bucket["failures"] += failed
        bucket["score"] += score
    for bucket in categories.values():
        bucket["score"] = round(bucket["score"] / bucket["rules"], 2) if bucket["rules"] else None
    overall = round(sum(b["score"] or 0 for b in categories.values()) / len(categories), 2) if categories else None
    with get_conn() as conn:
        runs = query_rows(conn, "SELECT * FROM pipeline_runs ORDER BY start_time DESC LIMIT 1") if table_exists("pipeline_runs") else []
        failures = query_rows(
            conn,
            "SELECT f.rule_id, r.category, f.severity FROM dq_failures f "
            "LEFT JOIN dq_rules r ON r.rule_id = f.rule_id",
        ) if table_exists("dq_failures") else []
    latest = runs[0] if runs else {}
    source_records = int(latest.get("source_records") or 0)
    valid_records = int(latest.get("valid_records") or 0)
    quarantined = int(latest.get("quarantined_records") or 0)
    failed_rules = sum(1 for r in rows if not r.get("passed"))
    by_rule = lambda needle: sum(1 for f in failures if needle in (f.get("rule_id") or "").upper())
    by_category = lambda needle: sum(1 for f in failures if needle in (f.get("category") or "").lower())
    kpis = {
        "total_records_processed": _card("total_records_processed", "Total Records Processed", source_records, definition="Source records in the latest pipeline run."),
        "valid_records": _card("valid_records", "Valid Records", valid_records, definition="Records accepted into the silver layer."),
        "invalid_records": _card("invalid_records", "Invalid Records", quarantined, definition="Records rejected to quarantine.", higher=False),
        "data_quality_score": _card("data_quality_score", "Data Quality Score", overall, "score", "Mean weighted pass rate across DQ categories."),
        "duplicate_records": _card("duplicate_records", "Duplicate Records", by_rule("DUP") + by_category("uniqueness"), definition="Uniqueness-rule failures in the latest run.", higher=False),
        "missing_values": _card("missing_values", "Missing Values", by_rule("NOT_NULL") + by_category("completeness"), definition="Completeness-rule failures in the latest run.", higher=False),
        "referential_integrity_violations": _card("referential_integrity_violations", "Referential Integrity Violations", by_category("referential"), definition="Failures where a referenced key is missing.", higher=False),
        "invalid_dates": _card("invalid_dates", "Invalid Dates", by_rule("DATE"), definition="Date-format and date-order rule failures.", higher=False),
        "failed_checks": _card("failed_checks", "Failed Checks", failed_rules, definition="DQ rules that failed in the latest run.", higher=False),
        "quarantined_records": _card("quarantined_records", "Quarantined Records", quarantined, definition="Records held in the quarantine layer.", higher=False),
    }
    return _empty({
        "overall_score": overall,
        "categories": list(categories.values()),
        "rules_total": len(rows),
        "rules_passed": sum(1 for r in rows if r.get("passed")),
        "total_failures": sum(int(r.get("failed_count") or 0) for r in rows),
        "kpis": kpis,
    }, request)


@router.get("/data-quality/rules")
def dq_rules(request: Request):
    with get_conn() as conn:
        rows = query_rows(conn, "SELECT rule_id, rule_name, table_name AS dataset, category, severity, "
                          "description, passed, failed_count, checked_count, checked_at, "
                          "CASE WHEN passed THEN 'Pass' ELSE 'Fail' END AS status "
                          "FROM dq_rules ORDER BY category, rule_id") if table_exists("dq_rules") else []
    return _empty(rows, request)


@router.get("/data-quality/failures")
def dq_failures(request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        if not table_exists("dq_failures"):
            return table_envelope([], 0, f.page, f.page_size, f.applied())
        total = int(query_rows(conn, "SELECT COUNT(*) AS n FROM dq_failures")[0]["n"])
        rows = query_rows(
            conn,
            "SELECT failure_id AS validation_id, table_name AS dataset, record_id, rule_id, "
            "failure_reason, severity, detected_at, pipeline_run_id AS run_id, 'Open' AS resolution_status "
            "FROM dq_failures ORDER BY detected_at DESC, failure_id ASC LIMIT $limit OFFSET $offset",
            {"limit": f.page_size, "offset": (f.page - 1) * f.page_size},
        )
    return table_envelope(rows, total, f.page, f.page_size, f.applied())


@router.get("/data-quality/datasets")
def dq_datasets(request: Request):
    with get_conn() as conn:
        if not table_exists("dq_rules"):
            return _empty([], request)
        rows = query_rows(
            conn,
            "SELECT table_name AS dataset, SUM(checked_count) AS records, "
            "SUM(checked_count - failed_count) AS valid_records, SUM(failed_count) AS invalid_records, "
            "ROUND(AVG(CASE WHEN checked_count > 0 THEN 100.0 * (1 - failed_count * 1.0 / checked_count) "
            "ELSE CASE WHEN passed THEN 100.0 ELSE 0.0 END END), 2) AS quality_score, "
            "CASE WHEN SUM(failed_count) > 0 THEN 'Issues found' ELSE 'Pass' END AS status "
            "FROM dq_rules GROUP BY table_name ORDER BY table_name",
        )
    return _empty(rows, request)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
@router.get("/pipeline/runs")
def pipeline_runs(request: Request):
    with get_conn() as conn:
        rows = query_rows(conn, "SELECT * FROM pipeline_runs ORDER BY start_time DESC") if table_exists("pipeline_runs") else []
    return _empty(rows, request)


@router.get("/pipeline/summary")
def pipeline_summary(request: Request):
    """Blueprint pipeline KPI cards for the latest run and manifest."""
    with get_conn() as conn:
        runs = query_rows(conn, "SELECT * FROM pipeline_runs ORDER BY start_time DESC") if table_exists("pipeline_runs") else []
    latest = runs[0] if runs else {}
    successful = next((r for r in runs if str(r.get("status", "")).lower() == "success"), {})
    manifest_dir = DATA_PATH / "manifests"
    files = sorted(manifest_dir.glob("pipeline_*.json")) if manifest_dir.exists() else []
    manifest: dict[str, Any] = {}
    if files:
        try:
            manifest = json.loads(files[-1].read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            manifest = {}
    bronze = manifest.get("bronze") or {}
    gold = manifest.get("gold") or {}
    totals = manifest.get("totals") or {}
    kpis = {
        "latest_run": _card("latest_run", "Latest Run", latest.get("run_id", "N/A"), "text", "Most recent pipeline execution."),
        "total_source_records": _card("total_source_records", "Total Source Records", int(latest.get("source_records") or totals.get("source_records") or 0)),
        "bronze_records": _card("bronze_records", "Bronze Records", int(bronze.get("total_rows") or 0)),
        "silver_records": _card("silver_records", "Silver Records", int(latest.get("valid_records") or totals.get("valid_records") or 0)),
        "gold_records": _card("gold_records", "Gold Records", sum(int(v or 0) for v in (gold.get("row_counts") or {}).values())),
        "valid_records": _card("valid_records", "Valid Records", int(latest.get("valid_records") or 0)),
        "quarantined_records": _card("quarantined_records", "Quarantined Records", int(latest.get("quarantined_records") or 0), higher=False),
        "processing_duration": _card("processing_duration", "Processing Duration", round(float(latest.get("duration_seconds") or 0), 2), "seconds", "Wall-clock duration of the latest run.", higher=False),
        "failed_stages": _card("failed_stages", "Failed Stages", sum(1 for r in runs if str(r.get("status", "")).lower() not in {"success", "succeeded"}), definition="Pipeline runs with a non-success status.", higher=False),
        "last_successful_run": _card("last_successful_run", "Last Successful Run", successful.get("run_id", "N/A"), "text", "Most recent successful pipeline execution."),
    }
    return _empty(kpis, request)


def _load_pipeline_manifest(run_id: str) -> dict[str, Any] | None:
    manifest_dir = DATA_PATH / "manifests"
    if not manifest_dir.exists():
        return None
    # Direct match first, then scan.
    direct = manifest_dir / f"pipeline_{run_id}.json"
    candidates = [direct] if direct.exists() else sorted(manifest_dir.glob("pipeline_*.json"))
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if str(payload.get("run_id") or "") == run_id:
            payload["_manifest_file"] = path.name
            return payload
    return None


def _run_table_counts(manifest: dict[str, Any]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for name, info in ((manifest.get("bronze") or {}).get("tables") or {}).items():
        row = counts.setdefault(str(name), {"source": 0, "bronze": 0, "silver": 0, "gold": 0, "quarantined": 0, "valid": 0})
        row["bronze"] = int((info or {}).get("row_count") or 0)
        row["source"] = max(row["source"], row["bronze"])
    for report in ((manifest.get("silver") or {}).get("reports") or []):
        name = str((report or {}).get("table") or "")
        if not name:
            continue
        row = counts.setdefault(name, {"source": 0, "bronze": 0, "silver": 0, "gold": 0, "quarantined": 0, "valid": 0})
        row["source"] = max(row["source"], int((report or {}).get("input_rows") or 0))
        row["silver"] = int((report or {}).get("output_rows") or 0)
        row["valid"] = row["silver"]
        row["quarantined"] = int((report or {}).get("quarantined_rows") or 0)
    for name, value in (((manifest.get("gold") or {}).get("row_counts") or {}).items()):
        row = counts.setdefault(str(name), {"source": 0, "bronze": 0, "silver": 0, "gold": 0, "quarantined": 0, "valid": 0})
        row["gold"] = int(value or 0)
    return counts


@router.get("/pipeline/runs/compare")
def pipeline_runs_compare(request: Request, run_a: str = Query(...), run_b: str = Query(...)):
    with get_conn() as conn:
        if not table_exists("pipeline_runs"):
            raise HTTPException(404, "pipeline_runs not available")
        run_rows = query_rows(conn, "SELECT run_id, status, duration_seconds, source_records, valid_records, quarantined_records FROM pipeline_runs WHERE run_id IN ($a, $b)", {"a": run_a, "b": run_b})
    by_id = {str(r.get("run_id")): r for r in run_rows}
    missing = [rid for rid in [run_a, run_b] if rid not in by_id]
    if missing:
        raise HTTPException(422, f"Unknown run ID(s): {', '.join(missing)}")

    manifest_a = _load_pipeline_manifest(run_a) or {}
    manifest_b = _load_pipeline_manifest(run_b) or {}
    counts_a = _run_table_counts(manifest_a)
    counts_b = _run_table_counts(manifest_b)
    table_names = sorted(set(counts_a) | set(counts_b))
    table_deltas = []
    for name in table_names:
        a = counts_a.get(name, {"source": 0, "bronze": 0, "silver": 0, "gold": 0, "quarantined": 0, "valid": 0})
        b = counts_b.get(name, {"source": 0, "bronze": 0, "silver": 0, "gold": 0, "quarantined": 0, "valid": 0})
        delta = {k: int(b.get(k, 0)) - int(a.get(k, 0)) for k in ["source", "bronze", "silver", "gold", "quarantined", "valid"]}
        table_deltas.append({"table": name, "run_a": a, "run_b": b, "delta": delta})

    def _dq_score(manifest: dict[str, Any]) -> float | None:
        q = manifest.get("quality") or {}
        val = q.get("dq_score")
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    run_a_row, run_b_row = by_id[run_a], by_id[run_b]
    dq_a, dq_b = _dq_score(manifest_a), _dq_score(manifest_b)
    payload = {
        "run_a": {"run_id": run_a, "status": run_a_row.get("status"), "duration_seconds": run_a_row.get("duration_seconds"), "source_records": run_a_row.get("source_records"), "valid_records": run_a_row.get("valid_records"), "quarantined_records": run_a_row.get("quarantined_records"), "dq_score": dq_a},
        "run_b": {"run_id": run_b, "status": run_b_row.get("status"), "duration_seconds": run_b_row.get("duration_seconds"), "source_records": run_b_row.get("source_records"), "valid_records": run_b_row.get("valid_records"), "quarantined_records": run_b_row.get("quarantined_records"), "dq_score": dq_b},
        "deltas": {
            "duration_seconds": (float(run_b_row.get("duration_seconds") or 0) - float(run_a_row.get("duration_seconds") or 0)),
            "source_records": int(run_b_row.get("source_records") or 0) - int(run_a_row.get("source_records") or 0),
            "valid_records": int(run_b_row.get("valid_records") or 0) - int(run_a_row.get("valid_records") or 0),
            "quarantined_records": int(run_b_row.get("quarantined_records") or 0) - int(run_a_row.get("quarantined_records") or 0),
            "dq_score": (None if dq_a is None or dq_b is None else round(dq_b - dq_a, 4)),
        },
        "tables": table_deltas,
    }
    return _empty(payload, request)


@router.get("/pipeline/runs/{run_id}")
def pipeline_run(run_id: str, request: Request):
    with get_conn() as conn:
        rows = query_rows(conn, "SELECT * FROM pipeline_runs WHERE run_id = $run_id", {"run_id": run_id}) if table_exists("pipeline_runs") else []
    if not rows:
        raise HTTPException(404, f"Run {run_id} not found")
    row = dict(rows[0])
    manifest = _load_pipeline_manifest(run_id)
    if manifest:
        stages = []
        for stage_name in ["bronze", "silver", "quality", "gold"]:
            stage = manifest.get(stage_name)
            if isinstance(stage, dict):
                stages.append({"stage": stage_name, "status": "success" if stage else "unknown", "details": {k: v for k, v in stage.items() if k in ("source_rows", "valid_rows", "quarantined_rows", "row_counts", "dq_score", "tables", "reports")}})
            else:
                stages.append({"stage": stage_name, "status": "missing", "details": {}})
        row["stages"] = stages
        row["manifest_file"] = manifest.get("_manifest_file")
        row["dq_score"] = (manifest.get("quality") or {}).get("dq_score")
        row["has_errors"] = bool(row.get("error_message"))
    return _empty(row, request)


@router.get("/pipeline/manifest")
def pipeline_manifest(request: Request):
    manifest_dir = DATA_PATH / "manifests"
    files = sorted(manifest_dir.glob("pipeline_*.json")) if manifest_dir.exists() else []
    if not files:
        return _empty({}, request, status="not_available")
    try:
        payload = json.loads(files[-1].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        payload = {}
    return _empty(payload, request, manifest_file=files[-1].name)


@router.get("/pipeline/lineage")
def pipeline_lineage(request: Request):
    with get_conn() as conn:
        rows = query_rows(conn, "SELECT * FROM lineage ORDER BY target_table") if table_exists("lineage") else []
    return _empty(rows, request)


@router.get("/pipeline/lineage/{table_name}")
def pipeline_lineage_table(table_name: str, request: Request):
    with get_conn() as conn:
        if not table_exists("lineage"):
            raise HTTPException(404, "lineage not available")
        allowed = {str(r["target_table"]) for r in query_rows(conn, "SELECT DISTINCT target_table FROM lineage")}
        if table_name not in allowed:
            raise HTTPException(422, f"Unknown table_name: {table_name}")
        rows = query_rows(conn, "SELECT * FROM lineage WHERE target_table = $t", {"t": table_name})
        all_rows = query_rows(conn, "SELECT target_table, source_tables, layer FROM lineage")
    if not rows:
        raise HTTPException(404, f"No lineage for {table_name}")
    row = dict(rows[0])
    # Downstream: any lineage row whose source_tables references this table.
    downstream = []
    for r in all_rows:
        src = str(r.get("source_tables") or "")
        if table_name in src:
            downstream.append({"target_table": r.get("target_table"), "layer": r.get("layer")})
    row["downstream_tables"] = downstream
    # normalize source_tables to list when possible
    try:
        row["source_tables_list"] = json.loads(row.get("source_tables") or "[]")
    except (json.JSONDecodeError, TypeError):
        row["source_tables_list"] = [s.strip() for s in str(row.get("source_tables") or "").split(",") if s.strip()]
    return _empty(row, request)


# ---------------------------------------------------------------------------
# Explorer
# ---------------------------------------------------------------------------
@router.get("/explorer/datasets")
def explorer_datasets(request: Request):
    with get_conn() as conn:
        out = []
        for name, table in EXPLORER_DATASETS.items():
            try:
                n = int(query_rows(conn, f"SELECT COUNT(*) AS n FROM {table}")[0]["n"])
            except Exception:  # noqa: BLE001 - a dataset table may not exist in a partial build
                n = 0
            out.append({"id": name, "table": table, "label": name.replace("-", " ").title(), "row_count": n})
    return _empty(out, request)


def _explorer_table(dataset: str) -> str:
    if dataset not in EXPLORER_DATASETS:
        raise HTTPException(404, f"Unknown dataset: {dataset}")
    return EXPLORER_DATASETS[dataset]


@router.get("/explorer/{dataset}/records")
def explorer_records(dataset: str, request: Request):
    f = parse_filters(request)
    table = _explorer_table(dataset)
    with get_conn() as conn:
        cols = columns(conn, table)
        date_cols = [c for c in cols if c.endswith(("_date", "_at")) or c in {"month", "date"}]
        date_col = date_cols[0] if date_cols else "month"
        rows, total = paginated_rows(conn, table, f, date_col=date_col)
    return table_envelope(rows, total, f.page, f.page_size, f.applied(), dataset=dataset)


@router.get("/explorer/{dataset}/schema")
def explorer_schema(dataset: str, request: Request):
    table = _explorer_table(dataset)
    with get_conn() as conn:
        rows = conn.execute(f"DESCRIBE {table}").fetchall()
    schema = [{"column_name": r[0], "column_type": r[1], "nullable": r[2]} for r in rows]
    return _empty({"dataset": dataset, "table": table, "columns": schema}, request)


# ---------------------------------------------------------------------------
# Patient Journey (Phase 4)
# ---------------------------------------------------------------------------

def _json_safe(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return value


def _safe_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: _json_safe(v) for k, v in row.items()}


def _resolve_journey_patient(conn, patient_id: str | None, encounter_id: str | None, admission_id: str | None) -> str:
    if patient_id:
        row = query_rows(conn, "SELECT patient_id FROM silver_patients WHERE patient_id = $pid LIMIT 1", {"pid": patient_id})
        if not row:
            raise HTTPException(404, f"Patient not found: {patient_id}")
        return str(row[0]["patient_id"])
    if encounter_id:
        row = query_rows(conn, "SELECT patient_id FROM silver_encounters WHERE encounter_id = $eid LIMIT 1", {"eid": encounter_id})
        if not row:
            raise HTTPException(404, f"Encounter not found: {encounter_id}")
        return str(row[0]["patient_id"])
    if admission_id:
        row = query_rows(conn, "SELECT patient_id FROM silver_admissions WHERE admission_id = $aid LIMIT 1", {"aid": admission_id})
        if not row:
            raise HTTPException(404, f"Admission not found: {admission_id}")
        return str(row[0]["patient_id"])
    raise FilterValidationError("Provide patient_id, encounter_id, or admission_id.", {"parameter": "patient_id"})


_JOURNEY_EVENT_SOURCES: list[dict[str, Any]] = [
    {"type": "registration", "table": "silver_patients", "date_col": "registration_date", "id_col": "patient_id", "label": "Patient registration"},
    {"type": "appointment", "table": "silver_appointments", "date_col": "appointment_date", "id_col": "appointment_id", "label": "Appointment"},
    {"type": "encounter", "table": "silver_encounters", "date_col": "arrival_datetime", "id_col": "encounter_id", "label": "Encounter"},
    {"type": "admission", "table": "silver_admissions", "date_col": "admission_datetime", "id_col": "admission_id", "label": "Admission"},
    {"type": "transfer", "table": "silver_transfers", "date_col": "transfer_datetime", "id_col": "transfer_id", "label": "Transfer"},
    {"type": "procedure", "table": "silver_procedures", "date_col": "scheduled_start", "id_col": "procedure_id", "label": "Procedure"},
    {"type": "lab_order", "table": "silver_lab_orders", "date_col": "ordered_at", "id_col": "lab_order_id", "label": "Lab order"},
    {"type": "lab_result", "table": "silver_lab_results", "date_col": "result_at", "id_col": "result_id", "label": "Lab result"},
    {"type": "prescription", "table": "silver_prescriptions", "date_col": "prescribed_date", "id_col": "prescription_id", "label": "Prescription"},
    {"type": "dispensing", "table": "silver_dispensing", "date_col": "dispensed_date", "id_col": "dispensing_id", "label": "Dispensing"},
    {"type": "invoice", "table": "silver_invoices", "date_col": "invoice_date", "id_col": "invoice_id", "label": "Invoice"},
    {"type": "payment", "table": "silver_payments", "date_col": "payment_date", "id_col": "payment_id", "label": "Payment"},
    {"type": "claim", "table": "silver_claims", "date_col": "claim_date", "id_col": "claim_id", "label": "Claim"},
    {"type": "claim_event", "table": "silver_claim_events", "date_col": "event_date", "id_col": "event_id", "label": "Claim event"},
    {"type": "feedback", "table": "silver_feedback", "date_col": "visit_date", "id_col": "feedback_id", "label": "Feedback"},
]


def _journey_events(conn, patient_id: str, event_type: str | None, date_from: str | None, date_to: str | None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    allowed_types = {s["type"] for s in _JOURNEY_EVENT_SOURCES}
    if event_type and event_type not in allowed_types:
        raise FilterValidationError(f"Unknown event_type: {event_type}", {"parameter": "event_type", "allowed": sorted(allowed_types)})
    for src in _JOURNEY_EVENT_SOURCES:
        if event_type and src["type"] != event_type:
            continue
        table = src["table"]
        if not table_exists(table):
            continue
        cols = set(columns(conn, table))
        if "patient_id" not in cols:
            continue
        date_col = src["date_col"] if src["date_col"] in cols else None
        where = ["patient_id = $pid"]
        params: dict[str, Any] = {"pid": patient_id}
        if date_col and date_from:
            where.append(f"CAST({date_col} AS DATE) >= CAST($df AS DATE)")
            params["df"] = date_from
        if date_col and date_to:
            where.append(f"CAST({date_col} AS DATE) <= CAST($dt AS DATE)")
            params["dt"] = date_to
        sql = f"SELECT * FROM {table} WHERE {' AND '.join(where)}"
        if date_col:
            sql += f" ORDER BY {date_col} ASC"
        sql += " LIMIT 500"
        try:
            rows = query_rows(conn, sql, params)
        except Exception:  # noqa: BLE001, S112 - skip tables with unexpected shape
            continue
        for r in rows:
            sr = _safe_row(r)
            dt_val = sr.get(src["date_col"])
            events.append({
                "event_type": src["type"],
                "event_label": src["label"],
                "event_date": dt_val,
                "event_id": sr.get(src["id_col"]),
                "table": table,
                "detail": sr,
            })
    events.sort(key=lambda e: str(e.get("event_date") or ""))
    return events


@router.get("/journey/sample-patient")
def journey_sample_patient(request: Request):
    with get_conn() as conn:
        row = query_rows(conn, """
            SELECT patient_id, COUNT(*) AS n FROM (
              SELECT patient_id FROM silver_appointments
              UNION ALL SELECT patient_id FROM silver_encounters
              UNION ALL SELECT patient_id FROM silver_admissions
              UNION ALL SELECT patient_id FROM silver_invoices
              UNION ALL SELECT patient_id FROM silver_lab_orders
            ) t GROUP BY patient_id ORDER BY n DESC, patient_id ASC LIMIT 1
        """)
    pid = str(row[0]["patient_id"]) if row else None
    return _empty({"patient_id": pid}, request)


@router.get("/journey")
def patient_journey(request: Request):
    f = parse_filters(request)
    patient_id = request.query_params.get("patient_id")
    encounter_id = request.query_params.get("encounter_id")
    admission_id = request.query_params.get("admission_id")
    event_type = request.query_params.get("event_type")
    date_from = request.query_params.get("date_from") or f.date_from
    date_to = request.query_params.get("date_to") or f.date_to

    with get_conn() as conn:
        pid = _resolve_journey_patient(conn, patient_id, encounter_id, admission_id)
        patient_rows = query_rows(conn, "SELECT * FROM silver_patients WHERE patient_id = $pid LIMIT 1", {"pid": pid})
        patient = _safe_row(patient_rows[0]) if patient_rows else {"patient_id": pid}

        # Encounters summary
        enc_rows = query_rows(conn, """
            SELECT COUNT(*) AS encounter_count,
                   COUNT(DISTINCT hospital_id) AS hospitals_visited,
                   MIN(arrival_datetime) AS first_encounter,
                   MAX(arrival_datetime) AS last_encounter
            FROM silver_encounters WHERE patient_id = $pid
        """, {"pid": pid})
        enc_summary = _safe_row(enc_rows[0]) if enc_rows else {}

        # Admissions summary
        adm_rows = query_rows(conn, """
            SELECT COUNT(*) AS admission_count,
                   COALESCE(SUM(los_days),0) AS total_los_days,
                   COALESCE(SUM(CASE WHEN readmission_flag THEN 1 ELSE 0 END),0) AS readmissions
            FROM silver_admissions WHERE patient_id = $pid
        """, {"pid": pid})
        adm_summary = _safe_row(adm_rows[0]) if adm_rows else {}

        # Billing summary
        bill_rows = query_rows(conn, """
            SELECT COUNT(*) AS invoice_count,
                   COALESCE(SUM(gross_amount),0) AS gross_amount,
                   COALESCE(SUM(net_amount),0) AS net_amount,
                   COALESCE(SUM(paid_amount),0) AS paid_amount,
                   COALESCE(SUM(balance_amount),0) AS balance_amount
            FROM silver_invoices WHERE patient_id = $pid
        """, {"pid": pid})
        billing_summary = _safe_row(bill_rows[0]) if bill_rows else {}

        claim_rows = query_rows(conn, """
            SELECT COUNT(*) AS claim_count,
                   COALESCE(SUM(claim_amount),0) AS claim_amount,
                   COALESCE(SUM(approved_amount),0) AS approved_amount,
                   COALESCE(SUM(paid_amount),0) AS claim_paid_amount
            FROM silver_claims WHERE patient_id = $pid
        """, {"pid": pid})
        claim_summary = _safe_row(claim_rows[0]) if claim_rows else {}

        # Feedback summary
        fb_rows = query_rows(conn, """
            SELECT COUNT(*) AS feedback_count,
                   AVG(rating) AS avg_rating,
                   COALESCE(SUM(CASE WHEN complaint_flag THEN 1 ELSE 0 END),0) AS complaints
            FROM silver_feedback WHERE patient_id = $pid
        """, {"pid": pid})
        feedback_summary = _safe_row(fb_rows[0]) if fb_rows else {}

        events = _journey_events(conn, pid, event_type, date_from, date_to)

        # Section records (for the UI panels) - limited
        def section(table: str, date_col: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
            if not table_exists(table):
                return []
            cols = set(columns(conn, table))
            if "patient_id" not in cols:
                return []
            q = f"SELECT * FROM {table} WHERE patient_id = $pid"
            p: dict[str, Any] = {"pid": pid}
            if date_col and date_col in cols:
                q += f" ORDER BY {date_col} DESC"
            q += f" LIMIT {int(limit)}"
            try:
                return [_safe_row(r) for r in query_rows(conn, q, p)]
            except Exception:  # noqa: BLE001
                return []

        diagnoses: list[dict[str, Any]] = []
        diagnoses_note = "No diagnosis fact table in this synthetic dataset; diagnosis dimension exists (dim_diagnosis)."

        payload = {
            "patient": patient,
            "encounter_summary": enc_summary,
            "admission_summary": adm_summary,
            "billing_summary": billing_summary,
            "claim_summary": claim_summary,
            "feedback_summary": feedback_summary,
            "appointments": section("silver_appointments", "appointment_date"),
            "encounters": section("silver_encounters", "arrival_datetime"),
            "admissions": section("silver_admissions", "admission_datetime"),
            "transfers": section("silver_transfers", "transfer_datetime"),
            "procedures": section("silver_procedures", "scheduled_start"),
            "lab_orders": section("silver_lab_orders", "ordered_at"),
            "lab_results": section("silver_lab_results", "result_at"),
            "prescriptions": section("silver_prescriptions", "prescribed_date"),
            "dispensing": section("silver_dispensing", "dispensed_date"),
            "diagnoses": diagnoses,
            "diagnoses_note": diagnoses_note,
            "billing_claims": section("silver_claims", "claim_date"),
            "invoices": section("silver_invoices", "invoice_date"),
            "payments": section("silver_payments", "payment_date"),
            "feedback": section("silver_feedback", "visit_date"),
            "timeline": events,
            "event_types": sorted({e["event_type"] for e in events}),
            "synthetic_notice": "Synthetic data only. No real patient identities, no clinical recommendations.",
        }
    return _empty(payload, request)


@router.get("/journey/events")
def patient_journey_events(request: Request):
    f = parse_filters(request)
    patient_id = request.query_params.get("patient_id")
    encounter_id = request.query_params.get("encounter_id")
    admission_id = request.query_params.get("admission_id")
    event_type = request.query_params.get("event_type")
    date_from = request.query_params.get("date_from") or f.date_from
    date_to = request.query_params.get("date_to") or f.date_to
    with get_conn() as conn:
        pid = _resolve_journey_patient(conn, patient_id, encounter_id, admission_id)
        events = _journey_events(conn, pid, event_type, date_from, date_to)
    # flatten for table/export
    rows = []
    for e in events:
        detail = e.get("detail") or {}
        row = {
            "patient_id": pid,
            "event_type": e.get("event_type"),
            "event_label": e.get("event_label"),
            "event_date": e.get("event_date"),
            "event_id": e.get("event_id"),
            "table": e.get("table"),
        }
        # include a few detail keys
        for k, v in list(detail.items())[:12]:
            if k not in row:
                row[f"detail_{k}"] = v
        rows.append(row)
    total = len(rows)
    # manual pagination
    start = (f.page - 1) * f.page_size
    end = start + f.page_size
    page_rows = rows[start:end]
    return table_envelope(page_rows, total, f.page, f.page_size, f.applied(), dataset="journey_events", patient_id=pid)


# ---------------------------------------------------------------------------
# Server-side exports
# ---------------------------------------------------------------------------
@router.get(
    "/exports/csv",
    description=(
        "Export rows from any registered GET data endpoint as CSV. "
        f"Parameters: `path` (required, API-relative endpoint path such as `/overview/kpis` or `/api/v1/overview/kpis`), "
        "`filename` (optional, download name without extension). "
        "All other query params are forwarded to the source endpoint as filters/sort. "
        f"Row limit: exports are rejected with 413 `EXPORT_LIMIT_EXCEEDED` when the filtered result set exceeds {MAX_EXPORT_ROWS:,} rows. "
        "The source endpoint is reused so filters, sorting, KPI formulas and SQL stay identical to the on-screen response."
    ),
)
def export_csv(
    request: Request,
    path: str = Query(..., description="API-relative GET endpoint path to export, with or without /api/v1 prefix."),
    filename: str = Query("export", description="Download filename without extension."),
):
    """Export rows from any registered GET data endpoint under the contract cap."""
    try:
        route, path_params = resolve_export_route(request, path)
    except ValueError as exc:
        raise FilterValidationError(str(exc), {"parameter": "path", "value": path}) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    payload = invoke_export_route(request, route, path_params)
    rows = export_rows(payload)
    return csv_response(rows, filename)


# ---------------------------------------------------------------------------
# Filter options
# ---------------------------------------------------------------------------
@router.get("/filters/departments")
def filter_departments(request: Request, hospital_id: str | None = Query(default=None)):
    """Department options for global filter. If hospital_id provided, narrow to that hospital."""
    f = parse_filters(request)
    hid = hospital_id or (f.hospital_ids[0] if f.hospital_ids else None)
    with get_conn() as conn:
        if hid:
            rows = query_rows(
                conn,
                "SELECT d.department_id, d.department_name, d.specialty_id, s.specialty_name, d.hospital_id "
                "FROM dim_department d LEFT JOIN dim_specialty s ON s.specialty_id = d.specialty_id "
                "WHERE d.hospital_id = $hospital_id ORDER BY d.department_name",
                {"hospital_id": hid},
            )
            if not rows:
                rows = query_rows(
                    conn,
                    "SELECT department_id, department_name, specialty_id, specialty_id AS specialty_name, hospital_id "
                    "FROM silver_dim_department WHERE hospital_id = $hospital_id ORDER BY department_name",
                    {"hospital_id": hid},
                )
        else:
            rows = query_rows(
                conn,
                "SELECT DISTINCT d.department_id, d.department_name, d.specialty_id, s.specialty_name "
                "FROM dim_department d LEFT JOIN dim_specialty s ON s.specialty_id = d.specialty_id "
                "ORDER BY d.department_name",
            )
            if not rows:
                rows = query_rows(
                    conn,
                    "SELECT DISTINCT department_id, department_name, specialty_id, specialty_id AS specialty_name "
                    "FROM silver_dim_department ORDER BY department_name",
                )
    return envelope(rows, f.date_from, f.date_to, [hid] if hid else [])


# ---------------------------------------------------------------------------
# KPI glossary
# ---------------------------------------------------------------------------
@router.get("/kpis/glossary")
def kpi_glossary(request: Request):
    path = ROOT / "analytics" / "kpi_definitions" / "kpis.json"
    if not path.exists():
        return _empty([], request, status="not_available")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        payload = []
    if isinstance(payload, dict):
        payload = payload.get("kpis", [])
    for item in payload:
        if isinstance(item, dict) and item.get("id") in SNAPSHOT_KPI_IDS:
            item["date_filter_available"] = False
            item["date_filter_note"] = "Date filter unavailable: this is a snapshot KPI with no date field."
    return _empty(payload, request)
