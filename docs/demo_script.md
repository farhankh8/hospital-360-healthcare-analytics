# HOSPITAL 360 - Demo Script (3-5 minutes)

## Setup
- API: `uvicorn api.main:app --port 8000`
- Web: `cd web && npm run dev` (or `npm run start` after build)
- Data: seed 42 generated, ETL loaded into DuckDB.

## Minute 1 - Executive overview
1. Open `/overview`. Show network KPIs, trends, hospital ranking, heatmap, and global filters.
2. Change date range/hospital filter; show KPIs/charts/tables update from API. Toggle compare period.
3. Call out synthetic-data disclaimer and "API is single source of truth for KPIs".

## Minute 2 - Investigate an operations issue
1. Go to `/hospitals` (Hospital Comparison). Use metric selector/ranking sort; click a hospital row to open profile.
2. In `/hospitals/[id]`, show profile header, KPI cards, tabs (Overview/Departments/Operations/Finance/Workforce/Experience), and drilldown.
3. Navigate to `/appointments` or `/emergency` to show domain KPIs, chart drilldown, table export.

## Minute 3 - Data trust and engineering
1. Open `/data-quality`: DQ score, rule/failure visibility, dataset quality.
2. Open `/pipeline`: run history, run detail stages, compare two runs, lineage drilldown.
3. Open `/explorer`: dataset selector, schema, server-side pagination, numeric filters, export, record detail.
4. Open `/patient-journey`: load sample patient, filter timeline events, export CSV.
5. Close with `/kpi-glossary` and `/methodology`: KPI definitions, formulas, synthetic methodology, limitations.

## Key talking points
- 21 connected pages, 10 synthetic hospitals, reproducible seed-42 data.
- Layered Bronze/Silver/Gold/DuckDB/FastAPI/Next.js architecture.
- Parameterized SQL, allowlisted filters, `{data,pagination,metadata}` envelopes.
- DQ quarantine and manifest reconciliation; no fabricated KPI values in UI.
