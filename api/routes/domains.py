"""Domain-specific chart, distribution and record endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request

from api.core.db import get_conn
from api.core.filters import build_where, parse_filters
from api.core.responses import envelope
from api.routes.common import (
    grouped, make_kpis_route, multi_series, rows_endpoint, series,
)
from api.services.query import columns, query_rows

router = APIRouter(tags=["domains"])

# ---------------------------------------------------------------------------
# KPI cards (all domains)
# ---------------------------------------------------------------------------
for module in (
    "appointments", "emergency", "inpatient", "procedures", "diagnostics",
    "pharmacy", "finance", "claims", "workforce", "inventory", "experience", "quality",
):
    router.add_api_route(f"/{module}/kpis", make_kpis_route(module), methods=["GET"])

# ---------------------------------------------------------------------------
# Appointments & access
# ---------------------------------------------------------------------------
router.add_api_route(
    "/appointments/trends",
    multi_series("gold_patient_access", "month", {
        "scheduled": "SUM(scheduled)", "completed": "SUM(completed)",
        "cancelled": "SUM(cancelled)", "no_shows": "SUM(no_shows)",
    }), methods=["GET"])
router.get("/appointments/no-shows")(grouped(
    "silver_appointments", "department_id", "COUNT(*)", "no_shows", 20, date_col="appointment_date"))
router.get("/appointments/departments")(grouped(
    "gold_department_monthly", "department_name", "AVG(no_show_rate)", "no_show_rate", 20))
router.get("/appointments/wait-times")(grouped(
    "gold_patient_access", "hospital_id", "AVG(avg_wait_minutes)", "avg_wait", 20))
router.get("/appointments/records")(rows_endpoint("silver_appointments", "appointment_date"))


@router.get("/appointments/heatmap")
def appointment_heatmap(request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        cols = columns(conn, "silver_appointments")
        where, params = build_where(f, cols, date_col="appointment_date")
        rows = query_rows(
            conn,
            "SELECT CAST(dayofweek(checkin_datetime) AS VARCHAR) AS weekday, "
            "CAST(hour(checkin_datetime) AS VARCHAR) AS hour, COUNT(*) AS appointments "
            f"FROM silver_appointments{where} AND checkin_datetime IS NOT NULL "
            "GROUP BY 1, 2 ORDER BY 1, 2",
            params,
        )
    return envelope(rows, f.date_from, f.date_to, f.hospital_ids)


# ---------------------------------------------------------------------------
# Emergency & patient flow
# ---------------------------------------------------------------------------
router.add_api_route(
    "/emergency/trend",
    multi_series("silver_encounters", "arrival_datetime", {
        "visits": "COUNT(*)",
        "admitted": "COUNT(*) FILTER (WHERE disposition = 'Admit')",
        "discharged": "COUNT(*) FILTER (WHERE disposition = 'Discharge')",
        "transferred": "COUNT(*) FILTER (WHERE disposition = 'Transfer')",
        "lwbs": "COUNT(*) FILTER (WHERE disposition = 'LWBS')",
    }), methods=["GET"])
router.get("/emergency/arrivals")(grouped(
    "silver_encounters", "triage_category", "COUNT(*)", "visits", 10, date_col="arrival_datetime"))
router.get("/emergency/records")(rows_endpoint(
    "silver_encounters", "arrival_datetime", force_filters="encounter_type = 'Emergency'"))


@router.get("/emergency/flow")
def emergency_flow(request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        cols = columns(conn, "silver_encounters")
        where, params = build_where(f, cols, date_col="arrival_datetime")
        where += " AND encounter_type = 'Emergency'"
        stages = ["Arrival", "Triage", "Clinical Assessment", "Disposition"]
        union = " UNION ALL ".join(
            f"SELECT '{stage}' AS stage, COUNT(*) AS patients FROM silver_encounters{where}"
            for stage in stages
        )
        rows = query_rows(conn, union, params)
    return envelope(rows, f.date_from, f.date_to, f.hospital_ids)


# ---------------------------------------------------------------------------
# Inpatient & beds
# ---------------------------------------------------------------------------
router.add_api_route(
    "/inpatient/occupancy",
    multi_series("gold_bed_utilization", "month", {
        "occupied_bed_days": "SUM(occupied_bed_days)",
        "available_bed_days": "SUM(available_bed_days)",
        "blocked_bed_days": "SUM(blocked_bed_days)",
        "occupancy_rate": "SUM(occupied_bed_days) * 100.0 / NULLIF(SUM(available_bed_days), 0)",
    }), methods=["GET"])
router.get("/inpatient/los")(grouped(
    "silver_admissions", "department_id", "AVG(los_days)", "avg_los", 20, date_col="admission_datetime"))
router.get("/inpatient/bed-status")(grouped(
    "silver_bed_snapshots", "status", "COUNT(*)", "beds", 10, date_col="snapshot_datetime"))
router.get("/inpatient/admissions")(rows_endpoint("silver_admissions", "admission_datetime"))
router.get("/inpatient/records")(rows_endpoint("silver_admissions", "admission_datetime"))


# ---------------------------------------------------------------------------
# Surgery & procedures
# ---------------------------------------------------------------------------
router.add_api_route(
    "/procedures/volume",
    multi_series("silver_procedures", "scheduled_start", {
        "scheduled": "COUNT(*)",
        "completed": "COUNT(*) FILTER (WHERE status = 'Completed')",
        "cancelled": "COUNT(*) FILTER (WHERE status = 'Cancelled')",
        "delayed": "COUNT(*) FILTER (WHERE status = 'Delayed')",
    }), methods=["GET"])
router.get("/procedures/utilization")(grouped(
    "silver_procedures", "or_room", "COUNT(*)", "procedures", 20, date_col="scheduled_start"))
router.get("/procedures/records")(rows_endpoint("silver_procedures", "scheduled_start"))


# ---------------------------------------------------------------------------
# Diagnostics & laboratory
# ---------------------------------------------------------------------------
router.add_api_route(
    "/diagnostics/tat",
    multi_series("gold_lab_performance", "month", {
        "avg_tat_minutes": "SUM(avg_tat_minutes * orders) / NULLIF(SUM(orders), 0)",
        "sla_rate": "SUM(sla_rate * orders) / NULLIF(SUM(orders), 0)",
    }), methods=["GET"])
router.get("/diagnostics/volume")(grouped(
    "gold_lab_performance", "test_name", "SUM(orders)", "orders", 20))
router.get("/diagnostics/records")(rows_endpoint("silver_lab_orders", "ordered_at"))


# ---------------------------------------------------------------------------
# Pharmacy
# ---------------------------------------------------------------------------
router.add_api_route(
    "/pharmacy/trend",
    multi_series("silver_prescriptions", "prescribed_date", {
        "prescriptions": "COUNT(*)", "items": "SUM(quantity)", "revenue": "SUM(amount)",
    }), methods=["GET"])
router.get("/pharmacy/records")(rows_endpoint("silver_prescriptions", "prescribed_date"))


# ---------------------------------------------------------------------------
# Finance & revenue
# ---------------------------------------------------------------------------
router.add_api_route(
    "/finance/revenue-trend",
    multi_series("gold_hospital_monthly", "month", {
        "gross_revenue": "SUM(gross_revenue)", "net_revenue": "SUM(net_revenue)",
        "collections": "SUM(collections)", "outstanding": "SUM(outstanding_balance)",
    }), methods=["GET"])
router.add_api_route(
    "/finance/collections",
    multi_series("gold_hospital_monthly", "month", {
        "collections": "SUM(collections)",
        "collection_rate": "SUM(collections) * 100.0 / NULLIF(SUM(net_revenue), 0)",
    }), methods=["GET"])


@router.get("/finance/receivables")
def finance_receivables(request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        cols = columns(conn, "silver_invoices")
        where, params = build_where(f, cols, date_col="invoice_date")
        rows = query_rows(
            conn,
            "SELECT CASE "
            "WHEN date_diff('day', CAST(invoice_date AS DATE), CURRENT_DATE) <= 30 THEN '0-30' "
            "WHEN date_diff('day', CAST(invoice_date AS DATE), CURRENT_DATE) <= 60 THEN '31-60' "
            "WHEN date_diff('day', CAST(invoice_date AS DATE), CURRENT_DATE) <= 90 THEN '61-90' "
            "ELSE '90+' END AS aging_bucket, "
            "COUNT(*) AS invoices, SUM(balance_amount) AS outstanding "
            f"FROM silver_invoices{where} AND balance_amount > 0 GROUP BY 1 ORDER BY 1",
            params,
        )
    return envelope(rows, f.date_from, f.date_to, f.hospital_ids)


@router.get("/finance/revenue-by")
def finance_revenue_by(request: Request, by: str = "department"):
    if by not in {"department", "specialty", "service_category"}:
        from fastapi import HTTPException
        raise HTTPException(400, "by must be department, specialty or service_category")
    f = parse_filters(request)
    with get_conn() as conn:
        if by == "service_category":
            cols = columns(conn, "silver_invoice_lines")
            where, params = build_where(f, {"invoice_date", "hospital_id", "department_id"}, date_col="invoice_date")
            # invoice_lines has no date; filter via invoice id join instead.
            base = parse_filters(request)
            iw, ip = build_where(base, columns(conn, "silver_invoices"), date_col="invoice_date")
            rows = query_rows(
                conn,
                "SELECT l.service_category AS label, SUM(l.line_amount) AS revenue "
                "FROM silver_invoice_lines l JOIN silver_invoices i ON i.invoice_id = l.invoice_id"
                f"{iw.replace('invoice_date', 'i.invoice_date')} GROUP BY 1 ORDER BY 2 DESC",
                ip,
            )
        else:
            cols = columns(conn, "gold_department_monthly")
            where, params = build_where(f, cols, date_col="month")
            key = "department_name" if by == "department" else "specialty_name"
            rows = query_rows(
                conn,
                f"SELECT {key} AS label, SUM(revenue) AS revenue FROM gold_department_monthly"
                f"{where} GROUP BY 1 ORDER BY 2 DESC LIMIT 20",
                params,
            )
    return envelope(rows, f.date_from, f.date_to, f.hospital_ids, group_by=by)


router.get("/finance/invoices")(rows_endpoint("silver_invoices", "invoice_date"))
router.get("/finance/records")(rows_endpoint("silver_invoices", "invoice_date"))


# ---------------------------------------------------------------------------
# Insurance & claims
# ---------------------------------------------------------------------------
router.get("/claims/denials")(grouped(
    "silver_claims", "denial_reason", "COUNT(*)", "claims", 20, date_col="claim_date"))
router.get("/claims/payers")(grouped(
    "gold_claim_performance", "payer_name", "SUM(claims)", "claims", 20))


@router.get("/claims/aging")
def claims_aging(request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        cols = columns(conn, "silver_claims")
        where, params = build_where(f, cols, date_col="claim_date")
        rows = query_rows(
            conn,
            "SELECT CASE "
            "WHEN date_diff('day', CAST(claim_date AS DATE), CURRENT_DATE) <= 30 THEN '0-30' "
            "WHEN date_diff('day', CAST(claim_date AS DATE), CURRENT_DATE) <= 60 THEN '31-60' "
            "WHEN date_diff('day', CAST(claim_date AS DATE), CURRENT_DATE) <= 90 THEN '61-90' "
            "ELSE '90+' END AS aging_bucket, COUNT(*) AS claims, SUM(claim_amount) AS value "
            f"FROM silver_claims{where} AND status IN ('Pending', 'Under review') GROUP BY 1 ORDER BY 1",
            params,
        )
    return envelope(rows, f.date_from, f.date_to, f.hospital_ids)


router.get("/claims/records")(rows_endpoint("silver_claims", "claim_date"))


# ---------------------------------------------------------------------------
# Workforce
# ---------------------------------------------------------------------------
router.add_api_route(
    "/workforce/coverage",
    multi_series("gold_workforce", "month", {
        "scheduled_hours": "SUM(scheduled_hours)", "worked_hours": "SUM(worked_hours)",
        "coverage_pct": "SUM(worked_hours) * 100.0 / NULLIF(SUM(scheduled_hours), 0)",
    }), methods=["GET"])
router.get("/workforce/overtime")(grouped(
    "gold_workforce", "department_id", "SUM(overtime_hours)", "overtime", 20))
router.get("/workforce/attendance")(grouped(
    "silver_attendance", "status", "COUNT(*)", "events", 10, date_col="attendance_date"))
router.get("/workforce/records")(rows_endpoint("silver_shifts", "shift_date"))


# ---------------------------------------------------------------------------
# Inventory & procurement
# ---------------------------------------------------------------------------
router.get("/inventory/stockouts")(grouped(
    "gold_inventory", "category", "SUM(stockouts)", "stockouts", 20))
router.get("/inventory/movements")(grouped(
    "silver_inventory_movements", "movement_type", "SUM(ABS(quantity))", "units", 10, date_col="movement_date"))


@router.get("/inventory/expiry")
def inventory_expiry(request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        cols = columns(conn, "silver_inventory_movements")
        where, params = build_where(f, cols, date_col="movement_date")
        rows = query_rows(
            conn,
            "SELECT CAST(date_trunc('month', CAST(expiry_date AS DATE)) AS DATE) AS period, "
            "COUNT(*) AS items, SUM(ABS(quantity) * unit_cost) AS value "
            f"FROM silver_inventory_movements{where} AND expiry_date IS NOT NULL GROUP BY 1 ORDER BY 1",
            params,
        )
    return envelope(rows, f.date_from, f.date_to, f.hospital_ids)


router.get("/inventory/records")(rows_endpoint("silver_inventory_movements", "movement_date"))


# ---------------------------------------------------------------------------
# Patient experience
# ---------------------------------------------------------------------------
router.add_api_route(
    "/experience/trend",
    multi_series("gold_patient_experience", "month", {
        "feedback": "SUM(feedback_count)",
        "avg_rating": "SUM(avg_rating * feedback_count) / NULLIF(SUM(feedback_count), 0)",
        "nps": "SUM(nps * feedback_count) / NULLIF(SUM(feedback_count), 0)",
    }), methods=["GET"])
router.get("/experience/by-hospital")(grouped(
    "gold_patient_experience", "hospital_id",
    "SUM(satisfaction_pct * feedback_count) / NULLIF(SUM(feedback_count), 0)", "satisfaction", 20))
router.get("/experience/records")(rows_endpoint("silver_feedback", "visit_date"))


# ---------------------------------------------------------------------------
# Quality & safety
# ---------------------------------------------------------------------------
router.add_api_route(
    "/quality/trend",
    multi_series("gold_quality_safety", "month", {
        "incidents": "SUM(incidents)", "critical": "SUM(critical_incidents)",
        "investigation_completion": "SUM(investigation_completion_rate * incidents) / NULLIF(SUM(incidents), 0)",
    }), methods=["GET"])
router.get("/quality/incidents")(grouped(
    "silver_incidents", "category", "COUNT(*)", "incidents", 20, date_col="incident_date"))
router.get("/quality/records")(rows_endpoint("silver_incidents", "incident_date"))
