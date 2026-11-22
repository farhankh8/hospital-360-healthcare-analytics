#!/usr/bin/env python3
"""Generate web/lib/landing-stats.json from measured sources.

Sources:
- data/manifests/pipeline_RUN_20261121_001.json (or latest pipeline manifest)
- pytest --collect-only -q
- playwright test --list --config=e2e/playwright.config.ts

Fallback: omit unavailable stats; never fail the build on missing sources.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
OUT = WEB / "lib" / "landing-stats.json"


def latest_manifest() -> Path | None:
    manifests = sorted((ROOT / "data" / "manifests").glob("pipeline_RUN_*.json"))
    return manifests[-1] if manifests else None


def read_manifest() -> dict:
    path = latest_manifest()
    if not path or not path.exists():
        return {}
    try:
        m = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    bronze = m.get("bronze", {}).get("tables", {})
    totals = m.get("totals", {})
    gold_obj = m.get("gold", {})
    gold_tables = gold_obj.get("tables") if isinstance(gold_obj, dict) else None
    gold_row_counts = gold_obj.get("row_counts") if isinstance(gold_obj, dict) else None
    if isinstance(gold_tables, dict) and gold_tables:
        gold_count = len(gold_tables)
    elif isinstance(gold_tables, list) and gold_tables:
        gold_count = len(gold_tables)
    elif isinstance(gold_row_counts, dict) and gold_row_counts:
        gold_count = len(gold_row_counts)
    else:
        gold_count = None
    return {
        "manifest_run_id": m.get("run_id"),
        "manifest_path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "hospitals": bronze.get("dim_hospital", {}).get("row_count"),
        "patients": bronze.get("dim_patient", {}).get("row_count"),
        "encounters": bronze.get("encounters", {}).get("row_count"),
        "appointments": bronze.get("appointments", {}).get("row_count"),
        "bronze_rows": totals.get("source_records"),
        "bronze_tables": len(bronze) if bronze else None,
        "valid_records": totals.get("valid_records"),
        "quarantined_records": totals.get("quarantined_records"),
        "gold_tables": gold_count,
        "doctors": bronze.get("dim_doctor", {}).get("row_count"),
        "staff": bronze.get("dim_staff", {}).get("row_count"),
        "beds": bronze.get("dim_bed", {}).get("row_count"),
        "admissions": bronze.get("admissions", {}).get("row_count"),
        "lab_orders": bronze.get("lab_orders", {}).get("row_count"),
        "invoices": bronze.get("billing_invoices", {}).get("row_count"),
        "claims": bronze.get("billing_claims", {}).get("row_count"),
    }


def pytest_collected() -> int | None:
    try:
        proc = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        text = proc.stdout + "\n" + proc.stderr
        m = re.search(r"(\d+)\s+tests?\s+collected", text)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def playwright_listed() -> int | None:
    try:
        proc = subprocess.run(
            ["npx", "playwright", "test", "--config=e2e/playwright.config.ts", "--list"],
            cwd=WEB,
            capture_output=True,
            text=True,
            timeout=180,
            shell=True,
        )
        text = proc.stdout + "\n" + proc.stderr
        m = re.search(r"Total:\s*(\d+)\s+tests?\s+in", text)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def main() -> None:
    data = read_manifest()
    data["pytest_collected"] = pytest_collected()
    data["playwright_tests"] = playwright_listed()
    from datetime import datetime, timezone
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
