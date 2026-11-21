# HOSPITAL 360 - Blueprint Parity Matrix

Maps the 21-page blueprint (`blueprint_clean.txt` / PDF) to current implementation on `feature/final-completion`.  
**Status values:** Implemented | Missing | Differs.  
**Current result:** 0 Missing, 0 Differs.

## 21-Page Parity

| # | Blueprint Page | Route | Status | Evidence / Notes |
|---|---|---|---|---|
| 1 | Network Overview | `/overview` | Implemented | KPI cards, trends, hospital ranking, distribution/heatmap, operational charts, drilldown table, global filters, compare period. |
| 2 | Hospital Comparison | `/hospitals` | Implemented | KPI cards, ranking/comparison charts, monthly trends, KPI heatmap, table with drilldown; row click navigates to profile; metric selector + ranking sort controls. |
| 3 | Hospital Profile | `/hospitals/[id]` | Implemented | Profile header, KPI cards, tabbed layout (Overview/Departments/Operations/Finance/Workforce/Experience), charts, department table, drilldowns. |
| 4 | Appointments & Patient Access | `/appointments` | Implemented | Config-driven page with appointment KPIs/charts/table, filters, export, drilldown. |
| 5 | Emergency & Urgent Care | `/emergency` | Implemented | Config-driven ED KPIs/charts/table. |
| 6 | Inpatient & Bed Management | `/inpatient` | Implemented | Occupancy/LOS/bed management KPIs/charts/table. |
| 7 | Surgery & Procedures | `/procedures` | Implemented | Procedure KPIs/charts/table. |
| 8 | Diagnostics & Lab | `/diagnostics` | Implemented | Diagnostics/Lab/TAT KPIs/charts/table. |
| 9 | Pharmacy & Medication | `/pharmacy` | Implemented | Pharmacy KPIs/charts/table. |
| 10 | Finance & Revenue Cycle | `/finance` | Implemented | Finance KPIs/charts/table. |
| 11 | Claims & Payer Performance | `/claims` | Implemented | Claims/denial KPIs/charts/table. |
| 12 | Workforce & HR | `/workforce` | Implemented | Workforce KPIs/charts/table. |
| 13 | Supply Chain & Inventory | `/inventory` | Implemented | Inventory KPIs/charts/table. |
| 14 | Patient Experience | `/experience` | Implemented | Experience/satisfaction KPIs/charts/table. |
| 15 | Quality & Compliance | `/quality` | Implemented | Quality/incident/compliance KPIs/charts/table. |
| 16 | Data Quality | `/data-quality` | Implemented | DQ summary, rules, freshness, quarantine, pipeline links. |
| 17 | Data Explorer | `/explorer` | Implemented | Dataset/schema/preview/table explorer; DataTable includes column visibility toggle (Columns control). |
| 18 | Patient Journey | `/patient-journey` | Implemented | Patient timeline/search, event filters, export, synthetic notice. Frontend route `/patient-journey`; API endpoints under `/api/v1/journey/*`. |
| 19 | KPI Dictionary | `/glossary` | Implemented | Glossary table/cards, search/filter, formula/definition display. |
| 20 | Pipeline Status | `/pipeline` | Implemented | Runs, compare runs, lineage drawer, manifest/DQ summary links. |
| 21 | Cross-cutting / All Pages | all routes | Implemented | Global filters + URL sync, compare period, export, drilldown, breadcrumbs, loading/empty/error states, synthetic disclaimers. |

## Cross-Cutting Requirements

| Requirement | Status | Evidence / Notes |
|---|---|---|
| Global filter bar with URL sync | Implemented | `FilterBar`, `useFilters`, URL query params. |
| Context-sensitive filters | Implemented | `page-filters.ts` / page configs hide irrelevant filters. |
| Filter hierarchy hospital→department→doctor | Implemented | Filter option dependencies in filter API/UI. |
| KPI cards: previous, abs change, % change, trend, sparkline, tooltip | Implemented | `KpiCard.tsx` shows previous, abs delta, % change, trend icon, sparkline, definition tooltip. |
| Chart interactions: tooltip, drilldown, legend toggle, zoom, download | Implemented | `EChart.tsx` default toolbox (dataZoom, dataView, restore, saveAsImage) for charts >80px; ECharts legend/tooltips enabled per chart config. |
| Tables: sort, search, pagination, CSV export, column visibility | Implemented | `DataTable.tsx` has sorting/search/pagination/export; column visibility toggle via Columns button. |
| CSV export max 5000 rows | Implemented | Export limit enforced in API/UI. |
| API envelope `{data,pagination,metadata}` | Implemented | Backend response helpers and frontend types. |
| SQL parameterized; dynamic identifiers allowlisted | Implemented | Query builder/allowlists; tests cover injection patterns. |
| Accessibility baseline (WCAG AA target) | Implemented | Key controls labeled; focus styles present. Phase 8 axe audit/remediations recorded in `docs/accessibility.md` and mobile viewport tests added. |
| Mobile responsive | Implemented | Responsive layout; Phase 8 mobile viewport Playwright checks added. |

## Known Follow-up (non-blocking)
- ECharts 6.x upgrade trial is tracked in Phase 8; revert if regressions/failures.
- No live deployment performed; deployment prep only.
