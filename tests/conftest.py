"""Shared pytest fixtures for HOSPITAL 360.

Unit tests use small, hand-built DataFrames with known values so they never need the
full generated dataset. Optional fixtures skip (not fail) when data files or source
modules are not present yet, which is expected while other layers are being built.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_optional(module: str) -> Any | None:
    """Import a module that may not exist yet; return None instead of raising."""
    try:
        return importlib.import_module(module)
    except Exception:  # noqa: BLE001 - parallel layers may be incomplete
        return None


def require_module(module: str) -> Any:
    found = load_optional(module)
    if found is None:
        pytest.skip(f"optional module {module!r} is not available yet")
    return found


def _frame(table: str, rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Build a frame using canonical schema columns; fall back to row keys."""
    schema = load_optional("generator.schema")
    columns = schema.columns(table) if schema and hasattr(schema, "columns") else list(rows[0])
    return pd.DataFrame(rows).reindex(columns=columns)


def _ts(value: str) -> pd.Timestamp:
    return pd.Timestamp(value)


# ---------------------------------------------------------------------------
# Inline sample data (small, deterministic, known values)
# ---------------------------------------------------------------------------
@pytest.fixture
def patients() -> pd.DataFrame:
    return _frame("patients", [
        {"patient_id": "PAT000001", "first_name": "Ada", "last_name": "One",
         "birth_date": "1980-05-10", "gender": "Female", "city": "Downtown",
         "state": "Region A", "registration_date": "2024-12-20", "blood_type": "O+",
         "patient_type": "Returning"},
        {"patient_id": "PAT000002", "first_name": "Ben", "last_name": "Two",
         "birth_date": "1992-08-14", "gender": "Male", "city": "Northside",
         "state": "Region B", "registration_date": "2025-01-02", "blood_type": "A+",
         "patient_type": "New"},
        {"patient_id": "PAT000003", "first_name": "Cy", "last_name": "Three",
         "birth_date": "1975-02-28", "gender": "Other", "city": "Westgate",
         "state": "Region C", "registration_date": "2025-01-05", "blood_type": "B+",
         "patient_type": "New"},
    ])


@pytest.fixture
def appointments() -> pd.DataFrame:
    return _frame("appointments", [
        {"appointment_id": "APT0000001", "patient_id": "PAT000001", "hospital_id": "H01",
         "department_id": "D001", "doctor_id": "DOC0001", "booking_date": "2025-01-01",
         "appointment_date": "2025-01-10", "appointment_type": "Follow-up",
         "status": "Completed", "checkin_datetime": "2025-01-10 08:55:00",
         "waiting_minutes": 5.0, "cancellation_reason": None,
         "booking_channel": "Online", "lead_days": 9, "rescheduled_flag": False},
        {"appointment_id": "APT0000002", "patient_id": "PAT000002", "hospital_id": "H01",
         "department_id": "D001", "doctor_id": "DOC0001", "booking_date": "2025-01-02",
         "appointment_date": "2025-01-11", "appointment_type": "New",
         "status": "Completed", "checkin_datetime": "2025-01-11 09:00:00",
         "waiting_minutes": 12.0, "cancellation_reason": None,
         "booking_channel": "Phone", "lead_days": 9, "rescheduled_flag": False},
        {"appointment_id": "APT0000003", "patient_id": "PAT000003", "hospital_id": "H03",
         "department_id": "D023", "doctor_id": "DOC0023", "booking_date": "2025-01-03",
         "appointment_date": "2025-01-12", "appointment_type": "Routine",
         "status": "No-show", "checkin_datetime": None, "waiting_minutes": None,
         "cancellation_reason": None, "booking_channel": "Online",
         "lead_days": 9, "rescheduled_flag": False},
        {"appointment_id": "APT0000004", "patient_id": "PAT000001", "hospital_id": "H03",
         "department_id": "D023", "doctor_id": "DOC0023", "booking_date": "2025-01-04",
         "appointment_date": "2025-01-13", "appointment_type": "Urgent",
         "status": "No-show", "checkin_datetime": None, "waiting_minutes": None,
         "cancellation_reason": None, "booking_channel": "Walk-in",
         "lead_days": 9, "rescheduled_flag": True},
        {"appointment_id": "APT0000005", "patient_id": "PAT000002", "hospital_id": "H01",
         "department_id": "D001", "doctor_id": "DOC0001", "booking_date": "2025-01-05",
         "appointment_date": "2025-01-14", "appointment_type": "Routine",
         "status": "Cancelled", "checkin_datetime": None, "waiting_minutes": None,
         "cancellation_reason": "Patient request", "booking_channel": "Portal",
         "lead_days": 9, "rescheduled_flag": False},
        {"appointment_id": "APT0000006", "patient_id": "PAT000003", "hospital_id": "H03",
         "department_id": "D023", "doctor_id": "DOC0023", "booking_date": "2025-01-06",
         "appointment_date": "2025-01-15", "appointment_type": "Follow-up",
         "status": "Scheduled", "checkin_datetime": None, "waiting_minutes": None,
         "cancellation_reason": None, "booking_channel": "Online",
         "lead_days": 9, "rescheduled_flag": False},
    ])


