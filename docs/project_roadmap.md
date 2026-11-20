# HOSPITAL 360 - Project Roadmap

The 16 phases from blueprint section 27, in the mandated build order. Status markers are a
snapshot of this repository at the time the documentation/testing layer was added; source
layers are being implemented in parallel, so re-check the code before quoting status to a
reviewer. **No measured result is claimed here** - run the pipeline and tests first.

**Legend:** 🟢 Implemented / verifiable in repo · 🟡 In progress or partially implemented ·
⚪ Not started in this snapshot

---

## 🟡 Phase 1 - Project foundation
Tasks: GitHub repository, project folder, Python environment, Next.js, FastAPI, DuckDB,
Tailwind, initial README, project structure.
Deliverable: application skeleton running locally.
Status: project structure, `CONTRACT.md`, environment files, Docker/CI configuration and
README are present; verify the Next.js skeleton builds before marking complete.

## 🟢 Phase 2 - Business requirements and data model
Tasks: define entities, IDs, table grains, ERD, relationships, KPI dictionary, business
rules, generation profiles.
Deliverable: approved data model.
Status: `generator/schema.py` (39 tables), `CONTRACT.md`, [erd.md](erd.md),
[data_dictionary.md](data_dictionary.md) and [kpi_glossary.md](kpi_glossary.md) exist.

## 🟡 Phase 3 - Reference data
Generate hospitals, departments, doctors, staff, specialties, payers, diagnoses,
procedures, medications, lab tests, inventory items, suppliers, beds.
Deliverable: consistent reference tables.
Status: hospital profile definitions live in `generator/config.py`; generation modules are
being completed in parallel.

## 🟡 Phase 4 - Patient and appointment system
Generate patients, appointments, encounters; implement booking, cancellation, no-show,
completed, check-in, waiting time and encounter relationships.
Deliverable: appointment analytics dataset.

## 🟡 Phase 5 - Inpatient operations
Generate admissions, discharges, transfers, bed snapshots; implement LOS, occupancy, bed
turnover and readmission logic.
Deliverable: inpatient analytics.

## 🟡 Phase 6 - Procedures and diagnostics
Generate procedures, OR schedules, lab orders/results; implement duration, cancellation,
OR utilisation, turnaround and SLA.
Deliverable: procedures and diagnostic analytics.

## 🟡 Phase 7 - Pharmacy and finance
Generate prescriptions, dispensing, invoices, invoice lines, payments; implement revenue,
collections, outstanding balances and medication revenue.
Deliverable: finance and pharmacy analytics.

## 🟡 Phase 8 - Insurance
Generate claims, claim lines, claim events, denials, appeals; implement denial rate,
processing time, claim aging, approved and paid amounts.
Deliverable: revenue cycle analytics.

## 🟡 Phase 9 - Workforce and inventory
Generate shifts, attendance, inventory movements, purchase orders; implement coverage,
overtime, absence, stock availability, expiry and procurement.
Deliverable: operational analytics.

## 🟡 Phase 10 - Patient experience and quality
Generate feedback, complaints, incidents; implement satisfaction, feedback trends, incident
categories and resolution metrics.
Deliverable: quality and experience analytics.

## 🟡 Phase 11 - Data engineering
Implement bronze ingestion, silver cleaning, gold transformations, DuckDB models, Parquet
storage, manifest, pipeline runs and quarantine.
Deliverable: reproducible ETL pipeline.
Status: pipeline implementation in parallel; tests in `tests/test_silver.py` and
`tests/test_gold.py` are ready and skip gracefully until data exists.

## 🟡 Phase 12 - Backend
Implement API routes, KPI services, SQL repositories, validation, filters, pagination,
exports and error handling.
Deliverable: working analytics API.
Status: `api/core` (config, DB access, filters, response envelopes) is present; route
implementation continues in parallel. Endpoint catalogue is in [api.md](api.md).

## ⚪ Phase 13 - Frontend core
Build reusable components: sidebar, header, filter bar, KPI cards, charts, tables, drawers,
tooltips, loading/empty/error states.
Deliverable: design system and dashboard framework.

## ⚪ Phase 14 - Main pages
Build all 21 pages in blueprint order: Network Overview, Hospital Comparison, Hospital
Profile, Appointments, Inpatient, Finance, Claims, Emergency, Diagnostics, Procedures,
Pharmacy, Workforce, Inventory, Patient Experience, Quality, Data Explorer, Patient
Journey, Data Quality, Pipeline, KPI Glossary, Methodology.
Deliverable: all pages functional.

## 🟢 Phase 15 - Testing
Generator tests, data quality tests, KPI tests, API tests, frontend tests, integration
tests, end-to-end tests.
Deliverable: validated application.
Status: this layer adds `tests/conftest.py`, `test_generator.py`, `test_silver.py`,
`test_gold.py`, `test_kpis.py`, `test_api.py`, `tests/e2e/analytics.spec.ts`,
`pytest.ini` and the Playwright config. Data-dependent suites skip until the pipeline has
run. Full integration results must be filled in after execution.

## 🟢 Phase 16 - Deployment
GitHub, Docker, frontend deployment, backend deployment, environment variables, API
connection, dataset availability, health checks.
Deliverable: live application.
Status: `Dockerfile.api`, `Dockerfile.web`, `docker-compose.yml`, `.dockerignore` and
`.github/workflows/ci.yml` are written; [deployment.md](deployment.md) documents the
remaining hosting steps. A live URL is not yet verified.

---

## Acceptance checklist pointer

The blueprint's final acceptance checklist (section 31) spans dataset, data engineering,
analytics, backend, frontend, testing and deployment. Track it in the project README's
"Project status" section and fill measured values with the `<!-- FILL AFTER RUN -->`
placeholders only after the pipeline and tests have actually run.
