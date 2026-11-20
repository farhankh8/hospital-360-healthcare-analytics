"""Data quality, pipeline, explorer, glossary and metadata endpoints."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from api.core.config import DATA_PATH, ROOT
from api.core.db import get_conn, table_exists
from api.core.filters import parse_filters
from api.core.responses import envelope, table_envelope
from api.services.query import columns, query_rows

router = APIRouter(tags=["system"])

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


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------
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
    return _empty({
        "overall_score": overall,
        "categories": list(categories.values()),
        "rules_total": len(rows),
        "rules_passed": sum(1 for r in rows if r.get("passed")),
        "total_failures": sum(int(r.get("failed_count") or 0) for r in rows),
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
            "FROM dq_failures ORDER BY detected_at DESC LIMIT $limit OFFSET $offset",
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


@router.get("/pipeline/runs/{run_id}")
def pipeline_run(run_id: str, request: Request):
    with get_conn() as conn:
        rows = query_rows(conn, "SELECT * FROM pipeline_runs WHERE run_id = $run_id", {"run_id": run_id}) if table_exists("pipeline_runs") else []
    if not rows:
        raise HTTPException(404, f"Run {run_id} not found")
    return _empty(rows[0], request)


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
        # Build safe pagination with allowlisted sort column.
        from api.core.filters import build_where
        where, params = build_where(f, cols, date_col=date_col)
        total = int(query_rows(conn, f"SELECT COUNT(*) AS n FROM {table}{where}", params)[0]["n"])
        order = f" ORDER BY {f.sort_by} {f.sort_dir.upper()}" if f.sort_by in cols else ""
        rows = query_rows(
            conn, f"SELECT * FROM {table}{where}{order} LIMIT $limit OFFSET $offset",
            {**params, "limit": f.page_size, "offset": (f.page - 1) * f.page_size},
        )
    return table_envelope(rows, total, f.page, f.page_size, f.applied(), dataset=dataset)


@router.get("/explorer/{dataset}/schema")
def explorer_schema(dataset: str, request: Request):
    table = _explorer_table(dataset)
    with get_conn() as conn:
        rows = conn.execute(f"DESCRIBE {table}").fetchall()
    schema = [{"column_name": r[0], "column_type": r[1], "nullable": r[2]} for r in rows]
    return _empty({"dataset": dataset, "table": table, "columns": schema}, request)


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
    return _empty(payload, request)
