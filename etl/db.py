"""DuckDB access helpers for HOSPITAL 360.

The analytical database is the single store consumed by the API.  This module
owns every schema-level detail (table names, type casts and spines) so that the
API can simply query ``silver_*``, ``gold_*``, ``dq_*`` and pipeline tables.

Public helpers
--------------
connect()                 -> duckdb connection to ``config.DUCKDB_PATH``
load_all(con=None)        -> (re)create every table/view from the parquet files
query(sql, params, con)   -> run SQL and return a pandas DataFrame

All paths are resolved from ``generator.config`` at call time (never captured
at import time) which makes the pipeline easy to point at a temporary fixture
directory during smoke tests.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import duckdb
import pandas as pd

from generator import config, schema

# ---------------------------------------------------------------------------
# Gold contract: (column, duckdb type) in exactly the order from CONTRACT.md
# ---------------------------------------------------------------------------
GOLD_TYPES: dict[str, list[tuple[str, str]]] = {
    "gold_network_daily": [
        ("date", "DATE"), ("encounters", "INTEGER"), ("admissions", "INTEGER"),
        ("appointments", "INTEGER"), ("completed_appointments", "INTEGER"),
        ("no_show_appointments", "INTEGER"), ("revenue", "DOUBLE"),
        ("collections", "DOUBLE"), ("occupied_beds", "INTEGER"),
        ("available_beds", "INTEGER"), ("avg_wait_minutes", "DOUBLE"),
    ],
    "gold_hospital_monthly": [
        ("hospital_id", "VARCHAR"), ("hospital_name", "VARCHAR"), ("month", "DATE"),
        ("patients", "INTEGER"), ("encounters", "INTEGER"), ("admissions", "INTEGER"),
        ("discharges", "INTEGER"), ("appointments", "INTEGER"),
        ("completed_appointments", "INTEGER"), ("cancelled_appointments", "INTEGER"),
        ("no_show_appointments", "INTEGER"), ("no_show_rate", "DOUBLE"),
        ("avg_wait_minutes", "DOUBLE"), ("occupied_bed_days", "DOUBLE"),
        ("available_bed_days", "DOUBLE"), ("occupancy_rate", "DOUBLE"),
        ("avg_los_days", "DOUBLE"), ("readmissions", "INTEGER"),
        ("readmission_rate", "DOUBLE"), ("gross_revenue", "DOUBLE"),
        ("net_revenue", "DOUBLE"), ("collections", "DOUBLE"),
        ("outstanding_balance", "DOUBLE"), ("collection_rate", "DOUBLE"),
        ("lab_orders", "INTEGER"), ("completed_lab_tests", "INTEGER"),
        ("avg_lab_tat_minutes", "DOUBLE"), ("lab_sla_rate", "DOUBLE"),
        ("claims_submitted", "INTEGER"), ("claims_denied", "INTEGER"),
        ("denial_rate", "DOUBLE"), ("feedback_count", "INTEGER"),
        ("avg_satisfaction", "DOUBLE"), ("complaint_count", "INTEGER"),
        ("incidents_count", "INTEGER"), ("scheduled_hours", "DOUBLE"),
        ("worked_hours", "DOUBLE"), ("overtime_hours", "DOUBLE"),
        ("stockouts", "INTEGER"), ("inventory_value", "DOUBLE"),
    ],
    "gold_department_monthly": [
        ("hospital_id", "VARCHAR"), ("department_id", "VARCHAR"),
        ("department_name", "VARCHAR"), ("specialty_id", "VARCHAR"),
        ("specialty_name", "VARCHAR"), ("month", "DATE"),
        ("patients", "INTEGER"), ("encounters", "INTEGER"),
        ("admissions", "INTEGER"), ("appointments", "INTEGER"),
        ("no_show_rate", "DOUBLE"), ("avg_wait_minutes", "DOUBLE"),
        ("occupancy_rate", "DOUBLE"), ("avg_los_days", "DOUBLE"),
        ("revenue", "DOUBLE"), ("lab_orders", "INTEGER"),
        ("avg_lab_tat_minutes", "DOUBLE"), ("denial_rate", "DOUBLE"),
        ("avg_satisfaction", "DOUBLE"), ("incidents_count", "INTEGER"),
    ],
    "gold_patient_access": [
        ("hospital_id", "VARCHAR"), ("department_id", "VARCHAR"), ("month", "DATE"),
        ("scheduled", "INTEGER"), ("completed", "INTEGER"), ("cancelled", "INTEGER"),
        ("no_shows", "INTEGER"), ("no_show_rate", "DOUBLE"),
        ("avg_wait_minutes", "DOUBLE"), ("avg_lead_days", "DOUBLE"),
        ("same_day_pct", "DOUBLE"), ("reschedule_rate", "DOUBLE"),
    ],
    "gold_bed_utilization": [
        ("hospital_id", "VARCHAR"), ("ward", "VARCHAR"), ("month", "DATE"),
        ("total_beds", "INTEGER"), ("occupied_bed_days", "DOUBLE"),
        ("available_bed_days", "DOUBLE"), ("blocked_bed_days", "DOUBLE"),
        ("occupancy_rate", "DOUBLE"), ("avg_los_days", "DOUBLE"),
        ("bed_turnover", "DOUBLE"), ("avg_boarding_hours", "DOUBLE"),
    ],
    "gold_financial_performance": [
        ("hospital_id", "VARCHAR"), ("department_id", "VARCHAR"), ("month", "DATE"),
        ("gross_revenue", "DOUBLE"), ("net_revenue", "DOUBLE"),
        ("collections", "DOUBLE"), ("outstanding_balance", "DOUBLE"),
        ("collection_rate", "DOUBLE"), ("avg_invoice_value", "DOUBLE"),
        ("refunds", "DOUBLE"), ("writeoffs", "DOUBLE"),
        ("revenue_growth_pct", "DOUBLE"),
    ],
    "gold_claim_performance": [
        ("hospital_id", "VARCHAR"), ("payer_id", "VARCHAR"), ("payer_name", "VARCHAR"),
        ("month", "DATE"), ("claims", "INTEGER"), ("approved", "INTEGER"),
        ("denied", "INTEGER"), ("denial_rate", "DOUBLE"),
        ("claimed_amount", "DOUBLE"), ("approved_amount", "DOUBLE"),
        ("paid_amount", "DOUBLE"), ("avg_processing_days", "DOUBLE"),
        ("appeals", "INTEGER"), ("appeal_success_rate", "DOUBLE"),
    ],
    "gold_lab_performance": [
        ("hospital_id", "VARCHAR"), ("test_code", "VARCHAR"), ("test_name", "VARCHAR"),
        ("month", "DATE"), ("orders", "INTEGER"), ("completed", "INTEGER"),
        ("pending", "INTEGER"), ("cancelled", "INTEGER"),
        ("avg_tat_minutes", "DOUBLE"), ("median_tat_minutes", "DOUBLE"),
        ("sla_rate", "DOUBLE"), ("delayed", "INTEGER"), ("critical", "INTEGER"),
    ],
    "gold_workforce": [
        ("hospital_id", "VARCHAR"), ("department_id", "VARCHAR"), ("month", "DATE"),
        ("headcount", "INTEGER"), ("scheduled_hours", "DOUBLE"),
        ("worked_hours", "DOUBLE"), ("overtime_hours", "DOUBLE"),
        ("absence_rate", "DOUBLE"), ("coverage_pct", "DOUBLE"),
        ("workforce_cost", "DOUBLE"),
    ],
    "gold_inventory": [
        ("hospital_id", "VARCHAR"), ("category", "VARCHAR"), ("month", "DATE"),
        ("inventory_value", "DOUBLE"), ("stockouts", "INTEGER"),
        ("low_stock", "INTEGER"), ("expired_value", "DOUBLE"),
        ("waste", "DOUBLE"), ("turnover", "DOUBLE"),
        ("purchase_orders", "INTEGER"), ("procurement_value", "DOUBLE"),
        ("supplier_on_time_rate", "DOUBLE"),
    ],
    "gold_patient_experience": [
        ("hospital_id", "VARCHAR"), ("department_id", "VARCHAR"), ("month", "DATE"),
        ("feedback_count", "INTEGER"), ("avg_rating", "DOUBLE"),
        ("satisfaction_pct", "DOUBLE"), ("promoters", "INTEGER"),
        ("detractors", "INTEGER"), ("nps", "DOUBLE"), ("complaints", "INTEGER"),
        ("complaint_resolution_days", "DOUBLE"),
    ],
    "gold_quality_safety": [
        ("hospital_id", "VARCHAR"), ("department_id", "VARCHAR"), ("month", "DATE"),
        ("incidents", "INTEGER"), ("incident_rate", "DOUBLE"), ("falls", "INTEGER"),
        ("medication_incidents", "INTEGER"), ("infection_incidents", "INTEGER"),
        ("critical_incidents", "INTEGER"),
        ("investigation_completion_rate", "DOUBLE"),
        ("avg_investigation_days", "DOUBLE"), ("readmission_rate", "DOUBLE"),
    ],
}

DQ_RULE_TYPES: list[tuple[str, str]] = [
    ("rule_id", "VARCHAR"), ("rule_name", "VARCHAR"), ("category", "VARCHAR"),
    ("table_name", "VARCHAR"), ("passed", "BOOLEAN"), ("failed_count", "BIGINT"),
    ("severity", "VARCHAR"), ("description", "VARCHAR"),
    ("checked_count", "BIGINT"), ("checked_at", "TIMESTAMP"),
    ("pipeline_run_id", "VARCHAR"),
]

DQ_FAILURE_TYPES: list[tuple[str, str]] = [
    ("failure_id", "VARCHAR"), ("rule_id", "VARCHAR"), ("table_name", "VARCHAR"),
    ("record_id", "VARCHAR"), ("failure_reason", "VARCHAR"), ("severity", "VARCHAR"),
    ("detected_at", "TIMESTAMP"), ("pipeline_run_id", "VARCHAR"),
    ("source_file", "VARCHAR"), ("record_json", "VARCHAR"),
]

PIPELINE_RUN_TYPES: list[tuple[str, str]] = [
    ("run_id", "VARCHAR"), ("start_time", "TIMESTAMP"), ("end_time", "TIMESTAMP"),
    ("duration_seconds", "DOUBLE"), ("status", "VARCHAR"),
    ("source_records", "BIGINT"), ("valid_records", "BIGINT"),
    ("quarantined_records", "BIGINT"), ("tables_created", "BIGINT"),
    ("error_message", "VARCHAR"),
]

LINEAGE_TYPES: list[tuple[str, str]] = [
    ("target_table", "VARCHAR"), ("layer", "VARCHAR"),
    ("source_tables", "VARCHAR"), ("transformations", "VARCHAR"),
]


# ---------------------------------------------------------------------------
# Connection / low-level helpers
# ---------------------------------------------------------------------------
def connect(path: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    """Open (or create) the analytical database at ``config.DUCKDB_PATH``."""
    target = Path(path) if path is not None else Path(config.DUCKDB_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(target))
    # UTF-8 and a generous memory budget keep the 100k-row facts comfortable.
    con.execute("SET memory_limit='2GB'")
    con.execute("SET threads=4")
    return con


def _parquet_path(directory: Path, name: str) -> Path:
    return Path(directory) / f"{name}.parquet"


def _create_typed_table(
    con: duckdb.DuckDBPyConnection,
    table: str,
    parquet: Path,
    columns: Iterable[tuple[str, str]],
) -> None:
    """Materialise ``parquet`` as ``table`` applying the contract type casts."""
    cols = list(columns)
    if not cols:
        raise ValueError(f"No column contract supplied for {table}")
    select = ",\n    ".join(
        f'CAST("{name}" AS {dtype}) AS "{name}"' for name, dtype in cols
    )
    safe_path = str(parquet).replace("'", "''").replace("\\", "/")
    con.execute(
        f"CREATE OR REPLACE TABLE {table} AS\nSELECT {select}\n"
        f"FROM read_parquet('{safe_path}')"
    )


def query(
    sql: str,
    params: Any = None,
    con: duckdb.DuckDBPyConnection | None = None,
) -> pd.DataFrame:
    """Execute ``sql`` and return a DataFrame.  ``params`` may be a tuple/list
    for ``?`` placeholders or a dict for named placeholders (DuckDB supports
    ``$name`` parameters via named params)."""
    own = con is None
    conn = con or connect()
    try:
        result = conn.execute(sql, params or [])
        try:
            return result.df()
        except Exception:
            return pd.DataFrame(result.fetchall(), columns=[c[0] for c in result.description])
    finally:
        if own:
            conn.close()


# ---------------------------------------------------------------------------
# Spines: guaranteed hospital and month grids for continuous charts
# ---------------------------------------------------------------------------
def ensure_spines(con: duckdb.DuckDBPyConnection) -> None:
    """Guarantee the 10 canonical hospitals and 24 months exist in DuckDB.

    The generator is the normal source of ``silver_dim_hospital``.  The
    constants in ``generator.config`` are the canonical network, so any missing
    hospital is inserted from there rather than fabricating new identifiers.
    """
    has_hospital = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_name='silver_dim_hospital'"
    ).fetchone()[0] > 0

    if not has_hospital:
        con.execute(
            "CREATE TABLE silver_dim_hospital ("
            "hospital_id VARCHAR, hospital_name VARCHAR, city VARCHAR, "
            "profile VARCHAR, hospital_type VARCHAR, beds BIGINT, "
            "status VARCHAR, latitude DOUBLE, longitude DOUBLE)"
        )
    for hid, name, city, profile, beds in config.HOSPITALS:
        con.execute(
            "INSERT INTO silver_dim_hospital "
            "SELECT ?, ?, ?, ?, ?, ?, 'Active', NULL, NULL "
            "WHERE NOT EXISTS (SELECT 1 FROM silver_dim_hospital WHERE hospital_id=?)",
            [hid, name, city, profile, beds, hid, hid],
        )
    con.execute(
        "CREATE OR REPLACE VIEW dim_hospital AS SELECT * FROM silver_dim_hospital"
    )

    # 24-month spine (first of month) -- 2025-01-01 .. 2026-12-31
    con.execute(
        "CREATE OR REPLACE TABLE dim_month AS "
        "SELECT CAST(DATE_TRUNC('month', d) AS DATE) AS month "
        "FROM generate_series(DATE '2025-01-01', DATE '2026-12-31', "
        "INTERVAL 1 MONTH) t(d) "
        "GROUP BY 1 ORDER BY 1"
    )

    # Common dimension aliases used by the gold SQL files.
    for table in schema.DIMENSION_TABLES:
        if table == "dim_hospital":
            continue
        src = f"silver_{table}"
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name=?",
            [src],
        ).fetchone()[0] > 0
        if exists:
            con.execute(f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM {src}")


# ---------------------------------------------------------------------------
# Full database load
# ---------------------------------------------------------------------------
def load_all(con: duckdb.DuckDBPyConnection | None = None) -> dict:
    """Load silver, gold, DQ, pipeline and lineage data into DuckDB.

    Returns a dictionary of ``table -> row_count`` for everything created.
    """
    own = con is None
    conn = con or connect()
    counts: dict[str, int] = {}
    try:
        silver_dir = Path(config.SILVER_DIR)
        gold_dir = Path(config.GOLD_DIR)
        meta_dir = silver_dir / "_meta"
        dq_dir = silver_dir / "_dq"

        # --- silver transactional + dimension tables -----------------------
        for table in schema.TABLES:
            parquet = _parquet_path(silver_dir, table)
            if parquet.exists():
                safe_path = str(parquet).replace("'", "''").replace("\\", "/")
                conn.execute(
                    f"CREATE OR REPLACE TABLE silver_{table} AS "
                    f"SELECT * FROM read_parquet('{safe_path}')"
                )
            counts[f"silver_{table}"] = conn.execute(
                f"SELECT COUNT(*) FROM silver_{table}"
            ).fetchone()[0] if conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name=?",
                [f"silver_{table}"],
            ).fetchone()[0] else 0

        ensure_spines(conn)

        # --- gold tables (typed exactly per CONTRACT.md section 3) ----------
        for table, columns in GOLD_TYPES.items():
            parquet = _parquet_path(gold_dir, table)
            if parquet.exists():
                _create_typed_table(conn, table, parquet, columns)
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

        # --- data-quality tables -------------------------------------------
        dq_rule_parquet = _parquet_path(dq_dir, "dq_rules")
        dq_fail_parquet = _parquet_path(dq_dir, "dq_failures")
        if dq_rule_parquet.exists():
            _create_typed_table(conn, "dq_rules", dq_rule_parquet, DQ_RULE_TYPES)
        else:
            conn.execute(
                "CREATE OR REPLACE TABLE dq_rules (" +
                ", ".join(f'"{n}" {t}' for n, t in DQ_RULE_TYPES) + ")"
            )
        counts["dq_rules"] = conn.execute("SELECT COUNT(*) FROM dq_rules").fetchone()[0]

        if dq_fail_parquet.exists():
            _create_typed_table(conn, "dq_failures", dq_fail_parquet, DQ_FAILURE_TYPES)
        else:
            conn.execute(
                "CREATE OR REPLACE TABLE dq_failures (" +
                ", ".join(f'"{n}" {t}' for n, t in DQ_FAILURE_TYPES) + ")"
            )
        counts["dq_failures"] = conn.execute("SELECT COUNT(*) FROM dq_failures").fetchone()[0]

        # --- pipeline run history + lineage --------------------------------
        runs_parquet = _parquet_path(meta_dir, "pipeline_runs")
        if runs_parquet.exists():
            _create_typed_table(conn, "pipeline_runs", runs_parquet, PIPELINE_RUN_TYPES)
        else:
            conn.execute(
                "CREATE OR REPLACE TABLE pipeline_runs (" +
                ", ".join(f'"{n}" {t}' for n, t in PIPELINE_RUN_TYPES) + ")"
            )
        counts["pipeline_runs"] = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]

        lineage_parquet = _parquet_path(meta_dir, "lineage")
        if lineage_parquet.exists():
            _create_typed_table(conn, "lineage", lineage_parquet, LINEAGE_TYPES)
        else:
            conn.execute(
                "CREATE OR REPLACE TABLE lineage (" +
                ", ".join(f'"{n}" {t}' for n, t in LINEAGE_TYPES) + ")"
            )
        counts["lineage"] = conn.execute("SELECT COUNT(*) FROM lineage").fetchone()[0]

        return counts
    finally:
        if own:
            conn.close()
