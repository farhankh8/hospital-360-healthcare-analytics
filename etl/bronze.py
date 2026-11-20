"""Bronze layer — lossless ingestion of the generator's CSV files.

Every value is read as text (``dtype=str`` withNA filtering disabled) so the
raw source representation is preserved byte-for-byte apart from CSV quoting.
No casting, trimming, de-duplication or null substitution happens here.

Outputs
-------
* ``data/silver/_bronze_ingest/<table>.parquet`` -- raw string-typed copy
* ``data/silver/_bronze_ingest/manifest.json``  -- bronze manifest

The manifest is also returned to the caller for embedding in the pipeline
manifest; no files are written to ``data/manifests`` from this module.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from generator import config, schema

SOURCE_LAYER = "bronze_csv"
RAW_SUBDIR = "_bronze_ingest"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def find_csv(bronze_dir: Path, table: str) -> Path | None:
    """Locate ``<table>.csv`` using the generator's layout with flat-file
    fallback: ``bronze/<table>/<table>.csv`` then ``bronze/<table>.csv``."""
    candidates = [
        Path(bronze_dir) / table / f"{table}.csv",
        Path(bronze_dir) / f"{table}.csv",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def read_raw_csv(path: Path) -> pd.DataFrame:
    """Read a CSV with every cell preserved as its original string."""
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        encoding="utf-8",
        on_bad_lines="warn",
    )


def ingest_all(
    run_id: str,
    bronze_dir: Path | None = None,
    raw_dir: Path | None = None,
) -> dict[str, Any]:
    """Ingest all canonical tables found in bronze.

    Returns a dictionary with keys ``manifest``, ``frames`` (table -> raw
    DataFrame), ``tables`` and ``total_rows``.
    """
    bronze_path = Path(bronze_dir) if bronze_dir is not None else Path(config.BRONZE_DIR)
    raw_path = Path(raw_dir) if raw_dir is not None else Path(config.SILVER_DIR) / RAW_SUBDIR
    raw_path.mkdir(parents=True, exist_ok=True)

    batch_id = f"BATCH_{run_id}"
    ingested_at = _now()
    frames: dict[str, pd.DataFrame] = {}
    table_entries: dict[str, Any] = {}
    total_rows = 0

    for table in schema.BRONZE_TABLES:
        csv_path = find_csv(bronze_path, table)
        if csv_path is None:
            # Missing tables are reported explicitly -- never silently ignored.
            table_entries[table] = {
                "source": SOURCE_LAYER,
                "batch_id": batch_id,
                "file_name": None,
                "created_time": None,
                "row_count": 0,
                "columns": schema.columns(table),
                "schema": [
                    {"column": col, "dtype": dtype, "description": desc}
                    for col, dtype, desc in schema.TABLES[table]
                ],
                "raw_parquet": None,
                "status": "missing",
            }
            continue

        raw = read_raw_csv(csv_path)
        # Preserve canonical column order without silently dropping data.
        expected = schema.columns(table)
        extra = [c for c in raw.columns if c not in expected]
        if extra:
            # Keep the columns in the raw parquet but flag them in the manifest;
            # silver uses the canonical schema as its contract.
            pass

        raw_parquet = raw_path / f"{table}.parquet"
        raw.to_parquet(raw_parquet, index=False)
        frames[table] = raw
        stat = csv_path.stat()
        rows = int(len(raw))
        total_rows += rows
        table_entries[table] = {
            "source": SOURCE_LAYER,
            "batch_id": batch_id,
            "file_name": csv_path.name,
            "file_path": str(csv_path),
            "created_time": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            .isoformat(timespec="seconds").replace("+00:00", "Z"),
            "row_count": rows,
            "columns": list(raw.columns),
            "schema": [
                {"column": col,
                 "dtype": next((dt for c, dt, _ in schema.TABLES[table] if c == col), "string"),
                 "description": next((d for c, _, d in schema.TABLES[table] if c == col), "")}
                for col in raw.columns
            ],
            "unexpected_columns": extra,
            "raw_parquet": str(raw_parquet),
            "status": "ingested",
        }

    manifest: dict[str, Any] = {
        "run_id": run_id,
        "batch_id": batch_id,
        "layer": "bronze",
        "source": SOURCE_LAYER,
        "generator_version": config.GENERATOR_VERSION,
        "seed": config.SEED,
        "ingested_at": ingested_at,
        "bronze_dir": str(bronze_path),
        "raw_parquet_dir": str(raw_path),
        "tables": table_entries,
        "total_rows": total_rows,
        "tables_ingested": sum(1 for v in table_entries.values() if v["status"] == "ingested"),
        "tables_missing": sum(1 for v in table_entries.values() if v["status"] == "missing"),
        "notes": (
            "Values are preserved as raw strings. Type correction, null handling "
            "and de-duplication occur only in the silver layer."
        ),
    }

    manifest_path = raw_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)

    return {
        "manifest": manifest,
        "frames": frames,
        "tables": list(frames),
        "total_rows": total_rows,
    }
