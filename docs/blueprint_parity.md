# HOSPITAL 360 - Blueprint Parity Matrix

This document maps the 21-page blueprint (`blueprint_clean.txt` / PDF) to the current implementation on `feature/final-completion`. Status: **Implemented** = meets core blueprint intent; **Partial** = present with minor gaps; **Deferred** = not implemented (with reason).

## Summary

| # | Blueprint Page | Route | Status | Notes |
|---|---|---|---|---|
| 1 | Network Overview | `/overview` | Implemented | KPI cards, trends, hospital ranking, distribution/heatmap, operational charts, drilldown table, global filters, compare period. |
| 2 | Hospital Comparison | `/hospitals` | Implemented | KPI cards, ranking/comparison charts, monthly trends, KPI heatmap, table with drilldown; row click navigates to profile. Added metric selector + ranking sort controls (Phase 6). Global hospital filter supports multi-hospital comparison. |
| 3 | Hospital Profile | `/hospitals/[id]` | Implemented | Profile header (name/ID/location/type/beds/specialties/status), KPI cards, tabbed layout (Overview/Departments/Operations/Finance/Workforce/Experience), charts, department table, drilldowns (Phase 6). |
| 4 | Appointments & Patient Access | `/appointments` | Implemented | Config-driven page with appointment KPIs/charts/table/filters; drilldown/export via shared components. |
| 5 | Emergency & Patient Flow | `/emergency` | Implemented | Emergency KPIs, flow/wait/triage charts, table, filters, drilldown/export. |
| 6 | Inpatient & Bed Management | `/inpatient` | Implemented | Occupancy/LOS/admissions/discharge/readmission KPIs and charts, table, filters, drilldown/export. |
| 7 | Surgery & Procedures | `/procedures` | Implemented | Procedure/OR/utilization/cancellation KPIs, charts, table, filters, drilldown/export. |
| 8 | Diagnostics & Laboratory | `/diagnostics` | Implemented | Lab/TAT/SLA/critical result KPIs, charts, table, filters, drilldown/export. |
| 9 | Pharmacy | `/pharmacy` | Implemented | Prescription/dispensing/revenue/stockout KPIs, charts, table, filters, drilldown/export. |
| 10 | Finance & Revenue | `/finance` | Implemented | Revenue/collections/receivables/aging KPIs, charts, table, filters, drilldown/export. |
| 11 | Insurance & Claims | `/claims` | Implemented | Claims/denial/processing/appeal KPIs, charts, table, filters, drilldown/export. |
| 12 | Workforce | `/workforce` | Implemented | Staffing/overtime/absence/coverage KPIs, charts, table, filters, drilldown/export. |
| 13 | Inventory & Procurement | `/inventory` | Implemented | Stock/expiry/procurement KPIs, charts, table, filters, drilldown/export. |
| 14 | Patient Experience | `/experience` | Implemented | Satisfaction/NPS/complaint KPIs, charts, table, filters, drilldown/export; synthetic/algorithmic sentiment labeled. |
| 15 | Quality & Safety | `/quality` | Implemented | Incident/readmission/quality KPIs, charts, table, filters, drilldown/export; educational monitoring disclaimer in methodology. |
| 16 | Data Explorer | `/explorer` | Implemented | Dataset selector, server-side paginated table, search, sort, numeric min/max filter, schema panel, row count via table pagination, export CSV, record drilldown/detail, source lineage panel. Column selector is minor gap (columns auto-discovered from records). |
| 17 | Patient Journey | `/patient-journey` | Implemented | Synthetic patient lookup by patient/encounter/admission ID, sample-patient action, summary cards, chronological timeline with event-type/date filters, event detail drilldown, CSV export, synthetic-data notice (Phase 4). |
| 18 | Data Quality | `/data-quality` | Implemented | DQ KPI cards, category/rule/failure views, dataset quality charts/tables, filters, drilldown/export. |
| 19 | Data Pipeline & Run History | `/pipeline` | Implemented | Run history, manifest, lineage, run detail stages, error drilldown, compare-runs API/UI with delta table/chart (Phase 3). |
| 20 | KPI Glossary | `/kpi-glossary` | Implemented | Search, category filter, table/card views, detail drawer with formula/numerator/denominator/unit/grain/caveat/source, methodology link (Phase 5). |
| 21 | Methodology & Disclaimer | `/methodology` | Implemented | Synthetic data, ETL/model, KPI definitions, analysis conventions, limitations/disclaimer; docs/methodology.md maintained. |

## Cross-cutting parity checks

| Area | Status | Notes |
|---|---|---|
| Global filters in URL | Implemented | Date/hospital/department/specialty/payer/encounter/patient type + page params. |
| Compare period | Implemented | Global compare toggle; KPI cards consume previous-period API values. |
| KPI drilldown | Implemented | KPI cards route to relevant analytics page/filter context; charts/tables support drilldown. |
| Export | Implemented | DataTable CSV export via `/api/v1/exports/csv`; journey has dedicated export. |
| Server-side pagination | Implemented | DataTable uses API pagination; explorer enforces max page size. |
| Error/empty/loading states | Implemented | Shared UI states; no fabricated values when API unavailable. |
| Responsive layout | Implemented | Tailwind responsive grid/breakpoints; mobile Playwright coverage exists. |
| Accessibility baseline | Partial | Semantic headings/labels/aria in key components; full Phase 8 audit pending. |
| API envelope `{data,pagination,metadata}` | Implemented | Maintained across endpoints. |
| Synthetic data disclaimer | Implemented | Footer/banner/methodology/journey notices. |

## Known minor gaps / follow-up

- **Data Explorer column selector**: columns are auto-discovered; explicit user column visibility toggle is not yet exposed.
- **Some blueprint click-throughs**: chart click opens drilldown drawer/filter context; not every blueprint click maps to a dedicated subpage where no subpage exists.
- **Department profile page**: blueprint references department detail in interactions; current implementation provides drilldown/filtering rather than a dedicated department profile route.
- **Phase 8**: full a11y/responsive/performance/security hardening and verification still required.
- **Phase 9**: screenshots, README/case-study refresh, demo script, diagrams still required.
- **Phase 10**: deployment prep only; no live deployment/accounts.
