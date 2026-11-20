"""HOSPITAL 360 pipeline orchestration.

    python -m etl.pipeline

bronze -> silver -> quality(silver) -> gold -> quality(gold) -> DuckDB -> manifest

Every run writes ``data/manifests/pipeline_<run_id>.json`` and appends a row to
``pipeline_runs`` (parquet + DuckDB table).  A ``lineage`` table maps each
target table to its source tables and transformations for the /pipeline/lineage
API endpoint and the Data Explorer.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from generator import config, schema
from etl import bronze, db, gold, quality, silver

# ---------------------------------------------------------------------------
# Documented lineage used by /pipeline/lineage and the Data Explorer.
# ---------------------------------------------------------------------------
GOLD_LINEAGE: dict[str, dict[str, Any]] = {
    "gold_network_daily": {
        "sources": ["dim_date", "silver_encounters", "silver_admissions", "silver_appointments",
                    "silver_invoices", "silver_payments", "silver_bed_snapshots"],
        "transformations": "Daily date spine; count/aggregate each fact by calendar date; "
                           "coalesce counts to 0; paid collections net of refunds.",
    },
    "gold_hospital_monthly": {
        "sources": ["dim_hospital", "dim_month", "dim_lab_test"] + [f"silver_{t}" for t in schema.FACT_TABLES],
        "transformations": "10 hospitals x 24 months grid; left-joined monthly aggregates; "
                           "no-show/compliance/denial rates exclude cancelled or non-adjudicated rows; "
                           "NULL denominators produce NULL; all rates rounded to 2dp.",
    },
    "gold_department_monthly": {
        "sources": ["dim_department", "dim_specialty", "dim_month", "silver_encounters",
                    "silver_admissions", "silver_appointments", "silver_bed_snapshots",
                    "silver_invoices", "silver_lab_orders", "silver_lab_results",
                    "silver_claims", "silver_feedback", "silver_incidents"],
        "transformations": "Department x month grid; hospital-level bed occupancy used as documented proxy.",
    },
    "gold_patient_access": {
        "sources": ["dim_department", "dim_month", "silver_appointments"],
        "transformations": "Appointment no-shows / (completed + no-shows); cancelled excluded; "
                           "lead days, same-day and reschedule rates.",
    },
    "gold_bed_utilization": {
        "sources": ["silver_bed_snapshots", "silver_admissions", "dim_bed"],
        "transformations": "Ward x month snapshots; blocked beds excluded from occupancy denominator; "
                           "bed turnover = discharges / total beds.",
    },
    "gold_financial_performance": {
        "sources": ["dim_department", "dim_month", "silver_invoices", "silver_payments", "silver_encounters"],
        "transformations": "collections = cleared payments net of refunds; writeoffs proxied by overdue balances; "
                           "collection_rate = collections / net_revenue; month-over-month LAG growth.",
    },
    "gold_claim_performance": {
        "sources": ["dim_hospital", "dim_payer", "dim_month", "silver_claims", "silver_claim_events"],
        "transformations": "denial_rate = denied / (approved + denied) adjudicated only; "
                           "appeal success from claim events.",
    },
    "gold_lab_performance": {
        "sources": ["dim_hospital", "dim_lab_test", "dim_month", "silver_lab_orders", "silver_lab_results"],
        "transformations": "Test x hospital x month TAT, median TAT and SLA against dim_lab_test.sla_minutes.",
    },
    "gold_workforce": {
        "sources": ["dim_department", "dim_month", "silver_shifts", "silver_attendance", "dim_staff"],
        "transformations": "Hours and headcount from shifts; absence from attendance; "
                           "coverage capped at 100; cost = actual hours x hourly rate.",
    },
    "gold_inventory": {
        "sources": ["dim_hospital", "dim_inventory_item", "dim_month",
                    "silver_inventory_movements", "silver_purchase_orders"],
        "transformations": "Cumulative signed stock by item; low-stock <= reorder level; "
                           "stockouts <= 0; supplier on-time from receipt dates.",
    },
    "gold_patient_experience": {
        "sources": ["dim_department", "dim_month", "silver_feedback"],
        "transformations": "satisfaction_pct = AVG(rating)/5*100; "
                           "nps = (promoters(nps>=9) - detractors(nps<=6)) / total * 100.",
    },
    "gold_quality_safety": {
        "sources": ["dim_department", "dim_month", "silver_incidents", "silver_encounters", "silver_admissions"],
        "transformations": "Incidents per 100 encounters; readmissions per discharge; "
                           "investigation completion rate.",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def next_run_id(manifest_dir: Path | None = None) -> str:
    directory = Path(manifest_dir) if manifest_dir is not None else Path(config.MANIFEST_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y%m%d")
    prefix = f"pipeline_RUN_{day}_"
    existing = [p for p in directory.glob(prefix + "*.json")]
    sequence = len(existing) + 1
    return f"RUN_{day}_{sequence:03d}"


def _write_meta(parquet_path: Path, rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> None:
    """Append rows to a parquet-backed metadata table (idempotent per run_id)."""
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame = frame[[c for c, _ in columns if c in frame.columns]]
    if parquet_path.exists():
        previous = pd.read_parquet(parquet_path)
        key = "run_id" if "run_id" in frame.columns else "target_table"
        if key in previous.columns and key in frame.columns:
            previous = previous[~previous[key].isin(frame[key].tolist())]
        frame = pd.concat([previous, frame], ignore_index=True)
    frame.to_parquet(parquet_path, index=False)


def _build_lineage_rows(run_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table in schema.TABLES:
        rows.append({
            "target_table": f"silver_{table}",
            "layer": "silver",
            "source_tables": json.dumps([f"bronze/{table}/{table}.csv"]),
            "transformations": "type correction; trim/standardise; PK dedup; null, date, "
                               "range, FK and quarantine rules (see etl/silver.py)",
        })
    for table, spec in GOLD_LINEAGE.items():
        rows.append({
            "target_table": table,
            "layer": "gold",
            "source_tables": json.dumps(spec["sources"]),
            "transformations": spec["transformations"],
        })
    return rows


def run_pipeline(run_id: str | None = None, bronze_dir: Path | None = None) -> dict[str, Any]:
    """Execute the full pipeline and return the manifest dictionary."""
    run_id = run_id or next_run_id()
    start = datetime.now(timezone.utc)
    manifest_dir = Path(config.MANIFEST_DIR)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"pipeline_{run_id}.json"
    error_message: str | None = None
    status = "success"

    try:
        # 1. Bronze ---------------------------------------------------------
        bronze_out = bronze.ingest_all(run_id, bronze_dir=bronze_dir)

        # 2. Silver ---------------------------------------------------------
        silver_out = silver.clean_all(
            bronze_out["frames"], bronze_out["manifest"], run_id,
        )

        # 3. Quality on silver ----------------------------------------------
        silver_rules = quality.run_silver(silver_out["tables"], run_id)

        # 4. Gold -----------------------------------------------------------
        gold_out = gold.build_all()

        # 5. Quality with analytical reconciliation -------------------------
        gold_rules = quality.run_gold(gold_out["tables"], run_id)
        dq = quality.write_results(silver_rules + gold_rules,
                                   silver_out["quarantine_records"], run_id)

        # 6. Metadata -------------------------------------------------------
        end = datetime.now(timezone.utc)
        duration = round((end - start).total_seconds(), 3)
        tables_created = len(silver_out["tables"]) + len(gold_out["tables"]) + 5
        run_row = {
            "run_id": run_id,
            "start_time": pd.Timestamp(start),
            "end_time": pd.Timestamp(end),
            "duration_seconds": duration,
            "status": status,
            "source_records": silver_out["source_rows"],
            "valid_records": silver_out["valid_rows"],
            "quarantined_records": silver_out["quarantined_rows"],
            "tables_created": tables_created,
            "error_message": None,
        }
        meta_dir = Path(config.SILVER_DIR) / "_meta"
        _write_meta(meta_dir / "pipeline_runs.parquet", [run_row], db.PIPELINE_RUN_TYPES)
        _write_meta(meta_dir / "lineage.parquet", _build_lineage_rows(run_id), db.LINEAGE_TYPES)

        # 7. DuckDB load ----------------------------------------------------
        db_counts = db.load_all()

        manifest: dict[str, Any] = {
            "run_id": run_id,
            "generator_version": config.GENERATOR_VERSION,
            "seed": config.SEED,
            "status": status,
            "start_time": start.isoformat().replace("+00:00", "Z"),
            "end_time": end.isoformat().replace("+00:00", "Z"),
            "duration_seconds": duration,
            "bronze": bronze_out["manifest"],
            "silver": {
                "reports": silver_out["reports"],
                "source_rows": silver_out["source_rows"],
                "valid_rows": silver_out["valid_rows"],
                "quarantined_rows": silver_out["quarantined_rows"],
            },
            "quality": {
                "dq_score": dq["dq_score"],
                "scoring": dq["scoring"],
                "summary": dq["summary"],
                "dq_results_path": dq["dq_results_path"],
            },
            "gold": {
                "row_counts": gold_out["row_counts"],
                "sql_models": gold_out["sql_models"],
                "validation": gold_out["validation"],
            },
            "quarantine": silver_out["quarantine_summary"],
            "duckdb_tables": db_counts,
            "totals": {
                "source_records": silver_out["source_rows"],
                "valid_records": silver_out["valid_rows"],
                "quarantined_records": silver_out["quarantined_rows"],
                "tables_created": tables_created,
            },
            "manifest_path": str(manifest_path),
        }
    except Exception as exc:  # pragma: no cover - exercised only on failure
        status = "failed"
        error_message = f"{type(exc).__name__}: {exc}"
        end = datetime.now(timezone.utc)
        manifest = {
            "run_id": run_id, "status": status,
            "start_time": start.isoformat().replace("+00:00", "Z"),
            "end_time": end.isoformat().replace("+00:00", "Z"),
            "duration_seconds": round((end - start).total_seconds(), 3),
            "error_message": error_message,
        }
        try:
            meta_dir = Path(config.SILVER_DIR) / "_meta"
            _write_meta(meta_dir / "pipeline_runs.parquet", [{
                "run_id": run_id, "start_time": pd.Timestamp(start),
                "end_time": pd.Timestamp(end),
                "duration_seconds": manifest["duration_seconds"],
                "status": status, "source_records": 0, "valid_records": 0,
                "quarantined_records": 0, "tables_created": 0,
                "error_message": error_message,
            }], db.PIPELINE_RUN_TYPES)
        except Exception:
            pass

    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    if status == "success":
        print_summary(manifest)
    else:
        print(f"PIPELINE FAILED [{run_id}]: {error_message}")
    return manifest


def print_summary(manifest: dict[str, Any]) -> None:
    """Print the required end-of-run summary."""
    print(f"\n=== HOSPITAL 360 PIPELINE {manifest['run_id']} — {manifest['status'].upper()} ===")
    print(f"Duration: {manifest['duration_seconds']}s")
    totals = manifest["totals"]
    print(f"Source records: {totals['source_records']:,} | "
          f"Valid: {totals['valid_records']:,} | "
          f"Quarantined: {totals['quarantined_records']:,}")
    print(f"DQ score: {manifest['quality']['dq_score']} / 100 "
          f"({manifest['quality']['summary']['failed_rules']} failed rules)")
    print("Gold table row counts:")
    for table, count in manifest["gold"]["row_counts"].items():
        print(f"  {table:<32} {count:>8,}")
    q = manifest["quarantine"]
    print(f"Quarantine by rule: {q.get('by_rule', {})}")
    grid = manifest["gold"]["validation"].get("hospital_monthly_grid", {})
    print(f"Hospital x month grid: {grid.get('actual')} / {grid.get('expected')} "
          f"({'OK' if grid.get('passed') else 'FAILED'})")
    print(f"Manifest: {manifest['manifest_path']}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the HOSPITAL 360 ETL pipeline")
    parser.add_argument("--run-id", help="Explicit run id (default RUN_YYYYMMDD_NNN)")
    parser.add_argument("--bronze-dir", help="Override bronze CSV directory")
    args = parser.parse_args()
    manifest = run_pipeline(
        run_id=args.run_id,
        bronze_dir=Path(args.bronze_dir) if args.bronze_dir else None,
    )
    raise SystemExit(0 if manifest.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
