"""Hospital list, comparison and profile endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api.core.db import get_conn
from api.core.filters import build_where, parse_filters
from api.core.responses import envelope
from api.services.kpi_specs import HOSPITAL
from api.services.metrics import build_kpis, period_metadata
from api.services.query import columns, query_rows

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@router.get("")
def list_hospitals(request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        rows = query_rows(
            conn,
            "SELECT hospital_id, hospital_name, city, profile, hospital_type, beds, status "
            "FROM dim_hospital ORDER BY hospital_id",
        )
    return envelope(rows, f.date_from, f.date_to, f.hospital_ids)


@router.get("/{hospital_id}/kpis")
def hospital_kpis(hospital_id: str, request: Request):
    f = parse_filters(request)
    f.hospital_ids = [hospital_id]
    with get_conn() as conn:
        data = build_kpis(conn, f, HOSPITAL)
    return envelope(data, f.date_from, f.date_to, f.hospital_ids, **period_metadata(f))


@router.get("/{hospital_id}/departments")
def hospital_departments(hospital_id: str, request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        rows = query_rows(
            conn,
            "SELECT d.department_id, d.department_name, s.specialty_name "
            "FROM dim_department d LEFT JOIN dim_specialty s ON s.specialty_id = d.specialty_id "
            "WHERE d.hospital_id = ? ORDER BY d.department_name",
            {"hospital_id": hospital_id},
        )
        if not rows:
            rows = query_rows(
                conn,
                "SELECT department_id, department_name, specialty_id AS specialty_name "
                "FROM silver_dim_department WHERE hospital_id = ? ORDER BY department_name",
                {"hospital_id": hospital_id},
            )
    return envelope(rows, f.date_from, f.date_to, [hospital_id])


@router.get("/{hospital_id}/trends")
def hospital_trends(hospital_id: str, request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        cols = columns(conn, "gold_hospital_monthly")
        where, params = build_where(f, cols, date_col="month")
        where = (where + " AND hospital_id = :hid") if where else " WHERE hospital_id = :hid"
        params["hid"] = hospital_id
        rows = query_rows(
            conn,
            "SELECT CAST(month AS DATE) AS period, SUM(encounters) AS encounters, "
            "SUM(admissions) AS admissions, SUM(gross_revenue) AS revenue, "
            "SUM(occupied_bed_days) * 100.0 / NULLIF(SUM(available_bed_days), 0) AS occupancy "
            f"FROM gold_hospital_monthly{where} GROUP BY 1 ORDER BY 1",
            params,
        )
    return envelope(rows, f.date_from, f.date_to, [hospital_id])


@router.get("/{hospital_id}/profile")
def hospital_profile(hospital_id: str, request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        hospital = query_rows(
            conn, "SELECT * FROM dim_hospital WHERE hospital_id = ?", {"hospital_id": hospital_id}
        )
        if not hospital:
            hospital = query_rows(
                conn, "SELECT * FROM silver_dim_hospital WHERE hospital_id = ?", {"hospital_id": hospital_id}
            )
        if not hospital:
            raise HTTPException(404, f"Hospital {hospital_id} not found")
        cols = columns(conn, "gold_hospital_monthly")
        where, params = build_where(f, cols, date_col="month")
        where = (where + " AND hospital_id = :hid") if where else " WHERE hospital_id = :hid"
        params["hid"] = hospital_id
        summary = query_rows(
            conn,
            "SELECT SUM(encounters) AS encounters, SUM(admissions) AS admissions, "
            "SUM(gross_revenue) AS revenue, SUM(occupied_bed_days) * 100.0 / "
            "NULLIF(SUM(available_bed_days), 0) AS occupancy, "
            "SUM(avg_los_days * discharges) / NULLIF(SUM(discharges), 0) AS average_los "
            f"FROM gold_hospital_monthly{where}",
            params,
        )
        network = query_rows(
            conn,
            "SELECT SUM(occupied_bed_days) * 100.0 / NULLIF(SUM(available_bed_days), 0) AS network_occupancy, "
            "SUM(avg_los_days * discharges) / NULLIF(SUM(discharges), 0) AS network_los "
            "FROM gold_hospital_monthly"
            + build_where(f, cols, date_col="month")[0],
            build_where(f, cols, date_col="month")[1],
        )
    return envelope(
        {"hospital": hospital[0], "summary": summary[0] if summary else {}, "network": network[0] if network else {}},
        f.date_from, f.date_to, [hospital_id],
    )
