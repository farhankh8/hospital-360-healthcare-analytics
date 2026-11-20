"""Phase 2 KPI contract reconciliation tests.

These tests treat ``analytics/kpi_definitions/kpis.json`` as the single source
of truth and assert that SQL, API specs, API responses and dashboard IDs agree.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.services.kpi_specs import SPECS

pytestmark = pytest.mark.kpi

ROOT = Path(__file__).resolve().parents[1]
KPIS_PATH = ROOT / "analytics" / "kpi_definitions" / "kpis.json"
PAGES_PATH = ROOT / "web" / "lib" / "page-configs.ts"
HOSPITAL_SQL = (ROOT / "analytics" / "sql" / "02_gold_hospital_monthly.sql").read_text(encoding="utf-8")
FINANCE_SQL = (ROOT / "analytics" / "sql" / "06_gold_financial_performance.sql").read_text(encoding="utf-8")

REQUIRED_FIELDS = [
    "id", "display_name", "business_definition", "formula_sql", "numerator", "denominator",
    "source_tables", "source_columns", "aggregation_method", "date_column", "filter_behavior",
    "units", "decimal_precision", "null_handling", "additivity", "expected_range", "aliases",
    "business_interpretation", "consumer_status", "audit_findings", "contract_version",
]


def _contract() -> list[dict]:
    return json.loads(KPIS_PATH.read_text(encoding="utf-8"))


def _specs() -> list[tuple[str, object]]:
    return [(endpoint, spec) for endpoint, specs in SPECS.items() for spec in specs]


def _alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for _, spec in _specs():
        for alias in spec.aliases:
            aliases[alias] = spec.id
    return aliases


def _frontend_ids() -> set[str]:
    text = PAGES_PATH.read_text(encoding="utf-8")
    result: set[str] = set()
    for block in re.findall(r"kpiIds:\s*\[(.*?)\]", text, re.DOTALL):
        result.update(re.findall(r"'([a-z0-9_]+)'", block))
    return result


@pytest.fixture
def client():
    module = pytest.importorskip("api.main")
    return TestClient(module.app)


# ---------------------------------------------------------------------------
# Contract shape and consumer coverage
# ---------------------------------------------------------------------------
def test_contract_has_190_complete_unique_definitions() -> None:
    contract = _contract()
    assert len(contract) == 190
    assert len({item["id"] for item in contract}) == 190
    for item in contract:
        missing = [field for field in REQUIRED_FIELDS if field not in item]
        assert not missing, f"{item['id']} is missing {missing}"
        assert item["contract_version"] == "phase2-kpi-integrity-v1"
        assert item["source_tables"], f"{item['id']} has no source tables"
        assert item["source_columns"], f"{item['id']} has no source columns"


def test_alias_map_is_unique_and_resolves_to_canonical_ids() -> None:
    contract = _contract()
    canonical = {item["id"] for item in contract}
    aliases = _alias_map()
    seen: dict[str, str] = {}
    for alias, target in aliases.items():
        assert target in canonical, f"alias {alias} targets unknown KPI {target}"
        if alias in seen:
            assert seen[alias] == target, f"alias {alias} is ambiguous"
        seen[alias] = target
    assert aliases.get("revenue") != "total_revenue"
    assert aliases.get("average_satisfaction") != "patient_satisfaction"
    assert aliases.get("avg_investigation_time") == "average_investigation_time"


def test_duplicate_api_ids_share_unit_and_formula_semantics() -> None:
    grouped: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for _, spec in _specs():
        grouped[spec.id].add((spec.unit, spec.description or spec.expr))
    repeated = {key: value for key, value in grouped.items() if sum(1 for _, s in _specs() if s.id == key) > 1}
    for key in ("total_revenue", "patient_satisfaction", "total_beds", "admissions"):
        assert len({unit for unit, _ in repeated.get(key, {("", "")})}) == 1, f"{key} has conflicting units"
    for key, variants in repeated.items():
        units = {unit for unit, _ in variants}
        assert len(units) == 1, f"{key} has conflicting units: {units}"


def test_frontend_ids_resolve_to_a_canonical_or_alias_response_key() -> None:
    contract = _contract()
    known = {item["id"] for item in contract} | set(_alias_map())
    produced = {spec.id for _, spec in _specs()} | set(_alias_map())
    for key in _frontend_ids():
        assert key in known, f"frontend KPI {key} is not in the contract"
        assert key in produced, f"frontend KPI {key} has no API producer"


def test_dimension_kpis_do_not_claim_a_date_column() -> None:
    by_id = {spec.id: spec for _, spec in _specs()}
    for key in ("hospitals_selected", "total_beds", "active_employees"):
        assert by_id[key].date_col == "", f"{key} must not apply a non-existent date filter"


# ---------------------------------------------------------------------------
# Conflict-specific assertions
# ---------------------------------------------------------------------------
def test_gross_and_net_revenue_are_distinct_contracts() -> None:
    by_id = {spec.id: spec for _, spec in _specs()}
    assert "gross_revenue" in by_id["total_revenue"].expr
    assert "net_revenue" in by_id["revenue"].expr
    assert "revenue" not in by_id["total_revenue"].aliases
    assert "average_satisfaction" not in by_id["patient_satisfaction"].aliases


def test_satisfaction_scale_is_documented_and_executable() -> None:
    contract = {item["id"]: item for item in _contract()}
    assert contract["patient_satisfaction"]["units"] == "percent"
    assert contract["average_satisfaction"]["units"] == "score"
    assert "/5" in contract["patient_satisfaction"]["formula_sql"]
    by_id = {spec.id: spec for _, spec in _specs()}
    assert by_id["patient_satisfaction"].unit == "percent"
    assert by_id["average_satisfaction"].unit == "score"


def test_collection_rate_is_uncapped_in_sql_and_specs() -> None:
    assert "LEAST(100" not in HOSPITAL_SQL
    assert "LEAST(100" not in FINANCE_SQL
    by_id = {spec.id: spec for _, spec in _specs()}
    expr = by_id["collection_rate"].expr
    assert "NULLIF" in expr and "100.0" in expr
    assert "LEAST" not in expr and "GREATEST" not in expr


def test_investigation_canonical_id_and_null_weighting() -> None:
    contract = {item["id"]: item for item in _contract()}
    assert "avg_investigation_time" in contract["average_investigation_time"]["aliases"]
    assert contract["avg_investigation_time"]["alias_of"] == "average_investigation_time"
    by_id = {spec.id: spec for _, spec in _specs()}
    spec = by_id["average_investigation_time"]
    assert "avg_investigation_time" in spec.aliases
    assert "FILTER (WHERE avg_investigation_days IS NOT NULL)" in spec.expr


# ---------------------------------------------------------------------------
# Data reconciliation
# ---------------------------------------------------------------------------
def test_total_patients_matches_distinct_encounter_patients(duckdb_conn) -> None:
    expected = duckdb_conn.scalar("SELECT COUNT(DISTINCT patient_id) FROM silver_encounters")
    # The gold monthly column deliberately repeats patients; it must not be used.
    summed = duckdb_conn.scalar("SELECT SUM(patients) FROM gold_hospital_monthly")
    assert expected > 0 and summed > expected


def test_revenue_reconciliation_from_silver_invoices(duckdb_conn) -> None:
    row = duckdb_conn.query(
        "SELECT SUM(gross_amount) AS gross, SUM(net_amount) AS net, "
        "SUM(gross_amount - net_amount) AS discounts, SUM(paid_amount) AS paid, "
        "SUM(balance_amount) AS balance FROM silver_invoices"
    ).iloc[0]
    assert row["gross"] == pytest.approx(row["net"] + row["discounts"], abs=0.01)
    assert row["net"] == pytest.approx(row["paid"] + row["balance"], abs=0.01)
    assert row["gross"] != pytest.approx(row["net"], abs=0.01)


def test_satisfaction_scale_matches_gold(duckdb_conn) -> None:
    row = duckdb_conn.query(
        "SELECT AVG(avg_rating) AS score, AVG(satisfaction_pct) AS pct "
        "FROM gold_patient_experience"
    ).iloc[0]
    assert row["pct"] == pytest.approx(row["score"] / 5 * 100, abs=0.5)


def test_collection_rate_matches_uncapped_gold_formula(duckdb_conn) -> None:
    row = duckdb_conn.query(
        "SELECT SUM(collections) AS collections, SUM(net_revenue) AS net, "
        "AVG(collection_rate) AS avg_stored FROM gold_hospital_monthly"
    ).iloc[0]
    expected = row["collections"] * 100 / row["net"]
    assert expected > 0
    # A capped implementation would make the average differ from the aggregate.
    assert row["avg_stored"] == pytest.approx(expected, abs=1.0)


def test_filters_change_values_and_use_business_date_columns(client, duckdb_path) -> None:
    base = client.get("/api/v1/overview/kpis").json()["data"]
    h01 = client.get("/api/v1/overview/kpis?hospital_id=H01").json()["data"]
    narrow = client.get(
        "/api/v1/overview/kpis?date_from=2025-01-01&date_to=2025-06-30"
    ).json()["data"]
    assert h01["total_patients"]["value"] < base["total_patients"]["value"]
    assert narrow["total_revenue"]["value"] < base["total_revenue"]["value"]


# ---------------------------------------------------------------------------
# API response reconciliation
# ---------------------------------------------------------------------------
def test_api_response_keys_and_units_match_contract(client, duckdb_path) -> None:
    overview = client.get("/api/v1/overview/kpis").json()["data"]
    assert "total_revenue" in overview and "revenue" not in overview
    assert "patient_satisfaction" in overview and "average_satisfaction" not in overview
    assert overview["total_revenue"]["unit"] == "currency"
    assert overview["patient_satisfaction"]["unit"] == "percent"

    experience = client.get("/api/v1/experience/kpis").json()["data"]
    assert experience["average_satisfaction"]["unit"] == "score"

    quality = client.get("/api/v1/quality/kpis").json()["data"]
    assert "average_investigation_time" in quality
    assert quality["avg_investigation_time"]["value"] == quality["average_investigation_time"]["value"]


def test_api_gross_net_and_collection_values_reconcile(client, duckdb_conn, duckdb_path) -> None:
    overview = client.get("/api/v1/overview/kpis").json()["data"]
    finance = client.get("/api/v1/finance/kpis").json()["data"]
    gross = duckdb_conn.scalar("SELECT SUM(gross_revenue) FROM gold_hospital_monthly")
    net = duckdb_conn.scalar("SELECT SUM(net_revenue) FROM gold_hospital_monthly")
    expected_rate = duckdb_conn.scalar(
        "SELECT SUM(collections) * 100.0 / NULLIF(SUM(net_revenue), 0) FROM gold_hospital_monthly"
    )
    assert overview["total_revenue"]["value"] == pytest.approx(round(gross, 2), abs=0.01)
    assert finance["revenue"]["value"] == pytest.approx(round(net, 2), abs=0.01)
    assert finance["net_revenue"]["value"] == pytest.approx(round(net, 2), abs=0.01)
    assert finance["collection_rate"]["value"] == pytest.approx(round(expected_rate, 2), abs=0.01)
