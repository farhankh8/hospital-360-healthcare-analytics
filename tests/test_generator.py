"""Generator tests: seed, identifiers, relationships, profiles and targets."""
from __future__ import annotations

import json
import os
from datetime import date

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
    assert len(schema.DIMENSION_TABLES) == 16
    assert len(schema.FACT_TABLES) == 23
    assert len(schema.TABLES) == 39
    assert "patient_id" in schema.columns("patients")
    assert schema.dtypes("patients")["patient_id"] == "string"
    assert schema.BRONZE_TABLES == list(schema.TABLES)


def test_manifest_reports_actual_counts_if_present(data_dir) -> None:
    manifests = sorted((data_dir / "manifests").glob("manifest_*.json"))
    if not manifests:
        pytest.skip("no pipeline manifest generated yet")
    payload = json.loads(manifests[-1].read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert payload, "manifest must not be empty"
    if "patients" in payload:
        assert payload["patients"] >= 0
    if "total_records" in payload:
        assert payload["total_records"] >= 0
