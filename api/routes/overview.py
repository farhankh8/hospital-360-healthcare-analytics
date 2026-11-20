"""Network overview endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api.core.db import get_conn
from api.core.filters import build_where, parse_filters
from api.core.responses import envelope
from api.routes.common import make_kpis_route
from api.services.query import columns, query_rows

router = APIRouter(prefix="/overview", tags=["overview"])

router.add_api_route("/kpis", make_kpis_route("overview"), methods=["GET"])

RANK_METRICS = {
    "revenue": "SUM(m.net_revenue)",
    "patient_volume": "SUM(m.encounters)",
    "occupancy": "SUM(m.occupied_bed_days) * 100.0 / NULLIF(SUM(m.available_bed_days), 0)",
    "satisfaction": "SUM(m.avg_satisfaction * m.feedback_count) / NULLIF(SUM(m.feedback_count), 0)",
    "los": "SUM(m.avg_los_days * m.discharges) / NULLIF(SUM(m.discharges), 0)",
}


@router.get("/trends")
def trends(request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        cols = columns(conn, "gold_network_daily")
        where, params = build_where(f, cols, date_col="date")
        rows = query_rows(
            conn,
            "SELECT CAST(date AS DATE) AS period, SUM(encounters) AS encounters, "
            "SUM(admissions) AS admissions, SUM(appointments) AS appointments, "
            "SUM(revenue) AS revenue, SUM(collections) AS collections, "
            "GREATEST(SUM(revenue) - SUM(collections), 0) AS outstanding "
            f"FROM gold_network_daily{where} GROUP BY 1 ORDER BY 1",
            params,
        )
        # Fallback when the daily gold table is empty: derive from monthly.
        if not rows:
            cols = columns(conn, "gold_hospital_monthly")
            where, params = build_where(f, cols, date_col="month")
            rows = query_rows(
                conn,
                "SELECT CAST(month AS DATE) AS period, SUM(encounters) AS encounters, "
                "SUM(admissions) AS admissions, SUM(appointments) AS appointments, "
                "SUM(net_revenue) AS revenue, SUM(collections) AS collections, "
                "SUM(outstanding_balance) AS outstanding "
                f"FROM gold_hospital_monthly{where} GROUP BY 1 ORDER BY 1",
                params,
            )
    return envelope(rows, f.date_from, f.date_to, f.hospital_ids, grain="month")


@router.get("/hospital-ranking")
def hospital_ranking(request: Request, metric: str = "revenue"):
    if metric not in RANK_METRICS:
        raise HTTPException(400, f"Unknown metric. Allowed: {', '.join(RANK_METRICS)}")
    f = parse_filters(request)
    with get_conn() as conn:
        cols = columns(conn, "gold_hospital_monthly")
        where, params = build_where(f, cols, date_col="month")
        where = where.replace("hospital_id IN", "m.hospital_id IN")
        where = where.replace("CAST(month AS DATE)", "CAST(m.month AS DATE)")
        expr = RANK_METRICS[metric]
        rows = query_rows(
            conn,
            f"SELECT m.hospital_id, COALESCE(h.hospital_name, m.hospital_name) AS hospital_name, "
            f"{expr} AS value FROM gold_hospital_monthly m "
            "LEFT JOIN dim_hospital h ON h.hospital_id = m.hospital_id"
            f"{where} GROUP BY 1, 2 ORDER BY value DESC",
            params,
        )
    return envelope(rows, f.date_from, f.date_to, f.hospital_ids, metric=metric)


@router.get("/heatmap")
def heatmap(request: Request):
    f = parse_filters(request)
    metrics = {
        "occupancy": "SUM(occupied_bed_days) * 100.0 / NULLIF(SUM(available_bed_days), 0)",
        "no_show_rate": "SUM(no_show_appointments) * 100.0 / NULLIF(SUM(completed_appointments + no_show_appointments), 0)",
        "average_los": "SUM(avg_los_days * discharges) / NULLIF(SUM(discharges), 0)",
        "satisfaction": "SUM(avg_satisfaction * feedback_count) / NULLIF(SUM(feedback_count), 0)",
        "denial_rate": "SUM(denial_rate * claims_submitted) / NULLIF(SUM(claims_submitted), 0)",
        "revenue_growth": "AVG(net_revenue)",
    }
    with get_conn() as conn:
        cols = columns(conn, "gold_hospital_monthly")
        where, params = build_where(f, cols, date_col="month")
        where = where.replace("hospital_id IN", "m.hospital_id IN").replace("CAST(month AS DATE)", "CAST(m.month AS DATE)")
        select = ["m.hospital_id", "COALESCE(h.hospital_name, m.hospital_name) AS hospital_name"]
        for name, expr in metrics.items():
            select.append(f"{expr} AS {name}")
        rows = query_rows(
            conn,
            "SELECT " + ", ".join(select) + " FROM gold_hospital_monthly m "
            "LEFT JOIN dim_hospital h ON h.hospital_id = m.hospital_id"
            f"{where} GROUP BY 1, 2 ORDER BY 1",
            params,
        )
    return envelope(rows, f.date_from, f.date_to, f.hospital_ids, metrics=list(metrics))


@router.get("/distribution")
def distribution(request: Request, by: str = "hospital"):
    if by not in {"hospital", "department", "specialty"}:
        raise HTTPException(400, "by must be hospital, department or specialty")
    f = parse_filters(request)
    with get_conn() as conn:
        if by == "hospital":
            cols = columns(conn, "gold_hospital_monthly")
            where, params = build_where(f, cols, date_col="month")
            rows = query_rows(
                conn,
                "SELECT e.hospital_id AS label, COUNT(*) AS value FROM silver_encounters e"
                f"{where.replace('month', 'arrival_datetime')} GROUP BY 1 ORDER BY 2 DESC",
                params,
            )
        else:
            cols = columns(conn, "gold_department_monthly")
            where, params = build_where(f, cols, date_col="month")
            key = "department_name" if by == "department" else "specialty_name"
            rows = query_rows(
                conn,
                f"SELECT {key} AS label, SUM(patients) AS value FROM gold_department_monthly"
                f"{where} GROUP BY 1 ORDER BY 2 DESC LIMIT 20",
                params,
            )
    return envelope(rows, f.date_from, f.date_to, f.hospital_ids, group_by=by)


@router.get("/operational")
def operational(request: Request):
    """Normalised 0-100 domain scores for a radar chart. Normalisation is documented."""
    f = parse_filters(request)
    scores = {
        "Access": "100 - COALESCE(SUM(no_show_appointments) * 100.0 / NULLIF(SUM(completed_appointments + no_show_appointments), 0), 0)",
        "Capacity": "COALESCE(SUM(occupied_bed_days) * 100.0 / NULLIF(SUM(available_bed_days), 0), 0)",
        "Finance": "COALESCE(SUM(collections) * 100.0 / NULLIF(SUM(net_revenue), 0), 0)",
        "Experience": "COALESCE(SUM(avg_satisfaction * feedback_count) / NULLIF(SUM(feedback_count), 0) * 20, 0)",
        "Workforce": "LEAST(COALESCE(SUM(worked_hours) * 100.0 / NULLIF(SUM(scheduled_hours), 0), 0), 100)",
    }
    with get_conn() as conn:
        cols = columns(conn, "gold_hospital_monthly")
        where, params = build_where(f, cols, date_col="month")
        sql = ", ".join(f"{expr} AS \"{name}\"" for name, expr in scores.items())
        row = query_rows(conn, f"SELECT {sql} FROM gold_hospital_monthly{where}", params)
    data = [{"domain": k, "score": round(float(row[0][k] or 0), 2)} for k in scores] if row else []
    return envelope(
        data, f.date_from, f.date_to, f.hospital_ids,
        normalisation="Access=100-no_show_rate; Capacity=occupancy; Finance=collection_rate; "
                      "Experience=avg rating/5*100; Workforce=worked/scheduled hours capped at 100.",
    )