@pytest.fixture
def encounters() -> pd.DataFrame:
    return _frame("encounters", [
        {"encounter_id": "ENC0000001", "patient_id": "PAT000001",
         "appointment_id": "APT0000001", "hospital_id": "H01", "department_id": "D001",
         "encounter_type": "Outpatient", "arrival_datetime": "2025-01-10 09:00:00",
         "triage_category": "Standard", "triage_datetime": "2025-01-10 09:05:00",
         "provider_datetime": "2025-01-10 09:20:00",
         "disposition_datetime": "2025-01-10 09:50:00", "waiting_minutes": 20.0,
         "treatment_minutes": 30.0, "disposition": "Discharge",
         "arrival_mode": "Walk-in", "critical_flag": False},
        {"encounter_id": "ENC0000002", "patient_id": "PAT000002",
         "appointment_id": "APT0000002", "hospital_id": "H01", "department_id": "D001",
         "encounter_type": "Outpatient", "arrival_datetime": "2025-01-11 09:00:00",
         "triage_category": "Standard", "triage_datetime": "2025-01-11 09:04:00",
         "provider_datetime": "2025-01-11 09:15:00",
         "disposition_datetime": "2025-01-11 09:45:00", "waiting_minutes": 15.0,
         "treatment_minutes": 30.0, "disposition": "Discharge",
         "arrival_mode": "Walk-in", "critical_flag": False},
        {"encounter_id": "ENC0000003", "patient_id": "PAT000003",
         "appointment_id": "APT0000003", "hospital_id": "H03", "department_id": "D023",
         "encounter_type": "Emergency", "arrival_datetime": "2025-01-12 10:00:00",
         "triage_category": "Urgent", "triage_datetime": "2025-01-12 10:03:00",
         "provider_datetime": "2025-01-12 10:25:00",
         "disposition_datetime": "2025-01-12 11:10:00", "waiting_minutes": 25.0,
         "treatment_minutes": 45.0, "disposition": "Admit",
         "arrival_mode": "Ambulance", "critical_flag": True},
        {"encounter_id": "ENC0000004", "patient_id": "PAT000002",
         "appointment_id": None, "hospital_id": "H03", "department_id": "D023",
         "encounter_type": "Emergency", "arrival_datetime": "2025-02-01 12:00:00",
         "triage_category": "Non-urgent", "triage_datetime": "2025-02-01 12:06:00",
         "provider_datetime": "2025-02-01 12:30:00",
         "disposition_datetime": "2025-02-01 13:00:00", "waiting_minutes": 30.0,
         "treatment_minutes": 30.0, "disposition": "Discharge",
         "arrival_mode": "Walk-in", "critical_flag": False},
    ])


