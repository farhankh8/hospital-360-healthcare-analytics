"""Data-quality framework for HOSPITAL 360.

Runs a documented rule set over the silver and gold layers and produces:

* ``data/manifests/dq_results.json`` -- every rule with category, severity,
  pass/fail status and the weighted DQ score;
* ``data/silver/_dq/dq_rules.parquet`` and ``dq_failures.parquet`` -- loaded by
  :mod:`etl.db` into the DuckDB tables ``dq_rules`` / ``dq_failures`` used by
  the ``/data-quality/*`` API endpoints.

Scoring (documented in the JSON output)
---------------------------------------
Each rule contributes ``weight = SEVERITY_WEIGHT[severity]`` and a pass ratio
``passed / checked``.  A category score is the severity-weighted mean of its
rule ratios expressed as a percentage.  The overall score is the weighted mean
of the six category scores using ``CATEGORY_WEIGHTS`` (they sum to 1.0).  This
prevents a large number of trivial checks from drowning out referential or
validity failures.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from etl import db
from etl.silver import (
    DATE_ORDER_CROSS,
    DATE_ORDER_INTRA,
    FOREIGN_KEYS,
    NULLABLE_FKS,
    PRIMARY_KEYS,
    PROCESS_ORDER,
)
from generator import config, schema

CATEGORY_WEIGHTS: dict[str, float] = {
    "Completeness": 0.15,
    "Validity": 0.20,
    "Uniqueness": 0.15,
    "Referential integrity": 0.20,
    "Consistency": 0.20,
    "Timeliness": 0.10,
}
SEVERITY_WEIGHTS: dict[str, float] = {"error": 3.0, "warning": 1.0, "info": 0.5}

CANONICAL_HOSPITALS = {h[0] for h in config.HOSPITALS}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _result(
    rule_id: str,
    rule_name: str,
    category: str,
    table: str,
    severity: str,
    description: str,
    failed_count: int,
    checked_count: int,
    run_id: str,
    samples: list[str] | None = None,
) -> dict[str, Any]:
    failed_count = int(failed_count)
    return {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "category": category,
        "table": table,
        "passed": failed_count == 0,
        "failed_count": failed_count,
        "checked_count": int(checked_count),
        "severity": severity,
        "description": description,
        "checked_at": _now(),
        "pipeline_run_id": run_id,
        "sample_failures": (samples or [])[:5],
    }


def _expected_dtype_family(token: str) -> str:
    return {
        "string": "string", "int64": "integer", "float64": "float",
        "bool": "boolean", "datetime64[ns]": "datetime", "date": "date",
    }.get(token, token)


def _actual_dtype_family(series: pd.Series) -> str:
    dtype = series.dtype
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_integer_dtype(dtype):
        return "integer"
    if pd.api.types.is_float_dtype(dtype):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    if dtype == object and len(series) and isinstance(series.dropna().iloc[0] if series.dropna().size else None, date):
        return "date"
    return "string"


def _as_datetime(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except (ValueError, TypeError):
        return pd.to_datetime(series, errors="coerce")


# ---------------------------------------------------------------------------
# Silver rules
# ---------------------------------------------------------------------------
def run_silver(silver_tables: dict[str, pd.DataFrame], run_id: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for table in PROCESS_ORDER:
        df = silver_tables.get(table)
        if df is None:
            continue

        # --- schema --------------------------------------------------------
        expected = schema.columns(table)
        missing = [c for c in expected if c not in df.columns]
        unexpected = [c for c in df.columns if c not in expected]
        bad_dtypes: list[str] = []
        for col, token, _ in schema.TABLES[table]:
            if col not in df.columns:
                continue
            if _expected_dtype_family(token) != _actual_dtype_family(df[col]):
                bad_dtypes.append(f"{col}:{df[col].dtype}")
        failures = missing + unexpected + bad_dtypes
        results.append(_result(
            f"SCHEMA_{table.upper()}", f"Schema contract: {table}", "Validity", table,
            "error", "All canonical columns exist with the documented pandas dtype family.",
            len(failures), len(expected), run_id, failures,
        ))

        # --- primary key uniqueness / completeness -------------------------
        pk = PRIMARY_KEYS.get(table)
        if pk and pk in df.columns:
            n = len(df)
            dupes = int(df[pk].dropna().duplicated().sum())
            results.append(_result(
                f"PK_UNIQUE_{table.upper()}", f"Unique primary key: {table}.{pk}",
                "Uniqueness", table, "error", "No duplicate primary key values in silver.",
                dupes, n, run_id,
                [str(v) for v in df.loc[df[pk].dropna().duplicated(), pk].head(5).tolist()],
            ))
            nulls = int(df[pk].isna().sum())
            results.append(_result(
                f"PK_NOT_NULL_{table.upper()}", f"Primary key present: {table}.{pk}",
                "Completeness", table, "error", "Primary key is never null.",
                nulls, n, run_id,
            ))

        # --- hospital code validity ----------------------------------------
        if "hospital_id" in df.columns:
            invalid = int((~df["hospital_id"].isna() &
                           ~df["hospital_id"].isin(CANONICAL_HOSPITALS)).sum())
            results.append(_result(
                f"HOSPITAL_CODE_{table.upper()}", f"Canonical hospital codes: {table}",
                "Validity", table, "error", "hospital_id is one of H01..H10.",
                invalid, len(df), run_id,
            ))

        # --- FK referential integrity --------------------------------------
        for col, parent in FOREIGN_KEYS.get(table, []):
            if col not in df.columns or parent not in silver_tables:
                continue
            parent_pk = PRIMARY_KEYS[parent]
            if parent_pk not in silver_tables[parent].columns:
                continue
            valid = set(silver_tables[parent][parent_pk].dropna().tolist())
            present = df[col].notna()
            orphan = present & ~df[col].isin(valid)
            nullable = (table, col) in NULLABLE_FKS
            results.append(_result(
                f"FK_{table.upper()}_{col.upper()}", f"FK {table}.{col} -> {parent}",
                "Referential integrity", table, "warning" if nullable else "error",
                "Every non-null foreign key resolves to a silver parent record."
                + (" (column is business-nullable; nulls are retained with a warning.)" if nullable else ""),
                int(orphan.sum()), int(present.sum()), run_id,
                [str(v) for v in df.loc[orphan, col].dropna().head(5).tolist()],
            ))
            if nullable:
                results.append(_result(
                    f"NULL_FK_{table.upper()}_{col.upper()}", f"Completeness {table}.{col}",
                    "Completeness", table, "warning",
                    "Business-nullable FK null count (retained, not quarantined).",
                    int((~present).sum()), len(df), run_id,
                ))

        # --- intra-table timelines -----------------------------------------
        for left, right, reason in DATE_ORDER_INTRA.get(table, []):
            if left not in df.columns or right not in df.columns:
                continue
            l, r = _as_datetime(df[left]), _as_datetime(df[right])
            bad = l.notna() & r.notna() & (l < r)
            results.append(_result(
                f"TIMELINE_{table.upper()}_{left.upper()}", f"Timeline: {table} {left} >= {right}",
                "Consistency", table, "error", f"Business rule: {reason}.",
                int(bad.sum()), int((l.notna() & r.notna()).sum()), run_id,
            ))

        # --- business logic -------------------------------------------------
        if table == "appointments" and "status" in df.columns:
            bad = ~df["status"].isin(["Completed", "Cancelled", "No-show", "Scheduled"]) & df["status"].notna()
            results.append(_result(
                "BUSINESS_APPOINTMENT_STATUS", "Appointment status vocabulary",
                "Validity", "appointments", "warning",
                "Status is one of Completed / Cancelled / No-show / Scheduled.",
                int(bad.sum()), len(df), run_id,
                df.loc[bad, "status"].dropna().astype(str).head(5).tolist(),
            ))
        if table == "invoices":
            money = ["gross_amount", "discount_amount", "net_amount", "paid_amount", "balance_amount"]
            if all(c in df.columns for c in money):
                v = df[money].fillna(0)
                expected_net = v["gross_amount"] - v["discount_amount"]
                bad = (v["net_amount"] - expected_net).abs().gt(1.0) & v["net_amount"].notna()
                results.append(_result(
                    "BUSINESS_INVOICE_RECONCILE", "Invoice net amount reconciliation",
                    "Consistency", "invoices", "warning",
                    "net_amount = gross_amount - discount_amount (tolerance 1.0).",
                    int(bad.sum()), len(df), run_id,
                ))
        if table == "admissions" and "los_days" in df.columns:
            bad = df["los_days"].notna() & (df["los_days"] < 0)
            results.append(_result(
                "BUSINESS_LOS_NONNEGATIVE", "Length of stay non-negative",
                "Validity", "admissions", "error", "los_days is never negative.",
                int(bad.sum()), len(df), run_id,
            ))

        # --- timeliness -----------------------------------------------------
        date_cols = [c for c, dt, _ in schema.TABLES[table] if dt in ("date", "datetime64[ns]")]
        if date_cols:
            max_dates = []
            for col in date_cols:
                if col not in df.columns:
                    continue
                parsed = _as_datetime(df[col])
                if parsed.notna().any():
                    max_dates.append(parsed.max())
            if max_dates:
                latest = max(max_dates)
                window_end = pd.Timestamp(config.END_DATE) + pd.Timedelta(days=1)
                stale = int(latest > window_end)
                results.append(_result(
                    f"FRESHNESS_{table.upper()}", f"Reporting-window freshness: {table}",
                    "Timeliness", table, "warning",
                    "Latest date does not exceed the configured reporting window end.",
                    stale, 1, run_id, [str(latest)],
                ))

    # --- cross-table timelines ---------------------------------------------
    for child, child_date, parent, parent_date, fk, reason in DATE_ORDER_CROSS:
        df = silver_tables.get(child)
        if df is None or parent not in silver_tables:
            continue
        if child_date not in df.columns or fk not in df.columns:
            continue
        parent_pk = PRIMARY_KEYS[parent]
        lookup = silver_tables[parent].set_index(parent_pk)[parent_date]
        p = _as_datetime(pd.Series(df[fk].map(lookup), index=df.index))
        c = _as_datetime(df[child_date])
        bad = c.notna() & p.notna() & (c < p)
        results.append(_result(
            f"TIMELINE_{child.upper()}_{parent.upper()}", f"Timeline: {child} vs {parent}",
            "Consistency", child, "error", f"Business rule: {reason}.",
            int(bad.sum()), int((c.notna() & p.notna()).sum()), run_id,
        ))

    return results


# ---------------------------------------------------------------------------
# Gold / analytical reconciliation rules
# ---------------------------------------------------------------------------
RATE_COLUMNS: dict[str, list[str]] = {
    "gold_hospital_monthly": ["no_show_rate", "occupancy_rate", "readmission_rate",
                              "collection_rate", "lab_sla_rate", "denial_rate"],
    "gold_department_monthly": ["no_show_rate", "occupancy_rate", "denial_rate"],
    "gold_patient_access": ["no_show_rate", "same_day_pct", "reschedule_rate"],
    "gold_bed_utilization": ["occupancy_rate"],
    "gold_financial_performance": ["collection_rate", "revenue_growth_pct"],
    "gold_claim_performance": ["denial_rate", "appeal_success_rate"],
    "gold_lab_performance": ["sla_rate"],
    "gold_workforce": ["absence_rate", "coverage_pct"],
    "gold_inventory": ["supplier_on_time_rate"],
    "gold_patient_experience": ["satisfaction_pct", "nps"],
    "gold_quality_safety": ["incident_rate", "investigation_completion_rate", "readmission_rate"],
}


def run_gold(gold_tables: dict[str, pd.DataFrame], run_id: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for table, columns in db.GOLD_TYPES.items():
        df = gold_tables.get(table)
        if df is None:
            continue
        expected = [c for c, _ in columns]
        bad = [c for c in expected if c not in df.columns] + [c for c in df.columns if c not in expected]
        results.append(_result(
            f"GOLD_SCHEMA_{table.upper()}", f"Gold contract columns: {table}",
            "Validity", table, "error",
            "Gold table exposes exactly the CONTRACT.md section 3 columns.",
            len(bad), len(expected), run_id, bad,
        ))

        numeric = [c for c, t in columns if t in ("DOUBLE", "INTEGER")]
        infinite = 0
        for col in numeric:
            if col not in df.columns:
                continue
            arr = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
            # NaN is the in-memory representation of a SQL NULL (valid when a
            # denominator is zero). Only +/-Inf is an invalid stored value.
            infinite += int(np.isinf(arr).sum())
        results.append(_result(
            f"GOLD_NUMERIC_{table.upper()}", f"No Inf in numeric columns: {table}",
            "Validity", table, "error",
            "No numeric gold value is infinite; NULL (NaN in pandas) is allowed for zero denominators.",
            infinite, max(1, len(df) * len(numeric)), run_id,
        ))

        rates = [c for c in RATE_COLUMNS.get(table, []) if c in df.columns]
        if rates:
            arr = df[rates].apply(pd.to_numeric, errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
            # nps/revenue_growth_pct are signed exceptions; collection_rate is
            # uncapped because cash can settle prior-period invoices but must
            # never be negative.
            exceptions = {"nps", "revenue_growth_pct", "collection_rate"}
            check_cols = [c for c in rates if c not in exceptions]
            bad_rates = 0
            if check_cols:
                sub = df[check_cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
                bad_rates = int(((sub < -1e-9) | (sub > 100 + 1e-9)).sum())
            if "collection_rate" in rates:
                cash = pd.to_numeric(df["collection_rate"], errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
                bad_rates += int((cash < -1e-9).sum())
            results.append(_result(
                f"GOLD_RATE_BOUNDS_{table.upper()}", f"Rate bounds 0..100: {table}",
                "Consistency", table, "error",
                "All percentage rates are within 0..100 except documented signed/growth "
                "exceptions; collection_rate is uncapped above 100 but non-negative.",
                bad_rates, max(1, int(np.isfinite(arr).sum())), run_id,
            ))

    # --- grain / continuity of the main workhorse -------------------------
    monthly = gold_tables.get("gold_hospital_monthly")
    if monthly is not None:
        bad = int(monthly.duplicated(subset=["hospital_id", "month"]).sum())
        results.append(_result(
            "GOLD_GRAIN_HOSPITAL_MONTHLY", "Hospital-month grain uniqueness",
            "Uniqueness", "gold_hospital_monthly", "error",
            "Exactly one row per (hospital_id, month).",
            bad, len(monthly), run_id,
        ))
        expected_rows = len(config.HOSPITALS) * 24
        results.append(_result(
            "GOLD_GRID_HOSPITAL_MONTHLY", "Continuous 10 hospitals x 24 months grid",
            "Completeness", "gold_hospital_monthly", "error",
            f"All {expected_rows} hospital-month combinations are present for continuous charts.",
            abs(len(monthly) - expected_rows), expected_rows, run_id,
        ))

    # --- analytical reconciliation ----------------------------------------
    daily = gold_tables.get("gold_network_daily")
    if monthly is not None and daily is not None:
        daily_enc = int(pd.to_numeric(daily["encounters"], errors="coerce").fillna(0).sum())
        monthly_enc = int(pd.to_numeric(monthly["encounters"], errors="coerce").fillna(0).sum())
        results.append(_result(
            "RECON_DAILY_MONTHLY_ENCOUNTERS", "Daily vs monthly encounter reconciliation",
            "Consistency", "gold_network_daily / gold_hospital_monthly", "error",
            "SUM(encounters) in daily and hospital-monthly models agree.",
            abs(daily_enc - monthly_enc), max(1, daily_enc), run_id,
            [f"daily={daily_enc}", f"monthly={monthly_enc}"],
        ))
    if monthly is not None:
        lab = gold_tables.get("gold_lab_performance")
        if lab is not None:
            m_lab = int(pd.to_numeric(monthly["lab_orders"], errors="coerce").fillna(0).sum())
            l_lab = int(pd.to_numeric(lab["orders"], errors="coerce").fillna(0).sum())
            results.append(_result(
                "RECON_LAB_ORDERS", "Lab order volume reconciliation",
                "Consistency", "gold_hospital_monthly / gold_lab_performance",
                "warning", "Total lab orders agree across gold models.",
                abs(m_lab - l_lab), max(1, m_lab), run_id,
                [f"monthly={m_lab}", f"lab={l_lab}"],
            ))
    return results


# ---------------------------------------------------------------------------
# Weighted score + persistence
# ---------------------------------------------------------------------------
def compute_score(results: list[dict[str, Any]]) -> dict[str, Any]:
    category_scores: dict[str, float] = {}
    category_details: dict[str, dict[str, Any]] = {}
    for category, weight in CATEGORY_WEIGHTS.items():
        rules = [r for r in results if r["category"] == category]
        if not rules:
            category_scores[category] = 100.0
            category_details[category] = {"weight": weight, "rules": 0, "score": 100.0}
            continue
        numerator = 0.0
        denominator = 0.0
        for rule in rules:
            checked = max(1, int(rule.get("checked_count", 1)))
            ratio = max(0.0, 1.0 - min(1.0, rule["failed_count"] / checked))
            w = SEVERITY_WEIGHTS.get(rule.get("severity", "warning"), 1.0)
            numerator += w * ratio
            denominator += w
        score = round(100.0 * numerator / denominator, 2) if denominator else 100.0
        category_scores[category] = score
        category_details[category] = {"weight": weight, "rules": len(rules), "score": score}

    overall = round(sum(CATEGORY_WEIGHTS[c] * category_scores[c] for c in CATEGORY_WEIGHTS), 2)
    return {
        "method": "severity-weighted rule ratios, then category-weighted mean",
        "formula": "score = SUM(weight_c * (SUM(sev_w * pass_ratio)/SUM(sev_w))) over categories; "
                   "weights are normalised to sum to 1.0",
        "category_weights": CATEGORY_WEIGHTS,
        "severity_weights": SEVERITY_WEIGHTS,
        "category_scores": category_scores,
        "category_details": category_details,
        "overall_score": overall,
    }


def write_results(
    results: list[dict[str, Any]],
    quarantine_records: list[dict[str, Any]],
    run_id: str,
) -> dict[str, Any]:
    """Write DQ JSON + parquet tables and return the complete DQ payload."""
    score = compute_score(results)
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    payload: dict[str, Any] = {
        "run_id": run_id,
        "generated_at": _now(),
        "framework": "HOSPITAL 360 documented DQ rule set",
        "rules": results,
        "summary": {
            "total_rules": len(results),
            "passed_rules": passed,
            "failed_rules": failed,
            "total_failures": int(sum(r["failed_count"] for r in results)),
            "total_rule_failures": int(sum(r["failed_count"] for r in results)),
            "quarantined_records": len(quarantine_records),
            "quarantine_rule_failures": len(quarantine_records),
            "quarantined_rows": len({r.get("source_row_key") for r in quarantine_records
                                     if r.get("source_row_key")}),
            "warning_failures": int(sum(r["failed_count"] for r in results
                                        if r["severity"] == "warning")),
        },
        "scoring": score,
        "dq_score": score["overall_score"],
    }

    manifest_path = Path(config.MANIFEST_DIR) / "dq_results.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    dq_dir = Path(config.SILVER_DIR) / "_dq"
    dq_dir.mkdir(parents=True, exist_ok=True)

    def norm(value: Any) -> Any:
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.bool_,)):
            return bool(value)
        if isinstance(value, (list, dict)):
            return json.dumps(value, default=str)
        if value is not None and pd.isna(value) and not isinstance(value, (list, dict)):
            return None
        return value

    rule_rows = []
    for r in results:
        rule_rows.append({
            "rule_id": r["rule_id"], "rule_name": r["rule_name"],
            "category": r["category"], "table_name": r["table"],
            "passed": bool(r["passed"]), "failed_count": int(r["failed_count"]),
            "severity": r["severity"], "description": r["description"],
            "checked_count": int(r.get("checked_count", 0)),
            "checked_at": pd.Timestamp(r["checked_at"]),
            "pipeline_run_id": run_id,
        })
    pd.DataFrame(rule_rows).to_parquet(dq_dir / "dq_rules.parquet", index=False)

    failure_rows = []
    for rec in quarantine_records:
        failure_rows.append({
            "failure_id": rec.get("quarantine_id"),
            "rule_id": rec.get("rule_id"),
            "table_name": rec.get("table"),
            "record_id": rec.get("record_id"),
            "failure_reason": rec.get("failure_reason"),
            "severity": rec.get("severity"),
            "detected_at": pd.Timestamp(rec.get("timestamp")),
            "pipeline_run_id": run_id,
            "source_file": rec.get("source_file"),
            "record_json": rec.get("record_json"),
        })
    if not failure_rows:
        failure_rows.append({
            "failure_id": None, "rule_id": None, "table_name": None,
            "record_id": None, "failure_reason": None, "severity": None,
            "detected_at": pd.Timestamp(_now()), "pipeline_run_id": run_id,
            "source_file": None, "record_json": None,
        })
    pd.DataFrame(failure_rows).to_parquet(dq_dir / "dq_failures.parquet", index=False)

    payload["dq_results_path"] = str(manifest_path)
    payload["dq_tables_path"] = str(dq_dir)
    return payload
