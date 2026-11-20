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
            "WHERE d.hospital_id = $hospital_id ORDER BY d.department_name",
            {"hospital_id": hospital_id},
        )
        if not rows:
            rows = query_rows(
                conn,
                "SELECT department_id, department_name, specialty_id AS specialty_name "
                "FROM silver_dim_department WHERE hospital_id = $hospital_id ORDER BY department_name",
                {"hospital_id": hospital_id},
            )
    return envelope(rows, f.date_from, f.date_to, [hospital_id])


@router.get("/{hospital_id}/trends")
def hospital_trends(hospital_id: str, request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        cols = columns(conn, "gold_hospital_monthly")
        where, params = build_where(f, cols, date_col="month")
        where = (where + " AND hospital_id = $hid") if where else " WHERE hospital_id = $hid"
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
            conn, "SELECT * FROM dim_hospital WHERE hospital_id = $hospital_id", {"hospital_id": hospital_id}
        )
        if not hospital:
            hospital = query_rows(
                conn, "SELECT * FROM silver_dim_hospital WHERE hospital_id = $hospital_id", {"hospital_id": hospital_id}
            )
        if not hospital:
            raise HTTPException(404, f"Hospital {hospital_id} not found")
        cols = columns(conn, "gold_hospital_monthly")
        where, params = build_where(f, cols, date_col="month")
        where = (where + " AND hospital_id = $hid") if where else " WHERE hospital_id = $hid"
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


def _hospital_where(request: Request, hospital_id: str, table: str, date_col: str = "month"):
    f = parse_filters(request)
    with get_conn() as conn:
        available = columns(conn, table)
    where, params = build_where(f, available, date_col=date_col)
    where = (where + " AND hospital_id = $hid") if where else " WHERE hospital_id = $hid"
    params["hid"] = hospital_id
    return f, where, params


@router.get("/{hospital_id}/bed-occupancy")
def hospital_bed_occupancy(hospital_id: str, request: Request):
    f, where, params = _hospital_where(request, hospital_id, "gold_bed_utilization")
    with get_conn() as conn:
        rows = query_rows(
            conn,
            "SELECT CAST(month AS DATE) AS period, "
            "SUM(occupied_bed_days) * 100.0 / NULLIF(SUM(available_bed_days), 0) AS occupancy_rate, "
            "SUM(available_bed_days) AS available_bed_days "
            f"FROM gold_bed_utilization{where} GROUP BY 1 ORDER BY 1",
            params,
        )
    return envelope(rows, f.date_from, f.date_to, [hospital_id])


@router.get("/{hospital_id}/patient-mix")
def hospital_patient_mix(hospital_id: str, request: Request):
    f, where, params = _hospital_where(request, hospital_id, "silver_encounters", "arrival_datetime")
    with get_conn() as conn:
        rows = query_rows(
            conn,
            "SELECT p.patient_type AS label, COUNT(*) AS patients "
            f"FROM (SELECT * FROM silver_encounters{where}) e "
            "JOIN silver_patients p ON p.patient_id = e.patient_id "
            "GROUP BY 1 ORDER BY 2 DESC",
            params,
        )
    return envelope(rows, f.date_from, f.date_to, [hospital_id])


@router.get("/{hospital_id}/doctor-performance")
def hospital_doctor_performance(hospital_id: str, request: Request):
    f, where, params = _hospital_where(request, hospital_id, "silver_procedures", "scheduled_start")
    with get_conn() as conn:
        rows = query_rows(
            conn,
            "SELECT COALESCE(d.doctor_name, p.surgeon_id) AS label, COUNT(*) AS procedures, "
            "SUM(p.revenue) AS revenue "
            f"FROM (SELECT * FROM silver_procedures{where}) p "
            "LEFT JOIN silver_dim_doctor d ON d.doctor_id = p.surgeon_id "
            "GROUP BY 1 ORDER BY 2 DESC LIMIT 12",
            params,
        )
    return envelope(rows, f.date_from, f.date_to, [hospital_id])


@router.get("/{hospital_id}/appointment-performance")
def hospital_appointment_performance(hospital_id: str, request: Request):
    f, where, params = _hospital_where(request, hospital_id, "gold_patient_access")
    with get_conn() as conn:
        rows = query_rows(
            conn,
            "SELECT CAST(month AS DATE) AS period, SUM(scheduled) AS scheduled, "
            "SUM(completed) AS completed, SUM(cancelled) AS cancelled, SUM(no_shows) AS no_shows "
            f"FROM gold_patient_access{where} GROUP BY 1 ORDER BY 1",
            params,
        )
    return envelope(rows, f.date_from, f.date_to, [hospital_id])


@router.get("/{hospital_id}/network-comparison")
def hospital_network_comparison(hospital_id: str, request: Request):
    f = parse_filters(request)
    with get_conn() as conn:
        cols = columns(conn, "gold_hospital_monthly")
        where, params = build_where(f, cols, date_col="month")
        rows = query_rows(
            conn,
            "SELECT hospital_id AS label, "
            "SUM(occupied_bed_days) * 100.0 / NULLIF(SUM(available_bed_days), 0) AS occupancy_rate, "
            "AVG(avg_satisfaction) AS satisfaction, "
            "SUM(net_revenue) AS net_revenue, "
            f"MAX(CASE WHEN hospital_id = $hid THEN 1 ELSE 0 END) AS selected "
            f"FROM gold_hospital_monthly{where} GROUP BY 1 ORDER BY 2 DESC",
            {**params, "hid": hospital_id},
        )
    return envelope(rows, f.date_from, f.date_to, [hospital_id])
