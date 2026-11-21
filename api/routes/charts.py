"""Full chart-data catalogue for every blueprint page.

These routes are additive: existing ETL, tables, KPI definitions and endpoint
responses are untouched. Every endpoint returns the standard ``envelope`` with
an array of rows so the shared ECharts renderer can consume it directly.

All SQL is static; user filters are applied through the allowlisted,
parameterised ``build_where`` helper.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Request

from api.core.config import DATA_PATH
from api.core.db import get_conn
from api.core.filters import build_where, parse_filters
from api.core.responses import envelope
from api.services.query import columns, query_rows

router = APIRouter(prefix="/charts", tags=["charts"])


def grouped(
    table: str,
    group_expr: str,
    expr: str,
    alias: str = "value",
    limit: int = 12,
    date_col: str = "month",
    extra_where: str = "",
    order_asc: bool = False,
) -> Callable[[Request], dict[str, Any]]:
    """One row per category: ``label`` plus a numeric measure."""

    def endpoint(request: Request) -> dict[str, Any]:
        f = parse_filters(request)
        with get_conn() as conn:
            where, params = build_where(f, columns(conn, table), date_col=date_col)
            if extra_where:
                where = (where + f" AND {extra_where}") if where else f" WHERE {extra_where}"
            sql = (
                f"SELECT {group_expr} AS label, {expr} AS {alias} FROM {table}{where} "
                f"GROUP BY 1 ORDER BY {alias} {'ASC' if order_asc else 'DESC'} LIMIT {limit}"
            )
            rows = query_rows(conn, sql, params)
        return envelope(rows, f.date_from, f.date_to, f.hospital_ids)

    endpoint.__name__ = f"chart_{table}_{alias}_{abs(hash(group_expr)) % 10000}"
    return endpoint


def multi(table: str, date_col: str, expressions: dict[str, str]) -> Callable[[Request], dict[str, Any]]:
    """One row per period with several named series."""

    def endpoint(request: Request) -> dict[str, Any]:
        f = parse_filters(request)
        with get_conn() as conn:
            where, params = build_where(f, columns(conn, table), date_col=date_col)
            selects = ", ".join(f"{expr} AS {name}" for name, expr in expressions.items())
            sql = (
                f"SELECT CAST({date_col} AS DATE) AS period, {selects} "
                f"FROM {table}{where} GROUP BY 1 ORDER BY 1"
            )
            rows = query_rows(conn, sql, params)
        return envelope(rows, f.date_from, f.date_to, f.hospital_ids, series=list(expressions))

    endpoint.__name__ = f"chart_multi_{table}_{abs(hash(tuple(expressions))) % 10000}"
    return endpoint


def custom(
    table: str,
    date_col: str,
    sql_template: str,
    extra_params: dict[str, Any] | None = None,
) -> Callable[[Request], dict[str, Any]]:
    """Static SQL with a single ``{where}`` placeholder built from filters."""

    def endpoint(request: Request) -> dict[str, Any]:
        f = parse_filters(request)
        with get_conn() as conn:
            where, params = build_where(f, columns(conn, table), date_col=date_col)
            params.update(extra_params or {})
            rows = query_rows(conn, sql_template.format(where=where), params)
        return envelope(rows, f.date_from, f.date_to, f.hospital_ids)

    endpoint.__name__ = f"chart_custom_{abs(hash(sql_template)) % 10000}"
    return endpoint


# ---------------------------------------------------------------------------
# Hospital comparison
# ---------------------------------------------------------------------------
router.add_api_route("/comparison-monthly", multi("gold_hospital_monthly", "month", {
    "revenue": "SUM(net_revenue)",
    "encounters": "SUM(encounters)",
    "patients": "SUM(patients)",
    "occupancy_rate": "SUM(occupied_bed_days) * 100.0 / NULLIF(SUM(available_bed_days), 0)",
    "avg_satisfaction": "SUM(avg_satisfaction * feedback_count) / NULLIF(SUM(feedback_count), 0)",
    "denial_rate": "SUM(claims_denied) * 100.0 / NULLIF(SUM(claims_submitted), 0)",
}), methods=["GET"])

@router.get("/hospital-rankings")
def hospital_rankings(request: Request) -> dict[str, Any]:
    f = parse_filters(request)
    metric = (request.query_params.get("metric") or "revenue").strip().lower()
    rank_sort = (request.query_params.get("rank_sort") or "desc").strip().lower()
    metric_map = {
        "revenue": "revenue",
        "patient_volume": "patient_volume",
        "occupancy": "occupancy",
        "satisfaction": "satisfaction",
        "los": "los",
        "denial_rate": "denial_rate",
    }
    order_col = metric_map.get(metric, "revenue")
    direction = "ASC" if rank_sort == "asc" else "DESC"
    with get_conn() as conn:
        where, params = build_where(f, columns(conn, "gold_hospital_monthly"), date_col="month")
        rows = query_rows(
            conn,
            f"""
            SELECT h.hospital_name AS label,
                   SUM(g.net_revenue) AS revenue,
                   SUM(g.encounters) AS patient_volume,
                   SUM(g.occupied_bed_days) * 100.0 / NULLIF(SUM(g.available_bed_days), 0) AS occupancy,
                   AVG(g.avg_satisfaction) AS satisfaction,
                   SUM(g.avg_los_days * g.discharges) / NULLIF(SUM(g.discharges), 0) AS los,
                   SUM(g.claims_denied) * 100.0 / NULLIF(SUM(g.claims_submitted), 0) AS denial_rate
            FROM (SELECT * FROM gold_hospital_monthly{where}) g
            JOIN silver_dim_hospital h ON h.hospital_id = g.hospital_id
            GROUP BY 1 ORDER BY {order_col} {direction} NULLS LAST
            """,
            params,
        )
    return envelope(rows, f.date_from, f.date_to, f.hospital_ids, metric=order_col, rank_sort=direction.lower())

router.add_api_route("/comparison-kpis", custom("gold_hospital_monthly", "month", """
WITH base AS (SELECT * FROM gold_hospital_monthly{where})
SELECT hospital_name AS x, 'Occupancy' AS y, AVG(occupancy_rate) AS value FROM base GROUP BY 1
UNION ALL SELECT hospital_name, 'No-show rate', AVG(no_show_rate) FROM base GROUP BY 1
UNION ALL SELECT hospital_name, 'LOS days', AVG(avg_los_days) FROM base GROUP BY 1
UNION ALL SELECT hospital_name, 'Satisfaction', AVG(avg_satisfaction) FROM base GROUP BY 1
UNION ALL SELECT hospital_name, 'Denial rate', AVG(denial_rate) FROM base GROUP BY 1
UNION ALL SELECT hospital_name, 'Revenue', AVG(net_revenue) FROM base GROUP BY 1
ORDER BY 1, 2
"""), methods=["GET"])

router.add_api_route("/comparison-los", custom("gold_hospital_monthly", "month", """
SELECT h.hospital_name AS label,
       SUM(g.avg_los_days * g.discharges) / NULLIF(SUM(g.discharges), 0) AS avg_los
