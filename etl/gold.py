"""Gold layer — 12 business-ready analytical models built with DuckDB SQL.

Each model lives in ``analytics/sql/<nn>_<gold_table>.sql``.  The SQL is
executed against the silver tables registered from parquet; the result is
coerced to the exact CONTRACT.md section 3 column order/types, written to
``data/gold/<table>.parquet`` and materialised as a typed DuckDB table.

Every model is smoke-tested immediately with ``SELECT * ... LIMIT 5`` and
``SELECT COUNT(*) ...``; NaN/Inf values are replaced with NULL before storage.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from generator import config, schema
from etl import db

SQL_DIR_NAME = "sql"


def sql_directory() -> Path:
    return Path(config.ANALYTICS_DIR) / SQL_DIR_NAME


def load_sql_models(sql_dir: Path | None = None) -> dict[str, str]:
    """Return ``{gold_table: SQL text}`` ordered by numeric filename prefix."""
    directory = Path(sql_dir) if sql_dir is not None else sql_directory()
    models: dict[str, str] = {}
    for path in sorted(directory.glob("*.sql")):
        match = re.match(r"^(\d+)_(gold_\w+)\.sql$", path.name)
        if not match:
            continue
        models[match.group(2)] = path.read_text(encoding="utf-8")
    expected = set(db.GOLD_TYPES)
    missing = expected - set(models)
    if missing:
        raise FileNotFoundError(
            f"Missing gold SQL models in {directory}: {sorted(missing)}"
        )
    return models


def register_silver(con, silver_dir: Path) -> None:
    """Register every silver parquet as ``silver_<table>`` plus dimension aliases."""
    for table in schema.TABLES:
        parquet = Path(silver_dir) / f"{table}.parquet"
        target = f"silver_{table}"
        if parquet.exists():
            safe = str(parquet).replace("'", "''").replace("\\", "/")
            con.execute(
                f"CREATE OR REPLACE TABLE {target} AS "
                f"SELECT * FROM read_parquet('{safe}')"
            )
        else:
            cols = ", ".join(f'"{c}" VARCHAR' for c in schema.columns(table))
            con.execute(f"CREATE OR REPLACE TABLE {target} ({cols})")
    db.ensure_spines(con)


def _coerce_model(frame: pd.DataFrame, table: str) -> pd.DataFrame:
    """Enforce exact column order and contract dtypes; replace NaN/Inf with NULL."""
    columns = db.GOLD_TYPES[table]
    expected = [name for name, _ in columns]
    missing = [c for c in expected if c not in frame.columns]
    if missing:
        raise ValueError(f"{table}: SQL is missing columns {missing}")
    frame = frame[expected].copy()
    for name, dtype in columns:
        series = frame[name]
        if dtype == "INTEGER":
            frame[name] = pd.to_numeric(series, errors="coerce").fillna(0).astype("int64")
        elif dtype == "DOUBLE":
            numeric = pd.to_numeric(series, errors="coerce").astype("float64")
            numeric = numeric.replace([np.inf, -np.inf], np.nan)
            frame[name] = numeric.astype("float64")
        elif dtype == "VARCHAR":
            frame[name] = series.astype("string")
        elif dtype == "DATE":
            frame[name] = pd.Series(
                [(v.date() if isinstance(v, pd.Timestamp) else v) for v in series],
                index=series.index, dtype="object",
            )
    return frame


def build_all(
    silver_dir: Path | None = None,
    gold_dir: Path | None = None,
    sql_dir: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Build, persist and validate all 12 gold tables."""
    silver_path = Path(silver_dir) if silver_dir is not None else Path(config.SILVER_DIR)
    gold_path = Path(gold_dir) if gold_dir is not None else Path(config.GOLD_DIR)
    gold_path.mkdir(parents=True, exist_ok=True)

    models = load_sql_models(sql_dir)
    con = db.connect(db_path)
    tables: dict[str, pd.DataFrame] = {}
    row_counts: dict[str, int] = {}
    validation: dict[str, Any] = {}
    try:
        register_silver(con, silver_path)
        for table, sql in models.items():
            frame = con.execute(sql).df()
            frame = _coerce_model(frame, table)
            parquet = gold_path / f"{table}.parquet"
            frame.to_parquet(parquet, index=False)
            db._create_typed_table(con, table, parquet, db.GOLD_TYPES[table])

            # Quality bar: every table must be queryable and countable.
            preview = con.execute(f"SELECT * FROM {table} LIMIT 5").df()
            count = int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            tables[table] = frame
            row_counts[table] = count
            validation[table] = {
                "preview_rows": int(len(preview)),
                "count": count,
                "columns": list(frame.columns),
                "parquet": str(parquet),
            }

        monthly = tables.get("gold_hospital_monthly")
        monthly_rows = int(len(monthly)) if monthly is not None else 0
        validation["hospital_monthly_grid"] = {
            "expected": len(config.HOSPITALS) * 24,
            "actual": monthly_rows,
            "passed": monthly_rows == len(config.HOSPITALS) * 24,
        }
        return {
            "tables": tables,
            "row_counts": row_counts,
            "validation": validation,
            "sql_models": sorted(models),
        }
    finally:
        con.close()
