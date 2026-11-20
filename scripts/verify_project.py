"""End-to-end verification of the HOSPITAL 360 build.

Usage:  python scripts/verify_project.py
Checks generated data, DuckDB gold models and all API endpoint groups.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def check_bronze() -> bool:
    section("1. BRONZE DATA")
    bronze = ROOT / "data" / "bronze"
    if not bronze.exists():
        print("  [FAIL] data/bronze does not exist")
        return False
    files = sorted(bronze.glob("*/*.csv"))
    if not files:
        print("  [FAIL] no bronze CSV files found")
        return False
    total = 0
    for f in files:
        try:
            with f.open("r", encoding="utf-8", errors="replace") as fh:
                n = sum(1 for _ in fh) - 1
        except OSError:
            n = -1
        total += max(n, 0)
        print(f"  {f.parent.name:24s} {n:>9,}")
    print(f"  {'TOTAL':24s} {total:>9,}")
    return total >= 500_000


def check_manifest() -> bool:
    section("2. MANIFEST")
    manifests = sorted((ROOT / "data" / "manifests").glob("*.json"))
    if not manifests:
        print("  [FAIL] no manifests found")
        return False
    for m in manifests:
        print(f"  {m.name}")
        try:
            payload = json.loads(m.read_text(encoding="utf-8"))
            print("    " + json.dumps(payload, default=str)[:300])
        except json.JSONDecodeError as exc:
            print(f"    [FAIL] invalid JSON: {exc}")
    return True


def check_duckdb() -> bool:
    section("3. DUCKDB GOLD MODELS")
    import duckdb

    path = ROOT / "data" / "hospital360.duckdb"
    if not path.exists():
        print("  [FAIL] analytical database not found")
        return False
    con = duckdb.connect(str(path), read_only=True)
    tables = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables ORDER BY table_name"
    ).fetchall()]
    gold = [t for t in tables if t.startswith("gold_")]
    print(f"  tables={len(tables)} gold_models={len(gold)}")
    ok = True
    for t in tables:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:36s} {n:>10,}")
        if t.startswith("gold_") and n == 0:
            ok = False
    if "gold_hospital_monthly" in tables:
        n = con.execute("SELECT COUNT(*) FROM gold_hospital_monthly").fetchone()[0]
        if n != 240:
            print(f"  [WARN] gold_hospital_monthly has {n} rows (expected 240 = 10 hospitals x 24 months)")
    con.close()
    return ok and len(gold) >= 12


def check_api() -> bool:
    section("4. API ENDPOINTS")
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    endpoints = [
        "/health",
        "/api/v1/overview/kpis",
        "/api/v1/overview/trends",
        "/api/v1/overview/hospital-ranking",
        "/api/v1/overview/heatmap",
        "/api/v1/hospitals",
        "/api/v1/hospitals/H01/kpis",
        "/api/v1/appointments/kpis",
        "/api/v1/emergency/kpis",
        "/api/v1/inpatient/kpis",
        "/api/v1/procedures/kpis",
        "/api/v1/diagnostics/kpis",
        "/api/v1/pharmacy/kpis",
        "/api/v1/finance/kpis",
        "/api/v1/claims/kpis",
        "/api/v1/workforce/kpis",
        "/api/v1/inventory/kpis",
        "/api/v1/experience/kpis",
        "/api/v1/quality/kpis",
        "/api/v1/data-quality/summary",
        "/api/v1/pipeline/runs",
        "/api/v1/explorer/datasets",
        "/api/v1/kpis/glossary",
    ]
    failed = []
    for ep in endpoints:
        try:
            resp = client.get(ep)
            status = resp.status_code
            body = resp.text[:160]
        except Exception as exc:  # noqa: BLE001 - report broken endpoints instead of crashing the verifier
            status = "EXC"
            body = f"{type(exc).__name__}: {exc}"[:160]
        flag = "OK" if status == 200 else f"HTTP {status}"
        print(f"  {flag:>10s}  {ep}")
        if status != 200:
            failed.append((ep, status, body))
    if failed:
        print("\n  Failures:")
        for ep, code, body in failed:
            print(f"    {ep} -> {code}: {body}")
    return not failed


def main() -> int:
    results = {
        "bronze": check_bronze(),
        "manifest": check_manifest(),
        "duckdb": check_duckdb(),
        "api": check_api(),
    }
    section("SUMMARY")
    for name, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL':6s}  {name}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
