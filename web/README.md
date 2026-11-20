# HOSPITAL 360 — Next.js Frontend

Next.js 15 (App Router) + TypeScript + Tailwind CSS + Apache ECharts + TanStack Table/Query frontend for HOSPITAL 360.

All displayed values are fetched from the FastAPI backend. There is no mock data in this application: when the API is unavailable the UI shows explicit error or empty states.

## Setup

```bash
npm install
cp .env.example .env.local   # optional; defaults to http://localhost:8000/api/v1
npm run dev
```

Open http://localhost:3000 (redirects to `/overview`).

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Development server |
| `npm run build` | Production build |
| `npm start` | Run the production build |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | ESLint |

`NEXT_PUBLIC_API_URL` is the only environment variable. It must point at the API base (default `http://localhost:8000/api/v1`).

## Architecture

- `lib/types.ts` — API envelopes, KPI values, filters, page/chart/table config types.
- `lib/api.ts` — typed fetch client; builds contract query strings from global filters; all reads go through one TanStack Query hook with the filter state in the query key and the abort signal forwarded to `fetch`.
- `lib/filters.tsx` — `FilterProvider`: URL-synchronised filter state (`date_from`, `date_to`, `hospital_id[]`, `department_id`, `specialty_id`, `payer_id`, `encounter_type`, `patient_type`) plus context-sensitive hospital/department/specialty options.
- `lib/page-configs.ts` — the single registry of all 21 pages (KPI endpoints/ids, charts, tables, filters, drilldowns) and KPI click-through routing rules.
- `lib/chart.ts` — normalises the documented API payload shapes into ECharts options.
- `components/AnalyticsPage.tsx` — generic renderer for data-driven pages.
- `components/{KpiCard,ChartContainer,DataTable,DrilldownDrawer,FilterBar,AppShell}.tsx` — reusable interaction layer.
- `components/ui/` — Card, Badge, Skeleton, Empty/Error states, Select, DateRangePicker.

Special pages use dedicated components: `ExplorerPage`, `PatientJourneyPage`, `DataQualityPage`, `PipelinePage`, `KpiGlossaryPage`, `MethodologyPage`.

## Routes

`/overview`, `/hospitals`, `/hospitals/[id]`, `/appointments`, `/emergency`, `/inpatient`, `/procedures`, `/diagnostics`, `/pharmacy`, `/finance`, `/claims`, `/workforce`, `/inventory`, `/experience`, `/quality`, `/explorer`, `/patient-journey`, `/data-quality`, `/pipeline`, `/kpi-glossary`, `/methodology`.

All 21 routes are registered in the grouped sidebar.

## Interaction notes

- KPI cards navigate to the relevant analytics page and preserve every active URL filter. Tooltips show glossary definitions where the API provides them.
- Charts support tooltips, legend toggling, data zoom on time series, range-to-filter selection, CSV download and click-through to the record drawer.
- Tables use server-side pagination/sorting, debounced search, column visibility, CSV export (capped at 5,000 rows) and row-level drilldowns.
- Global filters affect KPIs, charts, tables, exports and drilldowns. A chart that ignores filters is labelled "Unfiltered benchmark".
- Compare-period mode is a URL flag (`compare=1`) read by KPI cards.
- Lower-is-better metrics invert change colour so green always means favourable.

## Disclaimer

This is an educational portfolio project using entirely synthetic data. It is not a clinical system and must not be used for diagnosis, treatment or real hospital operations.
