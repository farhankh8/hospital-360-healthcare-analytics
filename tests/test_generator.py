"""Generator tests: seed, identifiers, relationships, profiles and targets."""
from __future__ import annotations

import json
import os
from datetime import date

import pandas as pd
import pytest

from generator import config, schema

pytestmark = pytest.mark.generator


def test_seed_is_fixed_and_reproducible() -> None:
    expected = int(os.getenv("H360_SEED", "42"))
    assert config.SEED == expected
    assert isinstance(config.SEED, int)


def test_generator_version_is_declared() -> None:
    assert config.GENERATOR_VERSION
    assert isinstance(config.GENERATOR_VERSION, str)


@pytest.mark.parametrize(
    ("table", "key"),
    [
        ("patients", "patient_id"),
        ("appointments", "appointment_id"),
        ("encounters", "encounter_id"),
        ("admissions", "admission_id"),
        ("claims", "claim_id"),
        ("bed_snapshots", "snapshot_id"),
    ],
)
def test_sample_primary_keys_are_unique(samples, table: str, key: str) -> None:
    frame = getattr(samples, table)
    assert key in frame.columns
    assert frame[key].notna().all(), f"{table}.{key} contains nulls"
    assert frame[key].is_unique, f"{table}.{key} contains duplicates"


def test_foreign_keys_resolve_in_inline_samples(samples) -> None:
    patient_ids = set(samples.patients["patient_id"])
    appointment_ids = set(samples.appointments["appointment_id"])
    encounter_ids = set(samples.encounters["encounter_id"])
    hospital_ids = {h[0] for h in config.HOSPITALS}

    assert set(samples.appointments["patient_id"]) <= patient_ids
    assert set(samples.appointments["hospital_id"]) <= hospital_ids
    assert set(samples.encounters["patient_id"]) <= patient_ids
    assert set(samples.encounters["hospital_id"]) <= hospital_ids
    linked = samples.encounters["appointment_id"].dropna()
    assert set(linked) <= appointment_ids
    assert set(samples.admissions["encounter_id"]) <= encounter_ids
    assert set(samples.admissions["patient_id"]) <= patient_ids
    assert set(samples.claims["hospital_id"]) <= hospital_ids


def test_hospital_profiles_vary() -> None:
    hospitals = config.HOSPITALS
    assert len(hospitals) == 10
    ids = [h[0] for h in hospitals]
    assert len(set(ids)) == 10
    profiles = {h[0]: h[3] for h in hospitals}
    assert profiles["H03"] == "Cardiology"
    assert profiles["H04"] == "Pediatrics"
    assert profiles["H09"] == "Emergency"
    assert profiles["H01"] == "Multispecialty"
    assert len(set(profiles.values())) > 1, "profiles must not be identical"
    assert config.TOTAL_BEDS == sum(h[4] for h in hospitals) == 3450
    assert max(hospitals, key=lambda h: h[4])[0] == "H01"


def test_reporting_window_is_24_months() -> None:
    assert config.START_DATE == date(2025, 1, 1)
    assert config.END_DATE == date(2026, 12, 31)
    assert config.START_DATE < config.END_DATE
    months = (
        (config.END_DATE.year - config.START_DATE.year) * 12
        + config.END_DATE.month
        - config.START_DATE.month
        + 1
    )
    assert months == 24


def test_inline_date_ordering_is_valid(samples) -> None:
    apt = samples.appointments
    assert (apt["booking_date"] <= apt["appointment_date"]).all()

    enc = samples.encounters
    assert (enc["arrival_datetime"] <= enc["triage_datetime"]).all()
    assert (enc["triage_datetime"] <= enc["provider_datetime"]).all()
    assert (enc["provider_datetime"] <= enc["disposition_datetime"]).all()

    adm = samples.admissions
    discharged = adm[adm["discharge_datetime"].notna()]
    assert (discharged["admission_datetime"] <= discharged["discharge_datetime"]).all()
    assert (discharged["los_days"] > 0).all()

    claims = samples.claims
    assert claims["claim_amount"].ge(0).all()


def test_target_counts_match_blueprint_thresholds() -> None:
    targets = config.TARGETS
    assert targets["hospitals"] == 10
    assert targets["patients"] >= 15_000
    assert targets["appointments"] >= 100_000
    assert targets["encounters"] >= 80_000
    assert targets["admissions"] >= 20_000
    assert targets["bed_snapshots"] >= 100_000
    assert targets["lab_orders"] >= 100_000
    assert targets["lab_results"] >= 150_000
    assert sum(targets.values()) >= 500_000