@pytest.fixture
def admissions() -> pd.DataFrame:
    return _frame("admissions", [
        {"admission_id": "ADM000001", "encounter_id": "ENC0000003",
         "patient_id": "PAT000003", "hospital_id": "H03", "department_id": "D023",
         "ward": "Cardiology", "bed_id": "BED-H03-0001",
         "admission_datetime": "2025-01-12 11:00:00",
         "discharge_datetime": "2025-01-15 11:00:00", "admission_type": "Emergency",
         "discharge_status": "Recovered", "los_days": 3.0,
         "readmission_flag": False, "boarding_hours": 1.0},
        {"admission_id": "ADM000002", "encounter_id": "ENC0000002",
         "patient_id": "PAT000002", "hospital_id": "H01", "department_id": "D001",
         "ward": "General", "bed_id": "BED-H01-0001",
         "admission_datetime": "2025-01-20 08:00:00",
         "discharge_datetime": "2025-01-22 08:00:00", "admission_type": "Elective",
         "discharge_status": "Recovered", "los_days": 2.0,
         "readmission_flag": True, "boarding_hours": 0.5},
        # Open admission: must not enter the LOS denominator.
        {"admission_id": "ADM000003", "encounter_id": "ENC0000001",
         "patient_id": "PAT000001", "hospital_id": "H01", "department_id": "D001",
         "ward": "General", "bed_id": "BED-H01-0002",
         "admission_datetime": "2025-02-01 08:00:00",
         "discharge_datetime": None, "admission_type": "Elective",
         "discharge_status": None, "los_days": None,
         "readmission_flag": False, "boarding_hours": 0.0},
    ])


@pytest.fixture
def claims() -> pd.DataFrame:
    return _frame("claims", [
        {"claim_id": "CLM0000001", "invoice_id": "INV0000001",
         "patient_id": "PAT000001", "hospital_id": "H01", "payer_id": "P01",
         "claim_date": "2025-01-16", "claim_amount": 1000.0,
         "approved_amount": 1000.0, "paid_amount": 900.0, "status": "Approved",
         "denial_reason": None, "processing_days": 5.0, "claim_type": "Outpatient"},
        {"claim_id": "CLM0000002", "invoice_id": "INV0000002",
         "patient_id": "PAT000002", "hospital_id": "H01", "payer_id": "P01",
         "claim_date": "2025-01-17", "claim_amount": 500.0,
         "approved_amount": 0.0, "paid_amount": 0.0, "status": "Denied",
         "denial_reason": "Missing authorization", "processing_days": 4.0,
         "claim_type": "Outpatient"},
        {"claim_id": "CLM0000003", "invoice_id": "INV0000003",
         "patient_id": "PAT000003", "hospital_id": "H03", "payer_id": "P02",
         "claim_date": "2025-01-18", "claim_amount": 2000.0,
         "approved_amount": 0.0, "paid_amount": 0.0, "status": "Denied",
         "denial_reason": "Coding error", "processing_days": 7.0,
         "claim_type": "Inpatient"},
        {"claim_id": "CLM0000004", "invoice_id": "INV0000004",
         "patient_id": "PAT000002", "hospital_id": "H03", "payer_id": "P02",
         "claim_date": "2025-01-19", "claim_amount": 800.0,
         "approved_amount": 0.0, "paid_amount": 0.0, "status": "Pending",
         "denial_reason": None, "processing_days": None, "claim_type": "Emergency"},
    ])