FROM (SELECT * FROM gold_hospital_monthly{where}) g
JOIN silver_dim_hospital h ON h.hospital_id = g.hospital_id
GROUP BY 1 ORDER BY 2 DESC
"""), methods=["GET"])

router.add_api_route("/comparison-denials", grouped(
    "gold_hospital_monthly", "hospital_name",
    "SUM(claims_denied) * 100.0 / NULLIF(SUM(claims_submitted), 0)", "denial_rate", 20), methods=["GET"])

# ---------------------------------------------------------------------------
# Appointments & patient access
# ---------------------------------------------------------------------------
router.add_api_route("/appointments/no-show-trend", multi("gold_patient_access", "month", {
    "no_show_rate": "SUM(no_shows) * 100.0 / NULLIF(SUM(scheduled), 0)",
    "reschedule_rate": "AVG(reschedule_rate)",
}), methods=["GET"])
router.add_api_route("/appointments/specialty", custom("silver_appointments", "appointment_date", """
SELECT COALESCE(s.specialty_name, 'Unassigned') AS label, COUNT(*) AS no_shows
FROM (SELECT * FROM silver_appointments{where}) a
LEFT JOIN silver_dim_department d ON d.department_id = a.department_id
LEFT JOIN silver_dim_specialty s ON s.specialty_id = d.specialty_id
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/appointments/wait-distribution", grouped("silver_appointments",
    "CASE WHEN waiting_minutes < 5 THEN '0-4' WHEN waiting_minutes < 10 THEN '5-9' "
    "WHEN waiting_minutes < 20 THEN '10-19' WHEN waiting_minutes < 30 THEN '20-29' "
    "WHEN waiting_minutes < 45 THEN '30-44' ELSE '45+' END",
    "COUNT(*)", "appointments", 10, date_col="appointment_date", order_asc=True), methods=["GET"])
router.add_api_route("/appointments/lead-time", grouped("silver_appointments",
    "CASE WHEN lead_days <= 0 THEN 'Same day' WHEN lead_days <= 3 THEN '1-3 days' "
    "WHEN lead_days <= 7 THEN '4-7 days' WHEN lead_days <= 14 THEN '8-14 days' ELSE '15+ days' END",
    "COUNT(*)", "appointments", 10, date_col="appointment_date"), methods=["GET"])
router.add_api_route("/appointments/cancellations", grouped("silver_appointments",
    "COALESCE(cancellation_reason, 'Not recorded')", "COUNT(*)", "cancelled", 10,
    date_col="appointment_date", extra_where="status = 'Cancelled'"), methods=["GET"])
