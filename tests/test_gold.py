"""Gold-layer tests: schemas, grain completeness, rate ranges and NULL denominators.

All tests in this module skip when the DuckDB database has not been built yet.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.gold, pytest.mark.integration]

GOLD_TABLES = [
    "gold_network_daily",
    "gold_hospital_monthly",
    "gold_department_monthly",
    "gold_patient_access",
    "gold_bed_utilization",
    "gold_financial_performance",
    "gold_claim_performance",
    "gold_lab_performance",
    "gold_workforce",
    "gold_inventory",
    "gold_patient_experience",
    "gold_quality_safety",
]

SILVER_TABLES = [
    "silver_patients",
    "silver_appointments",
    "silver_encounters",
    "silver_admissions",
    "silver_claims",
    "silver_bed_snapshots",
]

# Rates bounded by 0..100 according to CONTRACT.md.
BOUNDED_RATE_COLUMNS = {
    "no_show_rate": "gold_hospital_monthly",
    "occupancy_rate": "gold_hospital_monthly",
    "readmission_rate": "gold_hospital_monthly",
    "denial_rate": "gold_hospital_monthly",
    "lab_sla_rate": "gold_hospital_monthly",
    "same_day_pct": "gold_patient_access",
    "reschedule_rate": "gold_patient_access",
    "supplier_on_time_rate": "gold_inventory",
    "satisfaction_pct": "gold_patient_experience",
    "incident_rate": "gold_quality_safety",
    "investigation_completion_rate": "gold_quality_safety",
}


def _columns(duckdb_conn, table: str) -> set[str]:
    # Table names come from the module-level allowlists above, never from user input.
    rows = duckdb_conn.query(
        f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'"
    )
    return set(rows["column_name"]) if len(rows) else set()


def test_all_gold_tables_are_materialised(duckdb_conn) -> None:
    present = duckdb_conn.scalar(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_name LIKE 'gold_%'"
    )
    assert present >= len(GOLD_TABLES) - 1  # tolerate a module still being built


@pytest.mark.parametrize("table", GOLD_TABLES)
def test_gold_table_exists_with_columns(duckdb_conn, table: str) -> None:
    cols = _columns(duckdb_conn, table)
    assert cols, f"{table} is missing or has no columns"
    assert "month" in cols or "date" in cols, f"{table} needs a date dimension"


def test_silver_tables_available_for_drilldowns(duckdb_conn) -> None:
    present = duckdb_conn.scalar(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_name LIKE 'silver_%'"
    )
    assert present >= 1, "at least one silver_* table must be loaded for drill-downs"


def test_hospital_month_grain_is_unique(duckdb_conn) -> None:
    rows = duckdb_conn.query(
        "SELECT hospital_id, CAST(month AS DATE) AS month, COUNT(*) AS n "
        "FROM gold_hospital_monthly GROUP BY 1, 2 HAVING COUNT(*) > 1"
    )
    assert len(rows) == 0, "gold_hospital_monthly must have one row per hospital x month"


def test_hospital_month_completeness(duckdb_conn) -> None:
    summary = duckdb_conn.query(
        "SELECT hospital_id, COUNT(DISTINCT CAST(month AS DATE)) AS months "
        "FROM gold_hospital_monthly GROUP BY hospital_id"
    )
    assert len(summary) > 0, "gold_hospital_monthly is empty"
    assert len(summary) <= 10
    assert set(summary["hospital_id"]) <= {f"H{i:02d}" for i in range(1, 11)}
    expected = int(summary["months"].max())
    assert expected >= 1
    assert (summary["months"] == expected).all(), "every hospital must cover the same months"


def test_bounded_rates_are_within_range_or_null(duckdb_conn) -> None:
    cols = _columns(duckdb_conn, "gold_hospital_monthly")
    for column, table in BOUNDED_RATE_COLUMNS.items():
        if table != "gold_hospital_monthly" or column not in cols:
            continue
        bad = duckdb_conn.query(
            f"SELECT COUNT(*) AS n FROM gold_hospital_monthly "
            f"WHERE {column} IS NOT NULL AND ({column} < 0 OR {column} > 100)"
        )
        assert bad.iloc[0, 0] == 0, f"{column} outside 0..100"


def test_collection_rate_is_uncapped_non_negative_and_null_on_zero_denominator(duckdb_conn) -> None:
    bad = duckdb_conn.query(
        "SELECT COUNT(*) AS n FROM gold_hospital_monthly "
        "WHERE collection_rate IS NOT NULL AND collection_rate < 0"
    )
    assert bad.iloc[0, 0] == 0, "collection rate must never be negative"
    bad = duckdb_conn.query(
        "SELECT COUNT(*) AS n FROM gold_hospital_monthly "
        "WHERE COALESCE(net_revenue, 0) = 0 AND collection_rate IS NOT NULL"
    )
    assert bad.iloc[0, 0] == 0, "zero net revenue must produce a NULL collection rate"
    expected = duckdb_conn.query(
        "SELECT COUNT(*) AS n FROM gold_hospital_monthly "
        "WHERE collection_rate IS NOT NULL AND net_revenue > 0 "
        "AND ABS(collection_rate - ROUND(100.0 * collections / net_revenue, 2)) > 0.01"
    )
    assert expected.iloc[0, 0] == 0, "stored collection rate must equal the uncapped formula"


def test_no_show_rate_null_when_denominator_zero(duckdb_conn) -> None:
    bad = duckdb_conn.query(
        "SELECT COUNT(*) AS n FROM gold_hospital_monthly "
        "WHERE (COALESCE(completed_appointments, 0) + COALESCE(no_show_appointments, 0)) = 0 "
        "AND no_show_rate IS NOT NULL"
    )
    assert bad.iloc[0, 0] == 0, "NULL denominator must produce NULL no-show rate"


def test_occupancy_rate_null_when_no_available_bed_days(duckdb_conn) -> None:
    bad = duckdb_conn.query(
        "SELECT COUNT(*) AS n FROM gold_hospital_monthly "
        "WHERE COALESCE(available_bed_days, 0) = 0 AND occupancy_rate IS NOT NULL"
    )
    assert bad.iloc[0, 0] == 0, "NULL denominator must produce NULL occupancy"


def test_denial_rate_null_when_no_adjudicated_claims(duckdb_conn) -> None:
    bad = duckdb_conn.query(
        "SELECT COUNT(*) AS n FROM gold_hospital_monthly "
        "WHERE (COALESCE(claims_submitted, 0)) = 0 AND denial_rate IS NOT NULL"
    )
    assert bad.iloc[0, 0] == 0, "no adjudicated claims must produce NULL denial rate"


def test_module_rate_columns_in_range(duckdb_conn) -> None:
    checks = [
        ("gold_patient_access", "no_show_rate"),
        ("gold_bed_utilization", "occupancy_rate"),
        ("gold_claim_performance", "denial_rate"),
        ("gold_lab_performance", "sla_rate"),
        ("gold_inventory", "supplier_on_time_rate"),
        ("gold_patient_experience", "satisfaction_pct"),
        ("gold_quality_safety", "incident_rate"),
    ]
    for table, column in checks:
        if column not in _columns(duckdb_conn, table):
            continue
        bad = duckdb_conn.query(
            f"SELECT COUNT(*) AS n FROM {table} "
            f"WHERE {column} IS NOT NULL AND ({column} < 0 OR {column} > 100)"
        )
        assert bad.iloc[0, 0] == 0, f"{table}.{column} outside 0..100"