@pytest.fixture
def bed_snapshots() -> pd.DataFrame:
    return _frame("bed_snapshots", [
        {"snapshot_id": "SNP0000001", "snapshot_datetime": "2025-01-10 08:00:00",
         "hospital_id": "H01", "ward": "ICU", "bed_id": "BED-H01-0001",
         "bed_type": "ICU", "status": "Occupied", "occupied_flag": True,
         "blocked_flag": False},
        {"snapshot_id": "SNP0000002", "snapshot_datetime": "2025-01-10 08:00:00",
         "hospital_id": "H01", "ward": "ICU", "bed_id": "BED-H01-0002",
         "bed_type": "ICU", "status": "Available", "occupied_flag": False,
         "blocked_flag": False},
        {"snapshot_id": "SNP0000003", "snapshot_datetime": "2025-01-10 08:00:00",
         "hospital_id": "H01", "ward": "ICU", "bed_id": "BED-H01-0003",
         "bed_type": "ICU", "status": "Blocked", "occupied_flag": False,
         "blocked_flag": True},
        {"snapshot_id": "SNP0000004", "snapshot_datetime": "2025-01-10 09:00:00",
         "hospital_id": "H01", "ward": "ICU", "bed_id": "BED-H01-0001",
         "bed_type": "ICU", "status": "Occupied", "occupied_flag": True,
         "blocked_flag": False},
        {"snapshot_id": "SNP0000005", "snapshot_datetime": "2025-01-10 09:00:00",
         "hospital_id": "H01", "ward": "ICU", "bed_id": "BED-H01-0002",
         "bed_type": "ICU", "status": "Available", "occupied_flag": False,
         "blocked_flag": False},
        {"snapshot_id": "SNP0000006", "snapshot_datetime": "2025-01-10 09:00:00",
         "hospital_id": "H01", "ward": "ICU", "bed_id": "BED-H01-0003",
         "bed_type": "ICU", "status": "Blocked", "occupied_flag": False,
         "blocked_flag": True},
    ])


@pytest.fixture
def samples(patients, appointments, encounters, admissions, claims, bed_snapshots):
    """Bundle all inline sample frames under one convenient object."""
    return SimpleNamespace(
        patients=patients,
        appointments=appointments,
        encounters=encounters,
        admissions=admissions,
        claims=claims,
        bed_snapshots=bed_snapshots,
    )


@pytest.fixture
def dirty_appointments(appointments: pd.DataFrame) -> pd.DataFrame:
    """Status/dtype/noise cases for silver-layer tests."""
    dirty = appointments.copy()
    dirty.loc[0, "status"] = "COMPLETED "
    dirty.loc[1, "status"] = "no_show"
    dirty.loc[2, "hospital_id"] = " h01 "
    dirty.loc[3, "hospital_id"] = "UNKNOWN"
    dirty = pd.concat([dirty, dirty.iloc[[0]]], ignore_index=True)  # duplicate PK
    return dirty


# ---------------------------------------------------------------------------
# Optional fixtures: skip (never fail) when real data is not available
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def data_dir() -> Path:
    config = load_optional("generator.config")
    root = Path(config.DATA_DIR) if config and hasattr(config, "DATA_DIR") else ROOT / "data"
    return Path(root)


@pytest.fixture(scope="session")
def bronze_dir(data_dir: Path) -> Path:
    path = data_dir / "bronze"
    if not path.exists() or not any(path.rglob("*.csv")):
        pytest.skip("bronze CSVs not generated yet (run python -m generator.generate)")
    return path


@pytest.fixture(scope="session")
def duckdb_path(data_dir: Path) -> Path:
    api_config = load_optional("api.core.config")
    path = (
        Path(api_config.DATABASE_PATH)
        if api_config and hasattr(api_config, "DATABASE_PATH")
        else data_dir / "hospital360.duckdb"
    )
    if not path.exists() or path.stat().st_size == 0:
        pytest.skip("DuckDB database not built yet (run python -m etl.pipeline)")
    return path


@pytest.fixture(scope="session")
def duckdb_conn(duckdb_path: Path):
    duckdb = pytest.importorskip("duckdb")

    class _ReadOnlyDB:
        """Tiny helper so tests can run SQL without sharing a connection."""

        def __init__(self, path: Path) -> None:
            self.path = path

        def query(self, sql: str) -> pd.DataFrame:
            con = duckdb.connect(str(self.path), read_only=True)
            try:
                return con.execute(sql).fetchdf()
            finally:
                con.close()

        def scalar(self, sql: str):
            return self.query(sql).iloc[0, 0]

    return _ReadOnlyDB(duckdb_path)