router.add_api_route("/appointments/doctor-bookings", custom("silver_appointments", "appointment_date", """
WITH booked AS (
  SELECT a.hospital_id, COUNT(*) AS booked
  FROM (SELECT * FROM silver_appointments{where}) a GROUP BY 1
), capacity AS (
  SELECT s.hospital_id, SUM(s.scheduled_hours) * 4 AS available_slots
  FROM silver_shifts s GROUP BY 1
)
SELECT COALESCE(h.hospital_name, b.hospital_id) AS label,
       b.booked, COALESCE(c.available_slots, 0) AS available_slots
FROM booked b
LEFT JOIN capacity c ON c.hospital_id = b.hospital_id
LEFT JOIN silver_dim_hospital h ON h.hospital_id = b.hospital_id
ORDER BY booked DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/appointments/access", grouped("gold_patient_access", "hospital_id",
    "AVG(no_show_rate)", "no_show_rate", 20), methods=["GET"])

# ---------------------------------------------------------------------------
# Emergency & patient flow
# ---------------------------------------------------------------------------
router.add_api_route("/emergency/hourly", custom("silver_encounters", "arrival_datetime", """
SELECT CAST(hour(arrival_datetime) AS VARCHAR) AS label, COUNT(*) AS visits
FROM silver_encounters{where} GROUP BY 1 ORDER BY 1
"""), methods=["GET"])
router.add_api_route("/emergency/weekday", custom("silver_encounters", "arrival_datetime", """
SELECT d.weekday_name AS label, COUNT(*) AS visits
FROM (SELECT * FROM silver_encounters{where}) e
JOIN silver_dim_date d ON CAST(e.arrival_datetime AS DATE) = CAST(d.full_date AS DATE)
GROUP BY 1 ORDER BY 2 DESC
"""), methods=["GET"])
router.add_api_route("/emergency/triage", grouped("silver_encounters", "triage_category",
    "COUNT(*)", "visits", 10, date_col="arrival_datetime"), methods=["GET"])
router.add_api_route("/emergency/wait-by-triage", grouped("silver_encounters", "triage_category",
    "AVG(waiting_minutes)", "avg_wait", 10, date_col="arrival_datetime"), methods=["GET"])
router.add_api_route("/emergency/wait-by-hospital", grouped("silver_encounters", "hospital_id",
    "AVG(waiting_minutes)", "avg_wait", 20, date_col="arrival_datetime"), methods=["GET"])
router.add_api_route("/emergency/disposition", grouped("silver_encounters", "disposition",
    "COUNT(*)", "visits", 10, date_col="arrival_datetime"), methods=["GET"])
router.add_api_route("/emergency/times", custom("silver_encounters", "arrival_datetime", """
SELECT 'Arrival to triage' AS label, AVG(date_diff('minute', arrival_datetime, triage_datetime)) AS minutes FROM (SELECT * FROM silver_encounters{where}) e
UNION ALL SELECT 'Triage to provider', AVG(date_diff('minute', triage_datetime, provider_datetime)) FROM (SELECT * FROM silver_encounters{where}) e
UNION ALL SELECT 'Provider to disposition', AVG(date_diff('minute', provider_datetime, disposition_datetime)) FROM (SELECT * FROM silver_encounters{where}) e
"""), methods=["GET"])
router.add_api_route("/emergency/crowding", custom("silver_admissions", "admission_datetime", """
SELECT CAST(date_trunc('month', admission_datetime) AS DATE) AS period,
       COUNT(*) AS admissions, AVG(boarding_hours) AS avg_boarding_hours
FROM silver_admissions{where} GROUP BY 1 ORDER BY 1
"""), methods=["GET"])

# ---------------------------------------------------------------------------
# Inpatient & beds
# ---------------------------------------------------------------------------
router.add_api_route("/inpatient/admissions", multi("gold_hospital_monthly", "month", {
    "admissions": "SUM(admissions)", "discharges": "SUM(discharges)",
}), methods=["GET"])
router.add_api_route("/inpatient/heatmap", custom("gold_bed_utilization", "month", """
SELECT ward AS x, CAST(month AS DATE) AS y,
       SUM(occupied_bed_days) * 100.0 / NULLIF(SUM(available_bed_days), 0) AS value
FROM gold_bed_utilization{where} GROUP BY 1, 2 ORDER BY 2, 1 LIMIT 300
"""), methods=["GET"])
router.add_api_route("/inpatient/occupancy-hospital", grouped("gold_bed_utilization", "hospital_id",
    "SUM(occupied_bed_days) * 100.0 / NULLIF(SUM(available_bed_days), 0)", "occupancy_rate", 20), methods=["GET"])
router.add_api_route("/inpatient/occupancy-department", grouped("gold_department_monthly", "department_name",
    "AVG(occupancy_rate)", "occupancy_rate", 20), methods=["GET"])
router.add_api_route("/inpatient/occupancy-ward", grouped("gold_bed_utilization", "ward",
    "SUM(occupied_bed_days) * 100.0 / NULLIF(SUM(available_bed_days), 0)", "occupancy_rate", 20), methods=["GET"])
router.add_api_route("/inpatient/los-distribution", grouped("silver_admissions",
    "CASE WHEN los_days < 2 THEN '0-1' WHEN los_days < 4 THEN '2-3' WHEN los_days < 6 THEN '4-5' "
    "WHEN los_days < 8 THEN '6-7' ELSE '8+' END",
    "COUNT(*)", "admissions", 10, date_col="admission_datetime", order_asc=True), methods=["GET"])
router.add_api_route("/inpatient/los-specialty", custom("silver_admissions", "admission_datetime", """
SELECT COALESCE(s.specialty_name, 'Unassigned') AS label, AVG(a.los_days) AS avg_los
FROM (SELECT * FROM silver_admissions{where}) a
LEFT JOIN silver_dim_department d ON d.department_id = a.department_id
LEFT JOIN silver_dim_specialty s ON s.specialty_id = d.specialty_id
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/inpatient/turnover", grouped("gold_bed_utilization", "hospital_id",
    "AVG(bed_turnover)", "bed_turnover", 20), methods=["GET"])
router.add_api_route("/inpatient/discharge-weekday", custom("silver_admissions", "discharge_datetime", """
SELECT dayname(discharge_datetime) AS label, COUNT(*) AS discharges
FROM silver_admissions{where} GROUP BY 1 ORDER BY 2 DESC
"""), methods=["GET"])
router.add_api_route("/inpatient/readmission", custom("silver_admissions", "admission_datetime", """
SELECT CAST(date_trunc('month', admission_datetime) AS DATE) AS period,
       SUM(CASE WHEN readmission_flag THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0) AS readmission_rate
FROM silver_admissions{where} GROUP BY 1 ORDER BY 1
"""), methods=["GET"])

