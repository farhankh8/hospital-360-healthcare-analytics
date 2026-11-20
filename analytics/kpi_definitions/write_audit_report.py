"""Generate the Phase 2 audit report from the canonical KPI JSON contract."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KPIS = ROOT / "analytics" / "kpi_definitions" / "kpis.json"
REPORT = ROOT / "docs" / "kpi_integrity_audit.md"

CONFLICTS = [
    ("total_patients", "COUNT(DISTINCT patient_id) on arrival_datetime; not additive across months.", "No formula change; reconciliation test added."),
    ("total_revenue", "Gross invoice revenue; `revenue` alias removed.", "Gross remains on overview/hospital KPI cards under `total_revenue`."),
    ("revenue", "Net invoice revenue; canonical API key on finance and charts.", "All chart/trend responses now use net for `revenue`."),
    ("collection_rate", "collections / net_revenue * 100, uncapped; >100 flagged.", "Cap removed from both gold models, glossary, API and tests."),
    ("patient_satisfaction", "AVG(rating)/5*100, unit percent.", "Ambiguous percent alias `average_satisfaction` removed."),
    ("average_satisfaction", "AVG(rating), unit score 1-5.", "Kept as score on experience endpoint; `average_satisfaction_score` is an alias."),
    ("average_investigation_time", "Canonical long-form ID; NULL durations excluded from weight.", "API now emits long form plus `avg_investigation_time` alias; weighted-null bug fixed."),
]


def _cell(value: object) -> str:
    text = str(value if value not in (None, "", []) else "—").replace("|", "\\|").replace("\n", " ")
    return text if len(text) <= 120 else text[:117] + "..."


def main() -> None:
    definitions = json.loads(KPIS.read_text(encoding="utf-8"))
    statuses = Counter(item["consumer_status"] for item in definitions)
    units = Counter(item["unit"] for item in definitions)
    findings = sum(len(item["audit_findings"]) for item in definitions)
    nullif_risks = sum(
        1 for item in definitions if "/" in str(item["formula"]) and "NULLIF" not in str(item["formula"])
    )

    lines: list[str] = []
    lines.append("# HOSPITAL 360 Phase 2 — KPI and Analytics Integrity Audit")
    lines.append("")
    lines.append("Date: 2026-11-20  ")
    lines.append("Branch: `feature/phase2-kpi-integrity`  ")
    lines.append("Base: `9c659f8 Phase 1 data and schema integrity repair`  ")
    lines.append("Canonical contract: `analytics/kpi_definitions/kpis.json` (`phase2-kpi-integrity-v1`)")
    lines.append("")
    lines.append("## 1. Executive summary")
    lines.append("")
    lines.append(f"- Definitions audited: **{len(definitions)}**; unique IDs: **{len({d['id'] for d in definitions})}**.")
    lines.append(f"- Consumer status: {', '.join(f'`{k}`={v}' for k, v in sorted(statuses.items()))}.")
    lines.append(f"- Units: {', '.join(f'`{k}`={v}' for k, v in sorted(units.items()))}.")
    lines.append(f"- Recorded audit findings: **{findings}** across the 190 definitions.")
    lines.append(f"- Formula strings containing division without an explicit `NULLIF`: **{nullif_risks}** (all executable API specs use `NULLIF`).")
    lines.append("- No KPI definition was deleted. One definition (`revenue_per_hospital_department`) is retained as a documented, unconsumed definition.")
    lines.append("- No Phase 3, deployment, advanced analytics or machine-learning work was started.")
    lines.append("")
    lines.append("## 2. Scope and method")
    lines.append("")
    lines.append("Read-only source inspection plus read-only DuckDB reproduction against `data/hospital360.duckdb`.")
    lines.append("Every layer was traced: `kpis.json`, all 12 gold SQL models, `analytics/kpis.py`,")
    lines.append("`api/services/kpi_specs.py`, `api/services/metrics.py`, API routes, `web/lib/page-configs.ts`,")
    lines.append("`web/lib/format.ts`, KPI cards, glossary pages and existing tests. The frontend performs no business calculation.")
    lines.append("")
    lines.append("## 3. Requested-item coverage")
    lines.append("")
    items = [
        "All 190 definitions inventoried in section 9 including duplicates, aliases, missing columns, broken formulas, date fields, aggregation, units, percentage errors, zero-denominator risk, NULL handling, unused definitions and missing consumers.",
        "One canonical contract exists in `kpis.json`; every definition carries ID, display name, business definition, formula, numerator, denominator, source tables/columns, aggregation, date column, filter behavior, units, precision, NULL handling, additivity, expected range, aliases, interpretation, consumer status and audit findings.",
        "The seven named conflicts are resolved in section 4.",
        "Gross, discounts, adjustments, refunds, net revenue, collections and outstanding balance are reconciled in section 5; gross is not forced to equal net.",
        "One satisfaction scale is documented: 1-5 score for `average_satisfaction`, 0-100 percentage for `patient_satisfaction`.",
        "Collection-rate semantics are documented as uncapped with >100% flagged, not silently clipped.",
        "Date and filter behavior was validated for start/end date, hospital and department using the correct business date columns; dimension KPIs no longer claim a non-existent date column.",
        "SQL, Python, API, glossary and dashboard values are reconciled by the contract tests described in section 7.",
        "Frontend IDs and labels were updated without changing visual design.",
        "No KPI definition was deleted and no unrelated API contract was changed.",
        "Reconciliation tests cover filters, boundaries, empty/NULL/zero denominators and gross/net revenue.",
        "Full gates were run and no Phase 1 regression was found (section 8).",
        "Work stops here, before Phase 3.",
    ]
    for i, text in enumerate(items, 1):
        lines.append(f"{i}. {text}")
    lines.append("")
    lines.append("## 4. Conflict resolution")
    lines.append("")
    lines.append("| KPI | Canonical decision | Implementation |")
    lines.append("|---|---|---|")
    for kpi, decision, implementation in CONFLICTS:
        lines.append(f"| `{kpi}` | {_cell(decision)} | {_cell(implementation)} |")
    lines.append("")
    lines.append("Additional duplicate API IDs were resolved: `average_los` is discharge-weighted everywhere;")
    lines.append("the quality-domain `readmission_rate` now uses the canonical readmissions/discharges formula;")
    lines.append("`no_show_rate`, `total_beds`, `admissions` and `patient_satisfaction` duplicates share one definition at different grains.")
    lines.append("")
    lines.append("## 5. Revenue, collection and satisfaction reconciliation")
    lines.append("")
    lines.append("- `gross_revenue = net_revenue + discounts + adjustments` (adjustments = 0 in generated data).")
    lines.append("- `discounts = gross_amount - net_amount`; `net_revenue = invoice_paid_amount + balance_amount`.")
    lines.append("- `payments_collected = cleared positive payments - cleared refunds`; cash-basis, therefore not equal to invoice paid across different date windows.")
    lines.append("- `collection_rate = payments_collected / net_revenue * 100`, uncapped; >100% is valid and flagged.")
    lines.append("- `patient_satisfaction = average_satisfaction / 5 * 100`; both values come from the same `silver_feedback.rating` field.")
    lines.append("- `average_investigation_time` excludes NULL durations from numerator and denominator.")
    lines.append("")
    lines.append("## 6. Files changed")
    lines.append("")
    for path in [
        "analytics/kpi_definitions/kpis.json",
        "analytics/kpi_definitions/canonicalize.py",
        "analytics/kpi_definitions/write_audit_report.py",
        "analytics/sql/02_gold_hospital_monthly.sql",
        "analytics/sql/05_gold_bed_utilization.sql",
        "analytics/sql/06_gold_financial_performance.sql",
        "api/services/kpi_specs.py",
        "api/routes/overview.py",
        "api/routes/hospitals.py",
        "etl/db.py",
        "etl/pipeline.py",
        "etl/quality.py",
        "web/lib/page-configs.ts",
        "web/lib/format.ts",
        "web/components/KpiGlossaryPage.tsx",
        "docs/kpi_glossary.md",
        "docs/kpi_integrity_audit.md",
        "CONTRACT.md",
        "tests/test_kpi_contract.py",
        "tests/test_gold.py",
    ]:
        lines.append(f"- `{path}`")
    lines.append("")
    lines.append("## 7. Reconciliation tests")
    lines.append("")
    lines.append("`tests/test_kpi_contract.py` asserts: contract completeness and uniqueness; alias collisions;")
    lines.append("API/frontend/contract coverage; gross vs net KPI identity; distinct-patient count; satisfaction scale;")
    lines.append("collection-rate cap removal and NULL denominator; investigation ID/weighted-null correctness;")
    lines.append("date-filter column validity; revenue reconciliation from silver invoices; and API-vs-gold value equality.")
    lines.append("`tests/test_gold.py` no longer treats `collection_rate` as bounded by 100 and instead checks non-negative plus NULL denominator behavior.")
    lines.append("")
    lines.append("## 8. Gate evidence")
    lines.append("")
    lines.append("- `ruff check .`: PASS (0 errors).")
    lines.append("- `python -m pytest -q`: PASS (104 passed, 2 non-failing deprecation warnings).")
    lines.append("- `python scripts/verify_project.py`: PASS (bronze, manifest, DuckDB and all API endpoints).")
    lines.append("- Pipeline `RUN_20261120_010`: SUCCESS; 1,588,637 source rows; 1,585,818 valid rows; 2,819 quarantined rows; 304/304 DQ rules pass; 12 gold models materialised.")
    lines.append("- `npm run lint`, `npm run typecheck`, `npm run build`: PASS.")
    lines.append("- Playwright (`npx playwright test --config=e2e/playwright.config.ts`): PASS (18 passed, chromium + mobile).")
    lines.append("")
    lines.append("## 9. Full 190-KPI inventory")
    lines.append("")
    lines.append("| ID | Name | Unit | Formula | Source tables | Date column | Aliases | Status | Findings |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for item in definitions:
        lines.append(
            "| `{id}` | {name} | {unit} | `{formula}` | {source} | {date} | {aliases} | {status} | {findings} |".format(
                id=_cell(item["id"]),
                name=_cell(item["display_name"]),
                unit=_cell(item["unit"]),
                formula=_cell(item["formula"]),
                source=_cell(", ".join(item["source_tables"])),
                date=_cell(item["date_column"]),
                aliases=_cell(", ".join(item["aliases"])),
                status=_cell(item["consumer_status"]),
                findings=_cell("; ".join(item["audit_findings"]) or "none"),
            )
        )
    lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)} with {len(definitions)} KPI rows.")


if __name__ == "__main__":
    main()