def test_controlled_dq_issues_are_configured() -> None:
    issues = config.DQ_INJECTION
    expected = {
        "duplicate_patients", "missing_payer", "invalid_dates", "unknown_department",
        "invalid_status", "incorrect_hospital_id", "negative_amounts",
        "orphaned_references",
    }
    assert expected <= set(issues)
    assert all(count > 0 for count in issues.values())


def test_schema_defined_for_all_layer_tables() -> None:
    assert len(schema.DIMENSION_TABLES) == 18
    assert len(schema.FACT_TABLES) == 23
    assert len(schema.TABLES) == 41
    assert "dim_patient" in schema.DIMENSION_TABLES
    assert "dim_location" in schema.DIMENSION_TABLES
    assert "patient_id" in schema.columns("patients")
    assert schema.dtypes("patients")["patient_id"] == "string"
    assert schema.BRONZE_TABLES == list(schema.TABLES)


def test_manifest_reports_actual_counts_if_present(data_dir) -> None:
    manifest_dir = data_dir / "manifests"
    manifests = sorted(
        list(manifest_dir.glob("manifest_*.json"))
        + list(manifest_dir.glob("pipeline_*.json"))
        + list(manifest_dir.glob("generator_manifest.json"))
    )
    if not manifests:
        pytest.skip("no pipeline manifest generated yet")
    payload = json.loads(manifests[-1].read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert payload, "manifest must not be empty"
    if "patients" in payload:
        assert payload["patients"] >= 0
    if "total_records" in payload:
        assert payload["total_records"] >= 0


def _bronze(table: str) -> pd.DataFrame:
    path = config.BRONZE_DIR / table / f"{table}.csv"
    if not path.exists():
        pytest.skip(f"bronze data not generated: {table}")
    return pd.read_csv(path, low_memory=False)


def test_phase1_dimensions_are_generated() -> None:
    dim_patient = _bronze("dim_patient")
    patients = _bronze("patients")
    dim_location = _bronze("dim_location")
    dim_hospital = _bronze("dim_hospital")

    assert dim_patient["patient_id"].is_unique
    assert set(dim_patient["patient_id"]) == set(patients["patient_id"].dropna())
    assert "age_group" in dim_patient.columns
    assert dim_location["location_id"].is_unique
    assert set(dim_location["hospital_id"]) <= set(dim_hospital["hospital_id"])


def test_phase1_event_dates_respect_reporting_window() -> None:
    historical = {"birth_date", "registration_date"}
    for table, cols in schema.DATE_COLUMNS.items():
        if not (config.BRONZE_DIR / table / f"{table}.csv").exists():
            continue
        frame = _bronze(table)
        for col in cols:
            if col in historical:
                continue
            parsed = pd.to_datetime(frame[col], errors="coerce")
            latest = parsed.max()
            if pd.isna(latest):
                continue
            assert latest <= pd.Timestamp(config.END_DATE) + pd.Timedelta(days=1), (
                f"{table}.{col}: {latest} outside reporting window"
            )


def test_phase1_every_encounter_has_a_resolvable_appointment() -> None:
    encounters = _bronze("encounters")
    appointments = _bronze("appointments")
    assert encounters["appointment_id"].notna().all()
    assert set(encounters["appointment_id"]) <= set(appointments["appointment_id"])


def test_phase1_manifest_quarantine_counts_reconcile() -> None:
    manifests = sorted(config.MANIFEST_DIR.glob("pipeline_*.json"))
    phase1_manifests = []
    for path in manifests:
        candidate = json.loads(path.read_text(encoding="utf-8"))
        if "quarantined_rows" in candidate.get("totals", {}):
            phase1_manifests.append((path, candidate))
    if not phase1_manifests:
        pytest.skip("no Phase 1 pipeline manifest generated yet")
    payload = phase1_manifests[-1][1]
    totals = payload["totals"]
    quarantine = payload["quarantine"]
    quality_summary = payload["quality"]["summary"]
    assert quarantine["rows"] == totals["quarantined_rows"]
    assert quarantine["records"] == quarantine["rule_failure_records"]
    assert quarantine["records"] == totals["quarantine_rule_failures"]
    assert quality_summary["quarantine_rule_failures"] == quarantine["records"]
    assert quality_summary["quarantined_rows"] == quarantine["rows"]