# ---------------------------------------------------------------------------
# Surgery & procedures
# ---------------------------------------------------------------------------
router.add_api_route("/procedures/specialty", custom("silver_procedures", "scheduled_start", """
SELECT COALESCE(s.specialty_name, 'Unassigned') AS label, COUNT(*) AS procedures
FROM (SELECT * FROM silver_procedures{where}) p
LEFT JOIN silver_dim_department d ON d.department_id = p.department_id
LEFT JOIN silver_dim_specialty s ON s.specialty_id = d.specialty_id
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/procedures/or-hospital", grouped("silver_procedures", "hospital_id",
    "COUNT(*)", "procedures", 20, date_col="scheduled_start"), methods=["GET"])
router.add_api_route("/procedures/cancellations", grouped("silver_procedures",
    "COALESCE(cancellation_reason, 'Not recorded')", "COUNT(*)", "cancelled", 10,
    date_col="scheduled_start", extra_where="status = 'Cancelled'"), methods=["GET"])
router.add_api_route("/procedures/duration", grouped("silver_procedures",
    "CASE WHEN duration_minutes < 30 THEN '<30m' WHEN duration_minutes < 60 THEN '30-59m' "
    "WHEN duration_minutes < 120 THEN '1-2h' WHEN duration_minutes < 180 THEN '2-3h' ELSE '3h+' END",
    "COUNT(*)", "procedures", 10, date_col="scheduled_start", order_asc=True), methods=["GET"])
router.add_api_route("/procedures/start-performance", custom("silver_procedures", "scheduled_start", """
SELECT h.hospital_name AS label,
       COUNT(*) FILTER (WHERE date_diff('minute', p.scheduled_start, p.actual_start) <= 0) * 100.0
         / NULLIF(COUNT(*), 0) AS on_time_pct
FROM (SELECT * FROM silver_procedures{where}) p
LEFT JOIN silver_dim_hospital h ON h.hospital_id = p.hospital_id
GROUP BY 1 ORDER BY 2 DESC
"""), methods=["GET"])
router.add_api_route("/procedures/turnaround", grouped("silver_procedures", "or_room",
    "AVG(duration_minutes)", "avg_minutes", 20, date_col="scheduled_start"), methods=["GET"])
router.add_api_route("/procedures/surgeon", grouped("silver_procedures", "surgeon_id",
    "COUNT(*)", "procedures", 20, date_col="scheduled_start"), methods=["GET"])
router.add_api_route("/procedures/revenue", custom("silver_procedures", "scheduled_start", """
SELECT COALESCE(s.specialty_name, 'Unassigned') AS label, SUM(p.revenue) AS revenue
FROM (SELECT * FROM silver_procedures{where}) p
LEFT JOIN silver_dim_department d ON d.department_id = p.department_id
LEFT JOIN silver_dim_specialty s ON s.specialty_id = d.specialty_id
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])

# ---------------------------------------------------------------------------
# Diagnostics & laboratory
# ---------------------------------------------------------------------------
router.add_api_route("/diagnostics/orders-trend", multi("gold_lab_performance", "month", {
    "orders": "SUM(orders)", "completed": "SUM(completed)", "pending": "SUM(pending)",
}), methods=["GET"])
router.add_api_route("/diagnostics/category", custom("gold_lab_performance", "month", """
SELECT COALESCE(t.category, 'Unassigned') AS label, SUM(g.orders) AS orders
FROM (SELECT * FROM gold_lab_performance{where}) g
LEFT JOIN silver_dim_lab_test t ON t.test_code = g.test_code
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/diagnostics/tat-test", grouped("gold_lab_performance", "test_name",
    "AVG(avg_tat_minutes)", "avg_tat_minutes", 20), methods=["GET"])
router.add_api_route("/diagnostics/tat-hospital", grouped("gold_lab_performance", "hospital_id",
    "SUM(avg_tat_minutes * orders) / NULLIF(SUM(orders), 0)", "avg_tat_minutes", 20), methods=["GET"])
router.add_api_route("/diagnostics/sla", multi("gold_lab_performance", "month", {
    "sla_rate": "SUM(sla_rate * orders) / NULLIF(SUM(orders), 0)",
    "delayed": "SUM(delayed)",
}), methods=["GET"])
router.add_api_route("/diagnostics/pending", grouped("gold_lab_performance", "month",
    "SUM(pending)", "pending", 24, order_asc=True), methods=["GET"])
router.add_api_route("/diagnostics/delayed", grouped("gold_lab_performance", "test_name",
    "SUM(delayed)", "delayed", 20), methods=["GET"])
router.add_api_route("/diagnostics/heatmap", custom("silver_lab_orders", "ordered_at", """
SELECT t.test_name AS x, CAST(date_trunc('month', o.ordered_at) AS DATE) AS y, COUNT(*) AS value
FROM (SELECT * FROM silver_lab_orders{where}) o
LEFT JOIN silver_dim_lab_test t ON t.test_code = o.test_code
GROUP BY 1, 2 ORDER BY 2, 1 LIMIT 300
"""), methods=["GET"])
router.add_api_route("/diagnostics/workload", custom("silver_lab_orders", "ordered_at", """
SELECT CAST(hour(ordered_at) AS VARCHAR) AS label, COUNT(*) AS orders
FROM silver_lab_orders{where} GROUP BY 1 ORDER BY 1
"""), methods=["GET"])
router.add_api_route("/diagnostics/critical", grouped("gold_lab_performance", "hospital_id",
    "SUM(critical)", "critical", 20), methods=["GET"])
router.add_api_route("/diagnostics/activity-value", grouped("gold_lab_performance", "test_name",
    "SUM(orders)", "orders", 20), methods=["GET"])

# ---------------------------------------------------------------------------
# Pharmacy
# ---------------------------------------------------------------------------
router.add_api_route("/pharmacy/dispensing", custom("silver_dispensing", "dispensed_date", """
SELECT CAST(date_trunc('month', dispensed_date) AS DATE) AS period,
       COUNT(*) AS dispensed, SUM(quantity_dispensed) AS items
FROM silver_dispensing{where} GROUP BY 1 ORDER BY 1
"""), methods=["GET"])
router.add_api_route("/pharmacy/category", custom("silver_prescriptions", "prescribed_date", """
SELECT COALESCE(m.category, 'Unassigned') AS label, COUNT(*) AS prescriptions
FROM (SELECT * FROM silver_prescriptions{where}) p
LEFT JOIN silver_dim_medication m ON m.medication_code = p.medication_code
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/pharmacy/top-medications", custom("silver_prescriptions", "prescribed_date", """
SELECT COALESCE(m.medication_name, p.medication_code) AS label, SUM(p.quantity) AS quantity
FROM (SELECT * FROM silver_prescriptions{where}) p
LEFT JOIN silver_dim_medication m ON m.medication_code = p.medication_code
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/pharmacy/revenue", custom("silver_prescriptions", "prescribed_date", """
SELECT COALESCE(m.medication_name, p.medication_code) AS label, SUM(p.amount) AS revenue
FROM (SELECT * FROM silver_prescriptions{where}) p
LEFT JOIN silver_dim_medication m ON m.medication_code = p.medication_code
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/pharmacy/turnaround", custom("silver_dispensing", "dispensed_date", """
SELECT h.hospital_name AS label,
       AVG(date_diff('day', p.prescribed_date, d.dispensed_date)) AS avg_days
FROM (SELECT * FROM silver_dispensing{where}) d
JOIN silver_prescriptions p ON p.prescription_id = d.prescription_id
LEFT JOIN silver_dim_hospital h ON h.hospital_id = d.hospital_id
GROUP BY 1 ORDER BY 2 DESC
"""), methods=["GET"])
router.add_api_route("/pharmacy/stockout", grouped("gold_hospital_monthly", "month",
    "SUM(stockouts)", "stockouts", 24, order_asc=True), methods=["GET"])
router.add_api_route("/pharmacy/expiry", grouped("gold_inventory", "month",
    "SUM(expired_value)", "expired_value", 24, order_asc=True), methods=["GET"])
router.add_api_route("/pharmacy/hospital", grouped("silver_prescriptions", "hospital_id",
    "COUNT(*)", "prescriptions", 20, date_col="prescribed_date"), methods=["GET"])
router.add_api_route("/pharmacy/department", custom("silver_prescriptions", "prescribed_date", """
SELECT COALESCE(d.department_name, 'Unassigned') AS label, COUNT(*) AS prescriptions
FROM (SELECT * FROM silver_prescriptions{where}) p
LEFT JOIN silver_encounters e ON e.encounter_id = p.encounter_id
LEFT JOIN silver_dim_department d ON d.department_id = e.department_id
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])

