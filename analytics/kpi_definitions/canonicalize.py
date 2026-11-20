"""Apply and validate the single canonical KPI contract in ``kpis.json``.

Run with ``python -m analytics.kpi_definitions.canonicalize`` after changing any
KPI definition. The script is idempotent: it adds contract fields to the JSON
file without changing the array shape consumed by ``/kpis/glossary``.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.kpi_specs import SPECS

KPIS = ROOT / "analytics" / "kpi_definitions" / "kpis.json"
PAGES = ROOT / "web" / "lib" / "page-configs.ts"
DQ_PAGE = ROOT / "web" / "components" / "DataQualityPage.tsx"
PIPELINE_PAGE = ROOT / "web" / "components" / "PipelinePage.tsx"
SYSTEM_ROUTE = ROOT / "api" / "routes" / "system.py"
CONTRACT_VERSION = "phase2-kpi-integrity-v1"

SQL_KEYWORDS = {
    "and", "as", "asc", "by", "case", "cast", "count", "date", "date_diff", "date_part",
    "date_trunc", "desc", "distinct", "else", "end", "extract", "filter", "from", "greatest",
    "hour", "ilike", "in", "interval", "is", "least", "like", "lower", "minute", "month",
    "not", "null", "nullif", "or", "over", "round", "select", "sum", "then", "to", "when",
    "where", "with", "coalesce", "abs", "avg", "max", "min", "current_date", "partition",
    "order", "day", "integer", "varchar", "true", "false", "between", "lag", "regr_slope",
}

# Corrections to glossary pseudo-SQL that could not be executed as written.
FORMULA_FIXES: dict[str, str] = {
    "net_collections": "SUM(CASE WHEN LOWER(COALESCE(status,'')) = 'cleared' THEN COALESCE(amount,0) ELSE 0 END) - SUM(CASE WHEN LOWER(COALESCE(payment_type,'')) = 'refund' THEN ABS(COALESCE(amount,0)) ELSE 0 END)",
    "available_beds": "SUM(CASE WHEN NOT COALESCE(blocked_flag, FALSE) THEN 1 ELSE 0 END)",
    "average_discharge_time": "AVG(date_part('hour', discharge_datetime))",
    "procedure_turnaround_time": "AVG(date_diff('minute', actual_end, (SELECT MIN(s2.scheduled_start) FROM silver_procedures s2 WHERE s2.or_room = silver_procedures.or_room AND CAST(s2.scheduled_start AS DATE) = CAST(silver_procedures.scheduled_start AS DATE) AND s2.scheduled_start > silver_procedures.actual_end)))",
    "stockout_medication_count": "SUM(stockouts) FILTER (WHERE category = 'Pharmacy')",
    "total_collected": "SUM(CASE WHEN LOWER(COALESCE(status,'')) = 'cleared' THEN COALESCE(amount,0) ELSE 0 END)",
    "positive_feedback_percentage": "COUNT(*) FILTER (WHERE sentiment_label ILIKE '%Positive%') * 100.0 / NULLIF(COUNT(*), 0)",
    "negative_feedback_percentage": "COUNT(*) FILTER (WHERE sentiment_label ILIKE '%Negative%') * 100.0 / NULLIF(COUNT(*), 0)",
    "response_rate": "COUNT(*) FILTER (WHERE resolution_status IS NOT NULL AND resolution_status <> '') * 100.0 / NULLIF(COUNT(*), 0)",
    "revenue_per_hospital_department": "SUM(net_amount) OVER (PARTITION BY hospital_id, department_id)",
    "revenue_per_hospital": "SUM(net_amount) / NULLIF(COUNT(DISTINCT hospital_id), 0)",
    "supplier_delivery_performance": "SUM(supplier_on_time_rate * inventory_value) / NULLIF(SUM(inventory_value), 0)",
    "supplier_delivery": "SUM(supplier_on_time_rate * inventory_value) / NULLIF(SUM(inventory_value), 0)",
    "absence_rate": "SUM(absence_rate * headcount) / NULLIF(SUM(headcount), 0)",
    "shift_coverage": "SUM(coverage_pct * headcount) / NULLIF(SUM(headcount), 0)",
    "staffing_shortage": "SUM(CASE WHEN coverage_pct < 100 THEN 1 ELSE 0 END)",
    "open_staffing_gaps": "SUM(GREATEST(100 - coverage_pct, 0) / 100.0)",
    "expiring_items": "COUNT(DISTINCT item_id) FILTER (WHERE CAST(expiry_date AS DATE) <= CAST($date_to AS DATE) + INTERVAL '90' DAY)",
    "no_show_rate": "COUNT(*) FILTER (WHERE status = 'No-show') * 100.0 / NULLIF(COUNT(*) FILTER (WHERE status IN ('Completed','No-show')), 0)",
}

CAVEAT_FIXES: dict[str, str] = {
    "total_patients": "Distinct patients are not additive across months; summing monthly gold values double-counts returning patients.",
    "total_revenue": "Gross revenue is not net revenue. `revenue` is a separate net measure and is no longer an alias of this KPI.",
    "revenue": "Net revenue is not cash collected. This is the only meaning of the response key `revenue`.",
    "collection_rate": "Uncapped: values above 100% are valid when prior-period balances are collected and are flagged, never clipped. NULL/zero denominator -> NULL.",
    "patient_satisfaction": "Percent scale: AVG(rating)/5*100 with rating on a 1-5 scale. `average_satisfaction` is the raw score.",
    "average_satisfaction": "Score scale 1-5. It is never emitted as an alias of the percentage `patient_satisfaction`.",
    "average_satisfaction_score": "Deprecated display alias of `average_satisfaction`; same 1-5 score unit.",
    "satisfaction_percentage": "Percent alias of `patient_satisfaction`; AVG(rating)/5*100.",
    "average_investigation_time": "Canonical ID. Incidents without investigation_days are excluded from both numerator and weight.",
    "avg_investigation_time": "Deprecated short alias of `average_investigation_time`; same formula and unit.",
    "writeoff_amount": "Uses the documented overdue-balance proxy; no separate write-off source column exists in the generated data.",
    "hospitals_selected": "Dimension snapshot: no date filter is applied because dim_hospital has no date column.",
    "total_beds": "Dimension snapshot: no date filter is applied because dim_hospital has no date column.",
    "active_employees": "Dimension snapshot: no date filter is applied because silver_dim_staff has no date column.",
}

DATE_FIXES: dict[str, str] = {
    "hospitals_selected": "",
    "total_beds": "",
    "active_employees": "",
}

KNOWN_BAD_FORMULAS = set(FORMULA_FIXES) | {"revenue_per_hospital_department"}
SYSTEM_TABLE_HINTS = ("manifest", "pipeline_runs", "dq_failures", "dq_results", "quarantine")


def _api_consumers() -> tuple[dict[str, set[str]], dict[str, str]]:
    producers: dict[str, set[str]] = defaultdict(set)
    alias_to_canonical: dict[str, str] = {}
    for endpoint, specs in SPECS.items():
        for spec in specs:
            producers[spec.id].add(endpoint)
            for alias in spec.aliases:
                alias_to_canonical[alias] = spec.id
                producers[alias].add(endpoint)
    system = SYSTEM_ROUTE.read_text(encoding="utf-8")
    for key in re.findall(r'_card\(\s*"([^"]+)"', system):
        producers[key].add("system")
    return producers, alias_to_canonical


def _frontend_consumers() -> dict[str, set[str]]:
    consumers: dict[str, set[str]] = defaultdict(set)
    for path in (PAGES, DQ_PAGE, PIPELINE_PAGE):
        text = path.read_text(encoding="utf-8")
        blocks = re.findall(r"kpiIds:\s*\[(.*?)\]", text, re.DOTALL)
        blocks += re.findall(r"(?:DQ_KPI_IDS|PIPELINE_KPI_IDS)\s*=\s*\[(.*?)\]", text, re.DOTALL)
        for block in blocks:
            for key in re.findall(r"['\"]([a-z0-9_]+)['\"]", block):
                consumers[key].add(path.stem)
    return consumers


def _source_columns(formula: str, date_field: str) -> list[str]:
    tokens = re.findall(r"\b[a-z_][a-z0-9_]*\b", formula.lower())
    columns: list[str] = []
    for token in tokens:
        if (
            token in SQL_KEYWORDS
            or token.startswith(("silver_", "gold_", "dim_", "$"))
            or token in {"s2", "h", "i", "p", "e", "b"}
            or token in columns
        ):
            continue
        columns.append(token)
    date_column = date_field.split(".")[-1] if date_field else ""
    if date_column and date_column not in columns:
        columns.append(date_column)
    return columns


def _aggregation(formula: str) -> str:
    lowered = formula.lower()
    if "count(distinct" in lowered.replace(" ", ""):
        return "distinct count"
    if "/" in formula and any(k in lowered for k in ("nullif", "* 100")):
        return "weighted average / ratio"
    if "avg(" in lowered or "regr_slope" in lowered:
        return "average"
    if "count(" in lowered:
        return "count"
    if "sum(" in lowered:
        return "sum"
    if "/" in formula:
        return "ratio"
    return "descriptive"


def _additivity(aggregation: str, unit: str) -> str:
    if aggregation == "distinct count":
        return "semi-additive; not additive across months or overlapping dimensions"
    if aggregation in {"sum", "count"}:
        return "additive over disjoint periods and dimensions"
    if unit in {"percent", "score", "days", "minutes", "hours", "ratio", "currency"}:
        return "non-additive; recompute numerator and denominator after aggregation"
    return "non-additive; recompute from source rows"


def _expected_range(kpi: dict[str, Any]) -> str:
    unit = kpi["unit"].lower()
    if unit in {"count", "integer"}:
        return ">= 0"
    if unit == "currency":
        return ">= 0 for revenue/collection measures; refunds and adjustments may be negative"
    if unit == "percent":
        if kpi["id"] == "collection_rate":
            return ">= 0, unbounded above; >100 flagged for prior-period cash"
        if kpi["id"] == "net_promoter_score" or kpi["id"] == "nps":
            return "-100..100"
        return "0..100"
    if unit == "score":
        return "-100..100 for NPS; 1..5 for ratings"
    if unit in {"days", "minutes", "hours", "ratio"}:
        return ">= 0"
    return "documented per KPI"


def _null_handling(kpi: dict[str, Any]) -> str:
    denominator = str(kpi.get("denominator") or "")
    formula = str(kpi.get("formula") or "")
    if denominator and denominator not in {"5", "60"}:
        return "NULL when denominator is 0 or NULL; NULL inputs excluded from numerator and weight."
    if denominator in {"5", "60"}:
        return "NULL when no rows; denominator is the model constant " + denominator + "."
    if "/" in formula:
        return "NULL when denominator is 0 or NULL (NULLIF in executable specs)."
    return "NULL source values ignored by SQL aggregates; result NULL when no rows match."


def _precision(kpi: dict[str, Any]) -> int:
    return 0 if kpi["unit"].lower() in {"count", "integer"} else 2


def _filter_behavior(kpi: dict[str, Any]) -> str:
    if not kpi.get("date_field"):
        return "No date filter (dimension snapshot). Hospital/department filters still apply where the column exists."
    return (
        "Global start/end date, hospital and department filters applied by the API allowlist; "
        "the frontend never filters business values. " + str(kpi.get("exclusions") or "")
    )


def _findings(
    kpi: dict[str, Any],
    duplicate_names: Counter[str],
    producers: dict[str, set[str]],
    consumers: dict[str, set[str]],
) -> list[str]:
    findings: list[str] = []
    if duplicate_names[kpi["name"]] > 1:
        findings.append("Duplicate display name; disambiguated by canonical ID and unit.")
    if kpi["id"] in KNOWN_BAD_FORMULAS:
        findings.append("Glossary pseudo-SQL was corrected to executable form.")
    if "/" in str(kpi.get("formula") or "") and "NULLIF" not in str(kpi.get("formula") or ""):
        findings.append("Formula text lacks an explicit NULLIF; executable specs use NULLIF.")
    source = " ".join(kpi.get("source_tables") or []).lower()
    if any(hint in source for hint in SYSTEM_TABLE_HINTS):
        findings.append("Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes.")
    if kpi["id"] not in producers and kpi["id"] not in consumers:
        findings.append("No backend producer and no frontend card; retained and recorded, not deleted.")
    elif kpi["id"] not in producers:
        findings.append("Frontend card has no matching API key; contract test must fail.")
    elif kpi["id"] not in consumers:
        findings.append("Backend producer has no explicit frontend card (chart/table or API-only consumer).")
    if kpi.get("date_field") and kpi["date_field"].split(".")[0] in {"dim_hospital", "silver_dim_staff"}:
        findings.append("Invalid date column reference corrected to a dimension snapshot.")
    return findings


def _status(kpi: dict[str, Any], producers: dict[str, set[str]], consumers: dict[str, set[str]]) -> str:
    if kpi.get("alias_of"):
        return "alias"
    if kpi["id"] not in producers and kpi["id"] not in consumers:
        return "unused_definition_documented"
    if kpi["id"] not in producers:
        return "frontend_only_invalid"
    if kpi["id"] not in consumers:
        return "api_only"
    return "active"


def main() -> None:
    definitions = json.loads(KPIS.read_text(encoding="utf-8"))
    producers, alias_to_canonical = _api_consumers()
    consumers = _frontend_consumers()
    duplicate_names = Counter(item["name"] for item in definitions)
    by_name: dict[str, list[str]] = defaultdict(list)
    for item in definitions:
        by_name[item["name"]].append(item["id"])

    known_ids = {item["id"] for item in definitions}
    for alias, canonical in alias_to_canonical.items():
        if canonical not in known_ids:
            raise SystemExit(f"API alias {alias!r} points at unknown canonical KPI {canonical!r}")

    for kpi in definitions:
        key = kpi["id"]
        if key in CAVEAT_FIXES:
            kpi["caveat"] = CAVEAT_FIXES[key]
        if key in FORMULA_FIXES:
            kpi["formula"] = FORMULA_FIXES[key]
        if key in DATE_FIXES:
            kpi["date_field"] = DATE_FIXES[key]

        kpi["contract_version"] = CONTRACT_VERSION
        kpi["display_name"] = kpi["name"]
        kpi["formula_sql"] = kpi["formula"]
        kpi["date_column"] = kpi["date_field"].split(".")[-1] if kpi.get("date_field") else ""
        kpi["source_columns"] = _source_columns(kpi["formula"], kpi.get("date_field", ""))
        kpi["aggregation_method"] = _aggregation(kpi["formula"])
        kpi["filter_behavior"] = _filter_behavior(kpi)
        kpi["units"] = kpi["unit"]
        kpi["decimal_precision"] = _precision(kpi)
        kpi["null_handling"] = _null_handling(kpi)
        kpi["additivity"] = _additivity(kpi["aggregation_method"], kpi["unit"])
        kpi["expected_range"] = _expected_range(kpi)
        kpi["business_interpretation"] = (
            f"{kpi['business_definition']} Reported in {kpi['unit']} at {kpi.get('grain', 'the documented grain')}."
        )
        kpi["alias_of"] = alias_to_canonical.get(key)
        aliases = sorted(a for a, c in alias_to_canonical.items() if c == key)
        aliases += [other for other in by_name[kpi["name"]] if other != key and other not in aliases]
        kpi["aliases"] = sorted(set(aliases))
        kpi["same_definition_as"] = [
            other for other in by_name[kpi["name"]] if other != key and other not in alias_to_canonical
        ]
        kpi["api_endpoints"] = sorted(producers.get(key, set()))
        kpi["frontend_consumers"] = sorted(consumers.get(key, set()))
        kpi["consumer_status"] = _status(kpi, producers, consumers)
        kpi["audit_findings"] = _findings(kpi, duplicate_names, producers, consumers)
        kpi["last_reviewed"] = "2026-11-20 Phase 2 KPI and Analytics Integrity"

    KPIS.write_text(json.dumps(definitions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    statuses = Counter(item["consumer_status"] for item in definitions)
    print(f"Canonicalised {len(definitions)} KPI definitions ({CONTRACT_VERSION}).")
    print("Consumer status:", dict(sorted(statuses.items())))


if __name__ == "__main__":
    main()
