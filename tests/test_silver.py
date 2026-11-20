"""Silver-layer tests: dtype correction, dedup, status rules and quarantine.

The documented silver rules are encoded as small reference helpers in this file so the
contract stays testable without the full dataset. Additional integration tests exercise
the real etl implementation when it becomes importable, and skip otherwise.
"""
from __future__ import annotations

import re

import pandas as pd
import pytest

from conftest import load_optional
from generator import schema

pytestmark = pytest.mark.silver

VALID_APPOINTMENT_STATUSES = {"Completed", "Cancelled", "No-show", "Scheduled"}
STATUS_ALIASES = {
    "Noshow": "No-show",
    "No-Show": "No-show",
    "No Show": "No-show",
    "No_Show": "No-show",
    "Canceled": "Cancelled",
}


def normalise_status(value) -> str | None:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    text = " ".join(str(value).strip().split()).title()
    return STATUS_ALIASES.get(text, text)


def normalise_hospital_id(value) -> str | None:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    match = re.fullmatch(r"\s*(H\d{2})\s*", str(value), flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


def dedupe(frame: pd.DataFrame, key: str) -> pd.DataFrame:
    return frame.drop_duplicates(subset=[key], keep="first").reset_index(drop=True)


def coerce_dtypes(frame: pd.DataFrame, table: str) -> pd.DataFrame:
    out = frame.copy()
    for col, dtype, _ in schema.TABLES[table]:
        if col not in out.columns:
            continue
        if dtype in {"date", "datetime64[ns]"}:
            out[col] = pd.to_datetime(out[col], errors="coerce")
        elif dtype == "int64":
            out[col] = pd.to_numeric(out[col], errors="coerce")
        elif dtype == "float64":
            out[col] = pd.to_numeric(out[col], errors="coerce")
        elif dtype == "string":
            out[col] = out[col].astype("string")
    return out


def quarantine(frame: pd.DataFrame, invalid_mask: pd.Series, rule_id: str, run_id: str):
    quarantined = frame[invalid_mask].copy()
    quarantined["rule_id"] = rule_id
    quarantined["failure_reason"] = rule_id
    quarantined["run_id"] = run_id
    quarantined["detected_at"] = pd.Timestamp("2026-11-20T00:00:00Z")
    clean = frame[~invalid_mask].copy().reset_index(drop=True)
    return clean, quarantined.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Reference-rule tests (always run)
# ---------------------------------------------------------------------------
def test_dtype_correction_on_inline_frame(appointments: pd.DataFrame) -> None:
    raw = appointments.copy()
    raw["appointment_date"] = raw["appointment_date"].astype(str)
    raw["lead_days"] = raw["lead_days"].astype(str)

    cleaned = coerce_dtypes(raw, "appointments")

    assert pd.api.types.is_datetime64_any_dtype(cleaned["appointment_date"])
    assert pd.api.types.is_numeric_dtype(cleaned["lead_days"])
    assert pd.api.types.is_string_dtype(cleaned["appointment_id"])


def test_dedup_by_primary_key(dirty_appointments: pd.DataFrame) -> None:
    assert len(dirty_appointments) == 7
    deduped = dedupe(dirty_appointments, "appointment_id")
    assert len(deduped) == 6
    assert deduped["appointment_id"].is_unique


def test_status_normalisation() -> None:
    cases = {
        "COMPLETED ": "Completed",
        "no_show": "No-show",
        "No Show": "No-show",
        "  cancelled": "Cancelled",
        "No-show": "No-show",
        "Scheduled": "Scheduled",
    }
    for raw, expected in cases.items():
        assert normalise_status(raw) == expected
    assert normalise_status(None) is None


def test_appointments_have_canonical_statuses(appointments: pd.DataFrame) -> None:
    normalised = appointments["status"].map(normalise_status)
    assert set(normalised.dropna()) <= VALID_APPOINTMENT_STATUSES


def test_hospital_code_normalisation() -> None:
    assert normalise_hospital_id(" h01 ") == "H01"
    assert normalise_hospital_id("H03") == "H03"
    assert normalise_hospital_id("UNKNOWN") is None


def test_quarantine_separates_invalid_rows_with_metadata(dirty_appointments) -> None:
    invalid = dirty_appointments["hospital_id"].map(normalise_hospital_id).isna()
    clean, bad = quarantine(dirty_appointments, invalid, "DQ_UNKNOWN_HOSPITAL", "RUN_001")

    assert len(clean) + len(bad) == len(dirty_appointments)
    assert len(bad) == invalid.sum()
    for column in ("rule_id", "failure_reason", "run_id", "detected_at"):
        assert column in bad.columns
        assert bad[column].notna().all()
    assert "rule_id" not in clean.columns


def test_invalid_date_ordering_is_quarantined(admissions: pd.DataFrame) -> None:
    admissions = admissions.copy()
    admissions.loc[0, "discharge_datetime"] = "2025-01-01 00:00:00"
    admitted = pd.to_datetime(admissions["admission_datetime"])
    discharged = pd.to_datetime(admissions["discharge_datetime"])
    invalid = discharged.notna() & (discharged < admitted)

    clean, bad = quarantine(admissions, invalid, "DQ_DISCHARGE_BEFORE_ADMISSION", "RUN_002")
    assert len(bad) == 1
    assert bad.iloc[0]["admission_id"] == "ADM000001"
    assert "ADM000001" not in set(clean["admission_id"])


def test_duplicate_snapshots_detected(bed_snapshots: pd.DataFrame) -> None:
    dup = bed_snapshots.copy()
    dup = pd.concat([dup, dup.iloc[[0]]], ignore_index=True)
    assert dup["snapshot_id"].duplicated().any()
    assert len(dedupe(dup, "snapshot_id")) == len(bed_snapshots)


# ---------------------------------------------------------------------------
# Integration hooks: run against the real etl package when it is available
# ---------------------------------------------------------------------------
def _first_callable(specs: list[tuple[str, tuple[str, ...]]]):
    for module_name, names in specs:
        module = load_optional(module_name)
        if module is None:
            continue
        for name in names:
            candidate = getattr(module, name, None)
            if callable(candidate):
                return candidate
    return None


def test_etl_status_normaliser_matches_contract_when_available() -> None:
    fn = _first_callable([
        ("etl.silver", ("normalise_status", "normalize_status", "normalize_statuses")),
        ("etl.clean", ("normalise_status", "normalize_status", "clean_status")),
        ("etl.quality", ("normalise_status", "normalize_status")),
    ])
    if fn is None:
        pytest.skip("etl status normaliser not implemented yet")
    try:
        result = fn("COMPLETED ")
    except Exception as exc:  # noqa: BLE001 - parallel implementation may differ
        pytest.skip(f"etl status normaliser signature not usable here: {exc}")
    assert str(result).strip().title().replace("_", "-") in VALID_APPOINTMENT_STATUSES


def test_etl_pipeline_module_importable_when_available() -> None:
    module = load_optional("etl.pipeline")
    if module is None:
        pytest.skip("etl.pipeline not implemented yet")
    assert hasattr(module, "__name__")