# ---------------------------------------------------------------------------
# Finance & revenue
# ---------------------------------------------------------------------------
router.add_api_route("/finance/hospital", custom("gold_hospital_monthly", "month", """
SELECT h.hospital_name AS label, SUM(g.net_revenue) AS net_revenue
FROM (SELECT * FROM gold_hospital_monthly{where}) g
JOIN silver_dim_hospital h ON h.hospital_id = g.hospital_id
GROUP BY 1 ORDER BY 2 DESC
"""), methods=["GET"])
router.add_api_route("/finance/specialty", custom("gold_department_monthly", "month", """
SELECT specialty_name AS label, SUM(revenue) AS net_revenue
FROM gold_department_monthly {where} GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/finance/service-category", custom("silver_invoices", "invoice_date", """
SELECT l.service_category AS label, SUM(l.line_amount) AS gross_amount
FROM (SELECT * FROM silver_invoices{where}) i
JOIN silver_invoice_lines l ON l.invoice_id = i.invoice_id
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/finance/revenue-per-encounter", custom("gold_hospital_monthly", "month", """
SELECT h.hospital_name AS label,
       SUM(g.net_revenue) / NULLIF(SUM(g.encounters), 0) AS revenue_per_encounter
FROM (SELECT * FROM gold_hospital_monthly{where}) g
JOIN silver_dim_hospital h ON h.hospital_id = g.hospital_id
GROUP BY 1 ORDER BY 2 DESC
"""), methods=["GET"])
router.add_api_route("/finance/payer-mix", custom("silver_invoices", "invoice_date", """
SELECT COALESCE(p.payer_name, 'Self-pay') AS label, SUM(i.net_amount) AS net_revenue
FROM (SELECT * FROM silver_invoices{where}) i
LEFT JOIN silver_dim_payer p ON p.payer_id = i.payer_id
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/finance/leakage", custom("gold_financial_performance", "month", """
SELECT 'Outstanding balances' AS label, SUM(outstanding_balance) AS amount FROM gold_financial_performance{where}
UNION ALL SELECT 'Write-offs', SUM(writeoffs) FROM gold_financial_performance{where}
UNION ALL SELECT 'Refunds', SUM(refunds) FROM gold_financial_performance{where}
UNION ALL SELECT 'Discounts', SUM(gross_revenue - net_revenue) FROM gold_financial_performance{where}
"""), methods=["GET"])

# ---------------------------------------------------------------------------
# Insurance & claims
# ---------------------------------------------------------------------------
router.add_api_route("/claims/trend", multi("gold_claim_performance", "month", {
    "claims": "SUM(claims)", "approved": "SUM(approved)", "denied": "SUM(denied)",
}), methods=["GET"])
router.add_api_route("/claims/denial-trend", multi("gold_claim_performance", "month", {
    "denial_rate": "SUM(denied) * 100.0 / NULLIF(SUM(claims), 0)",
}), methods=["GET"])
router.add_api_route("/claims/reasons", grouped("silver_claims", "denial_reason",
    "COUNT(*)", "denied", 12, date_col="claim_date", extra_where="status = 'Denied'"), methods=["GET"])
router.add_api_route("/claims/hospital", grouped("gold_claim_performance", "hospital_id",
    "SUM(claims)", "claims", 20), methods=["GET"])
router.add_api_route("/claims/department", custom("silver_claims", "claim_date", """
SELECT COALESCE(d.department_name, 'Unassigned') AS label, COUNT(*) AS claims
FROM (SELECT * FROM silver_claims{where}) c
JOIN silver_invoices i ON i.invoice_id = c.invoice_id
LEFT JOIN silver_encounters e ON e.encounter_id = i.encounter_id
LEFT JOIN silver_dim_department d ON d.department_id = e.department_id
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/claims/amounts", custom("gold_claim_performance", "month", """
SELECT h.hospital_name AS label, SUM(c.claimed_amount) AS claimed,
       SUM(c.approved_amount) AS approved, SUM(c.paid_amount) AS paid
FROM (SELECT * FROM gold_claim_performance{where}) c
JOIN silver_dim_hospital h ON h.hospital_id = c.hospital_id
GROUP BY 1 ORDER BY 2 DESC
"""), methods=["GET"])
router.add_api_route("/claims/processing", grouped("silver_claims",
    "CASE WHEN processing_days <= 3 THEN '0-3' WHEN processing_days <= 7 THEN '4-7' "
    "WHEN processing_days <= 14 THEN '8-14' ELSE '15+' END",
    "COUNT(*)", "claims", 10, date_col="claim_date", order_asc=True), methods=["GET"])
router.add_api_route("/claims/appeals", grouped("gold_claim_performance", "hospital_id",
    "SUM(appeals)", "appeals", 20), methods=["GET"])

# ---------------------------------------------------------------------------
# Workforce
# ---------------------------------------------------------------------------
router.add_api_route("/workforce/staffing", multi("gold_workforce", "month", {
    "headcount": "SUM(headcount)", "scheduled_hours": "SUM(scheduled_hours)",
    "worked_hours": "SUM(worked_hours)",
}), methods=["GET"])
router.add_api_route("/workforce/department", grouped("gold_workforce", "department_id",
    "AVG(headcount)", "headcount", 20), methods=["GET"])
router.add_api_route("/workforce/role", custom("silver_dim_staff", "month", """
SELECT role AS label, COUNT(*) AS staff, SUM(hourly_rate) AS hourly_cost
FROM silver_dim_staff WHERE status = 'Active' GROUP BY 1 ORDER BY 2 DESC
"""), methods=["GET"])
router.add_api_route("/workforce/shift", grouped("silver_shifts", "shift_type",
    "SUM(scheduled_hours)", "scheduled_hours", 10, date_col="shift_date"), methods=["GET"])
router.add_api_route("/workforce/planned-actual", grouped("gold_workforce", "hospital_id",
    "SUM(worked_hours)", "worked_hours", 20), methods=["GET"])
router.add_api_route("/workforce/absence", multi("gold_workforce", "month", {
    "absence_rate": "AVG(absence_rate)",
}), methods=["GET"])
router.add_api_route("/workforce/gap", custom("gold_workforce", "month", """
SELECT d.department_name AS x, CAST(g.month AS DATE) AS y, AVG(g.coverage_pct) AS value
FROM (SELECT * FROM gold_workforce{where}) g
LEFT JOIN silver_dim_department d ON d.department_id = g.department_id
GROUP BY 1, 2 ORDER BY 2, 1 LIMIT 300
"""), methods=["GET"])
router.add_api_route("/workforce/cost", grouped("gold_workforce", "department_id",
    "SUM(workforce_cost)", "workforce_cost", 20), methods=["GET"])
router.add_api_route("/workload", grouped("gold_workforce", "hospital_id",
    "SUM(worked_hours) / NULLIF(SUM(headcount), 0)", "hours_per_staff", 20), methods=["GET"])

# ---------------------------------------------------------------------------
# Inventory & procurement
# ---------------------------------------------------------------------------
router.add_api_route("/inventory/value", multi("gold_inventory", "month", {
    "inventory_value": "SUM(inventory_value)", "expired_value": "SUM(expired_value)",
    "waste": "SUM(waste)",
}), methods=["GET"])
router.add_api_route("/inventory/category", grouped("gold_inventory", "category",
    "SUM(inventory_value)", "inventory_value", 20), methods=["GET"])
router.add_api_route("/inventory/hospital", grouped("gold_hospital_monthly", "hospital_id",
    "AVG(inventory_value)", "inventory_value", 20), methods=["GET"])
router.add_api_route("/inventory/low", grouped("gold_inventory", "category",
    "SUM(low_stock)", "low_stock", 20), methods=["GET"])
router.add_api_route("/inventory/consumption", custom("silver_inventory_movements", "movement_date", """
SELECT CAST(date_trunc('month', movement_date) AS DATE) AS period, SUM(quantity) AS quantity
FROM silver_inventory_movements{where} GROUP BY 1 ORDER BY 1
"""), methods=["GET"])
router.add_api_route("/inventory/turnover", grouped("gold_inventory", "month",
    "AVG(turnover)", "turnover", 24, order_asc=True), methods=["GET"])
router.add_api_route("/inventory/supplier", custom("silver_purchase_orders", "order_date", """
SELECT COALESCE(s.supplier_name, 'Unknown') AS label,
       SUM(CASE WHEN p.received_date <= p.expected_date THEN 1 ELSE 0 END) * 100.0
         / NULLIF(COUNT(*), 0) AS on_time_pct
FROM (SELECT * FROM silver_purchase_orders{where}) p
LEFT JOIN silver_dim_supplier s ON s.supplier_id = p.supplier_id
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/inventory/orders", multi("gold_inventory", "month", {
    "purchase_orders": "SUM(purchase_orders)", "procurement_value": "SUM(procurement_value)",
}), methods=["GET"])

