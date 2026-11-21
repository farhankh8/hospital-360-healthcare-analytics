# HOSPITAL 360 - Case Study

## Problem
Hospital leadership needs a unified view across fragmented HIS/EMR/scheduling/lab/pharmacy/billing/claims/HR/inventory/feedback systems. Manual reconciliation makes it hard to compare hospitals, explain KPI changes, and trace metrics to records.

## Solution
HOSPITAL 360 is a synthetic, end-to-end healthcare analytics platform: deterministic data generation, Bronze/Silver/Gold ETL into DuckDB, FastAPI analytical API, and a 21-page Next.js dashboard. All business KPIs are computed/served by the API; the frontend renders and drills down.

## Architecture
- **Generation**: Seeded Faker/NumPy/pandas generator, 10 hospital profiles, 24-month window, controlled DQ issues, manifest reconciliation.
- **ETL**: Bronze CSV -> Silver cleaned/quarantined Parquet -> Gold aggregates -> DuckDB.
- **API**: FastAPI `/api/v1`, allowlisted filters, parameterized SQL, pagination, CSV exports, DQ/pipeline/explorer/journey endpoints, consistent envelope.
- **Frontend**: Next.js/React/TypeScript/Tailwind/ECharts/TanStack Table; global URL filters; KPI cards/charts/tables/drilldowns/exports.

## Key outcomes (measured local run)
- Seed 42: 1,588,637 source records; 1,585,844 valid; 2,793 quarantined; DQ score 100.0/100.
- 21 blueprint pages implemented with drilldown/export/filter flows.
- Automated checks: pytest 159 passed, ruff pass, web lint/tsc/build pass, Playwright 30 passed.

## Data quality and trust
- DQ rules cover completeness/validity/uniqueness/consistency/referential/date checks; failures quarantined with rule IDs.
- KPI glossary documents formula, numerator/denominator, unit, grain, caveats, and sources.
- UI shows explicit loading/empty/error states; no fabricated KPI values.

## Limitations
- Entirely synthetic educational project; not for clinical use or real patient data.
- Some blueprint interactions are represented by drilldown/filter context rather than dedicated subpages.
- Deployment prep only in this phase; no live deployment performed.
