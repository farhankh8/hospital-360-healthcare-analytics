# HOSPITAL 360 - Project Roadmap

Status against the 16 phases in blueprint section 27, verified from the current repository and
local run `RUN_20261120_005`. Results below are measured, not targets.

**Legend:** 🟢 Complete and verified · 🟡 Implemented but externally unverified · ⚪ Not started

---

## 🟢 Phase 1 - Project foundation

GitHub repository, project structure, Python environment, Next.js, FastAPI, DuckDB, Tailwind,
README, Docker and CI configuration all exist. `python scripts/verify_project.py` passes.

## 🟢 Phase 2 - Business requirements and data model

`generator/schema.py` defines 41 tables with explicit grains. `CONTRACT.md`,
[erd.md](erd.md), [data_dictionary.md](data_dictionary.md) and [kpi_glossary.md](kpi_glossary.md)
document the model.

## 🟢 Phase 3 - Reference data

10 hospitals, 120 departments, 690 doctors, 2,980 staff, 18 specialties, 6 payers, 45
diagnoses, 44 procedures, 52 medications, 38 lab tests, 122 inventory items, 20 suppliers and
3,450 beds were generated with distinct hospital profiles.

## 🟢 Phase 4 - Patient and appointment system

15,240 source patients, 136,800 appointments and 82,000 encounters generated; booking,
cancellation, no-show, completion, check-in and waiting-time fields are present in silver/gold
models.

## 🟢 Phase 5 - Inpatient operations

24,804 admissions, 3,600 transfers and 102,000 bed snapshots generated; LOS, occupancy, bed
turnover and readmission logic are implemented in SQL models and KPI specs.

## 🟢 Phase 6 - Procedures and diagnostics

31,000 procedures, 106,000 lab orders and 156,592 lab results generated; duration,
cancellation, OR utilisation, turnaround and SLA metrics are implemented.

## 🟢 Phase 7 - Pharmacy and finance

53,000 prescriptions, 53,000 dispensing records, 66,000 invoices, 138,729 invoice lines and
78,884 payments generated; revenue, collections, balances and medication revenue are in the
finance models.

## 🟢 Phase 8 - Insurance

52,000 claims, 104,002 claim lines and 179,238 claim events generated; denial rate, processing
time, aging, approved and paid amounts are implemented.

## 🟢 Phase 9 - Workforce and inventory

52,000 shifts, 52,000 attendance records, 52,000 inventory movements and 5,200 purchase orders
generated; coverage, overtime, absence, stock availability, expiry and procurement are
implemented.

## 🟢 Phase 10 - Patient experience and quality

15,600 feedback records and 4,200 incidents generated; satisfaction, feedback trends, incident
categories and resolution metrics are implemented.

## 🟢 Phase 11 - Data engineering

Bronze CSVs, silver Parquet with quarantine, gold Parquet, 76 DuckDB tables, 12 gold models,
304 DQ rules and manifests are present. Current run: `RUN_20261121_001`,
1,588,637 source / 1,585,844 valid / 2,793 quarantined rows / 2,833 rule-failure records,
DQ score **100.00 / 100**.

## 🟢 Phase 12 - Backend

FastAPI `/api/v1` exposes 206 GET endpoints, including 118 chart endpoints, allowlisted
filters, pagination, CSV export, error handling, data-quality and pipeline introspection.
All verifier API checks pass.

## 🟢 Phase 13 - Frontend core

Sidebar, header, filter bar, KPI cards, ECharts containers, tables, drill-down drawer,
tooltips, loading/empty/error states, responsive layout and accessibility basics are
implemented in `web/components/`.

## 🟢 Phase 14 - Main pages

All 21 blueprint pages are implemented and smoke-tested in Chromium and mobile viewports.
Every page renders without uncaught browser errors.

## 🟢 Phase 15 - Testing

87 pytest tests pass; 18 Playwright tests pass (9 cases × Chromium/mobile), covering the §28
journey, no-data/API-failure/invalid-filter/large-range/empty/mobile/refresh/back/export/
compare cases and all 21 routes. Ruff, lint, type-check and build are clean.

## 🟡 Phase 16 - Deployment

`Dockerfile.api`, `Dockerfile.web`, `docker-compose.yml`, environment configuration and
[deployment.md](deployment.md) are present. The GitHub repository uses `main`, `develop` and
feature branches. A public live URL is not yet verified; the application is currently verified
only on the local stack.

---

## Blueprint §31 acceptance status

- **Dataset:** all items verified; 1,588,637 records, 10 hospitals, 15,200 unique patients, 24 months.
- **Data engineering:** all items verified.
- **Analytics:** KPI definitions, calculations, SQL models, comparisons and no-double-counting
  grains implemented; some operational KPIs are documented proxies where source systems do not
  contain direct measures.
- **Backend:** versioning, KPI/chart/detail routes, filters, pagination, exports, errors and
  validation verified.
- **Frontend:** 21 pages, connected KPIs/charts/filters/tables, drill-downs, search, export,
  states, responsiveness and accessibility basics verified.
- **Testing:** unit, data, API, integration and end-to-end suites verified.
- **Deployment:** GitHub and Docker configuration complete; frontend/backend deployed to a
  public URL and live-URL verification remain external steps.