# ---------------------------------------------------------------------------
# Patient experience
# ---------------------------------------------------------------------------
router.add_api_route("/experience/department", custom("silver_feedback", "visit_date", """
SELECT COALESCE(d.department_name, 'Unassigned') AS label, AVG(f.rating) AS avg_rating
FROM (SELECT * FROM silver_feedback{where}) f
LEFT JOIN silver_dim_department d ON d.department_id = f.department_id
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/experience/service", grouped("silver_feedback", "feedback_type",
    "AVG(rating)", "avg_rating", 12, date_col="visit_date"), methods=["GET"])
router.add_api_route("/experience/ratings", grouped("silver_feedback", "rating",
    "COUNT(*)", "feedback", 10, date_col="visit_date", order_asc=True), methods=["GET"])
router.add_api_route("/experience/nps", grouped("silver_feedback", "sentiment_label",
    "COUNT(*)", "feedback", 10, date_col="visit_date"), methods=["GET"])
router.add_api_route("/experience/categories", grouped("silver_feedback", "category",
    "COUNT(*)", "feedback", 12, date_col="visit_date"), methods=["GET"])
router.add_api_route("/experience/complaints", multi("silver_feedback", "visit_date", {
    "complaints": "SUM(CASE WHEN complaint_flag THEN 1 ELSE 0 END)",
    "feedback": "COUNT(*)",
}), methods=["GET"])
router.add_api_route("/experience/resolution", grouped("silver_feedback", "hospital_id",
    "AVG(resolution_days)", "avg_days", 20, date_col="visit_date"), methods=["GET"])
router.add_api_route("/experience/heatmap", custom("gold_patient_experience", "month", """
SELECT d.department_name AS x, CAST(g.month AS DATE) AS y, AVG(g.avg_rating) AS value
FROM (SELECT * FROM gold_patient_experience{where}) g
LEFT JOIN silver_dim_department d ON d.department_id = g.department_id
GROUP BY 1, 2 ORDER BY 2, 1 LIMIT 300
"""), methods=["GET"])

# ---------------------------------------------------------------------------
# Quality & safety
# ---------------------------------------------------------------------------
router.add_api_route("/quality/hospital", grouped("gold_quality_safety", "hospital_id",
    "SUM(incidents)", "incidents", 20), methods=["GET"])
router.add_api_route("/quality/severity", grouped("silver_incidents", "severity",
    "COUNT(*)", "incidents", 10, date_col="incident_date"), methods=["GET"])
router.add_api_route("/quality/department", custom("silver_incidents", "incident_date", """
SELECT COALESCE(d.department_name, 'Unassigned') AS label, COUNT(*) AS incidents
FROM (SELECT * FROM silver_incidents{where}) i
LEFT JOIN silver_dim_department d ON d.department_id = i.department_id
GROUP BY 1 ORDER BY 2 DESC LIMIT 12
"""), methods=["GET"])
router.add_api_route("/quality/investigation", grouped("silver_incidents", "status",
    "COUNT(*)", "incidents", 10, date_col="incident_date"), methods=["GET"])
router.add_api_route("/quality/readmission", multi("gold_quality_safety", "month", {
    "readmission_rate": "AVG(readmission_rate)",
}), methods=["GET"])
router.add_api_route("/quality/indicators", custom("gold_quality_safety", "month", """
SELECT 'Falls' AS label, SUM(falls) AS value FROM gold_quality_safety{where}
UNION ALL SELECT 'Medication incidents', SUM(medication_incidents) FROM gold_quality_safety{where}
UNION ALL SELECT 'Infection incidents', SUM(infection_incidents) FROM gold_quality_safety{where}
UNION ALL SELECT 'Critical incidents', SUM(critical_incidents) FROM gold_quality_safety{where}
"""), methods=["GET"])
router.add_api_route("/quality/heatmap", custom("silver_incidents", "incident_date", """
SELECT COALESCE(d.department_name, 'Unassigned') AS x,
       CAST(date_trunc('month', i.incident_date) AS DATE) AS y, COUNT(*) AS value
FROM (SELECT * FROM silver_incidents{where}) i
LEFT JOIN silver_dim_department d ON d.department_id = i.department_id
GROUP BY 1, 2 ORDER BY 2, 1 LIMIT 300
"""), methods=["GET"])

# ---------------------------------------------------------------------------
# Data quality & pipeline
# ---------------------------------------------------------------------------
router.add_api_route("/dq/datasets", grouped("dq_rules", "table_name",
    "AVG(CASE WHEN checked_count > 0 THEN 100.0 * (1 - failed_count * 1.0 / checked_count) "
    "ELSE CASE WHEN passed THEN 100.0 ELSE 0.0 END END)", "quality_score", 40,
    date_col="checked_at"), methods=["GET"])
router.add_api_route("/dq/severity", grouped("dq_rules", "severity",
    "COUNT(*)", "rules", 10, date_col="checked_at"), methods=["GET"])
router.add_api_route("/dq/categories", grouped("dq_rules", "category",
    "SUM(failed_count)", "failures", 20, date_col="checked_at"), methods=["GET"])
router.add_api_route("/dq/runs", grouped("pipeline_runs", "run_id",
    "SUM(source_records)", "source_records", 20, date_col="start_time"), methods=["GET"])
router.add_api_route("/dq/volume", multi("pipeline_runs", "start_time", {
    "source_records": "SUM(source_records)",
    "valid_records": "SUM(valid_records)",
    "quarantined_records": "SUM(quarantined_records)",
}), methods=["GET"])
router.add_api_route("/dq/completeness", grouped("dq_rules", "table_name",
    "AVG(CASE WHEN checked_count > 0 THEN 100.0 * (1 - failed_count * 1.0 / checked_count) "
    "ELSE CASE WHEN passed THEN 100.0 ELSE 0.0 END END)", "completeness", 40,
    date_col="checked_at", extra_where="LOWER(category) = 'completeness'"), methods=["GET"])
router.add_api_route("/dq/uniqueness", grouped("dq_rules", "table_name",
    "SUM(failed_count)", "violations", 40, date_col="checked_at",
    extra_where="LOWER(category) = 'uniqueness'"), methods=["GET"])
router.add_api_route("/dq/validity", grouped("dq_rules", "rule_name",
    "SUM(failed_count)", "failures", 20, date_col="checked_at",
    extra_where="LOWER(category) = 'validity'"), methods=["GET"])
router.add_api_route("/dq/consistency", grouped("dq_rules", "rule_name",
    "SUM(CASE WHEN passed THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0)", "pass_rate", 20,
    date_col="checked_at", extra_where="LOWER(category) = 'consistency'"), methods=["GET"])
router.add_api_route("/dq/rule-pass-rate", grouped("dq_rules", "category",
    "SUM(CASE WHEN passed THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0)", "pass_rate", 20,
    date_col="checked_at"), methods=["GET"])
router.add_api_route("/dq/validation-trend", multi("dq_rules", "checked_at", {
    "rules": "COUNT(*)",
    "passed": "SUM(CASE WHEN passed THEN 1 ELSE 0 END)",
    "failures": "SUM(failed_count)",
}), methods=["GET"])
router.add_api_route("/dq/quarantine-trend", multi("pipeline_runs", "start_time", {
    "quarantined_records": "SUM(quarantined_records)",
    "valid_records": "SUM(valid_records)",
}), methods=["GET"])
router.add_api_route("/dq/missing-by-column", grouped("dq_rules", "rule_name",
    "SUM(failed_count)", "missing", 20, date_col="checked_at",
    extra_where="LOWER(rule_name) LIKE '%missing%' OR LOWER(rule_name) LIKE '%present%'"), methods=["GET"])
router.add_api_route("/dq/duplicates", grouped("dq_rules", "table_name",
    "SUM(failed_count)", "duplicates", 40, date_col="checked_at",
    extra_where="LOWER(rule_name) LIKE '%unique%' OR LOWER(rule_name) LIKE '%duplicate%'"), methods=["GET"])

router.add_api_route("/dq/quarantine-by-rule", grouped("dq_failures", "rule_id",
    "COUNT(*)", "quarantined", 20, date_col="detected_at"), methods=["GET"])
router.add_api_route("/dq/quarantine-by-dataset", grouped("dq_failures", "table_name",
    "COUNT(*)", "quarantined", 40, date_col="detected_at"), methods=["GET"])


@router.get("/dq/injected-vs-detected")
def dq_injected_vs_detected(request: Request) -> dict[str, Any]:
    """Compare generator-injected DQ issues against quarantine detections."""
    f = parse_filters(request)
    manifest_path = DATA_PATH / "manifests" / "generator_manifest.json"
    injected: list[dict[str, Any]] = []
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            manifest = {}
        injected = manifest.get("dq_injections", []) or []

    rule_map = {
        "duplicate_patients": "PK_DUPLICATE",
        "missing_payer": "FK_NULL",
        "invalid_dates": "REQUIRED_DATE_INVALID",
        "unknown_department": "FK_ORPHAN",
        "invalid_status": "STATUS_INVALID",
        "incorrect_hospital_id": "HOSPITAL_ID_INVALID",
        "negative_amounts": "NEGATIVE_AMOUNT",
        "orphaned_references": "FK_ORPHAN",
    }

    with get_conn() as conn:
        detected_rows = query_rows(
            conn,
            "SELECT rule_id, table_name, COUNT(*) AS detected, COUNT(DISTINCT record_id) AS distinct_records "
            "FROM dq_failures GROUP BY 1, 2",
        )
    detected_index: dict[tuple[str, str], dict[str, int]] = {}
    for r in detected_rows:
        key = (str(r.get("rule_id") or ""), str(r.get("table_name") or ""))
        detected_index[key] = {
            "detected": int(r.get("detected") or 0),
            "distinct_records": int(r.get("distinct_records") or 0),
        }

    rows: list[dict[str, Any]] = []
    for inj in injected:
        issue_type = str(inj.get("issue_type") or "")
        table = str(inj.get("table") or "")
        injected_count = int(inj.get("count") or len(inj.get("row_identifiers") or []))
        rule_id = rule_map.get(issue_type, "")
        det = detected_index.get((rule_id, table), {"detected": 0, "distinct_records": 0})
        detected_count = det["detected"]
        # orphaned_references on prescriptions is detected as FK_ORPHAN; cascades can inflate table count.
        note = "match" if detected_count == injected_count else "mismatch"
        if issue_type == "orphaned_references" and detected_count >= injected_count:
            note = "detected (includes cascade orphans)" if detected_count > injected_count else "match"
        rows.append({
            "label": issue_type.replace("_", " ").title(),
            "issue_type": issue_type,
            "table": table,
            "rule_id": rule_id,
            "injected": injected_count,
            "detected": detected_count,
            "distinct_records": det["distinct_records"],
            "delta": detected_count - injected_count,
            "status": note,
        })

    total_injected = sum(int(r["injected"]) for r in rows)
    total_detected = sum(int(r["detected"]) for r in rows)
    return envelope(
        rows,
        f.date_from,
        f.date_to,
        f.hospital_ids,
        total_injected=total_injected,
        total_detected=total_detected,
        total_quarantine_rule_failures=sum(int(r.get("detected") or 0) for r in detected_rows),
        total_quarantined_distinct_records=sum(int(r.get("distinct_records") or 0) for r in detected_rows),
    )
