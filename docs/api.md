# HOSPITAL 360 - API Reference

Base URL: `/api/v1`. All endpoints are `GET`. Interactive OpenAPI docs are served by
FastAPI at `/docs` (ReDoc at `/redoc`) when the app is running.

## Response standards

**Health** is the only endpoint without the standard envelope:

```json
{ "status": "ok", "version": "1.0.0" }
```

**All other endpoints** use:

```json
{
  "data": { "...": "..." },
  "metadata": {
    "date_from": "2025-01-01",
    "date_to": "2026-12-31",
    "hospital_ids": ["H01"],
    "generated_at": "2026-11-20T00:00:00Z"
  }
}
```

**Table responses** include `pagination` at the top level. The same object is also kept
under `metadata.pagination` for backward compatibility with pre-Phase-3 clients:

```json
{
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_records": 0,
    "total_pages": 0
  },
  "metadata": {
    "pagination": {
      "page": 1,
      "page_size": 50,
      "total_records": 0,
      "total_pages": 0
    }
  }
}
```

**Errors** use one structured shape for validation, missing resources, export limits and
internal failures. `code` is a stable machine-readable string; `message` is human-readable:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable explanation",
    "details": { "parameter": "page", "value": "0" },
    "generated_at": "2026-11-20T00:00:00Z"
  }
}
```

Stable codes include `VALIDATION_ERROR` (422), `NOT_FOUND` (404),
`EXPORT_LIMIT_EXCEEDED` (413), `BAD_REQUEST` (400), `INTERNAL_ERROR` (500) and
`DATABASE_NOT_READY` (503). Responses never include stack traces.

## Common query parameters

| Parameter | Type | Notes |
|---|---|---|
| `date_from`, `date_to` | `YYYY-MM-DD` | Inclusive; default `2025-01-01` / `2026-12-31` |
| `hospital_id` | repeatable string | `?hospital_id=H01&hospital_id=H03` |
| `department_id`, `specialty_id`, `payer_id` | string | Context-sensitive; ignored if the target table lacks the column |
| `encounter_type`, `patient_type` | string | Allowlisted values |
| `page`, `page_size` | int | Default 1 / 50; each must be a positive integer and page size may not exceed 5,000 |
| `search` | string | Applied only to allowlisted searchable text columns |
| `sort_by`, `sort_dir` | string | `sort_dir` must be `asc` or `desc`; `sort_by` must be an identifier |
| `previous` | bool | `true`/`false`, `1`/`0` or `yes`/`no`; compares with the preceding equal-length period |
| `numeric_column`, `numeric_min`, `numeric_max` | string/number | Explorer range filter; column must be allowlisted and numeric |

All supported parameters are validated. Unknown keys, malformed dates, reversed date ranges,
invalid integers/booleans/numbers, oversized `page_size`, invalid sort directions and malformed
identifiers return `VALIDATION_ERROR` (422) with the offending `details`. Filter columns are
allowlisted and all values are passed as bound SQL parameters; arbitrary SQL is never executed.

Snapshot KPIs (`hospitals_selected`, `total_beds`, `active_employees`) have no date field. They
remain active and report `date_filter_available: false` with an explanatory note instead of
silently ignoring the date range.

`kpis` endpoints return an object keyed by KPI id:

```json
"data": {
  "total_encounters": {
    "value": 24836,
    "previous": 22911,
    "change_pct": 8.4,
    "sparkline": [1720, 1810, 1890, 1990, 2040, 2105, 2180, 2210, 2280, 2340, 2405, 24836],
    "unit": "count"
  }
}
```

> The numbers above are **illustrative shape only**, from the blueprint. Real values come
> from the generated DuckDB database after running the pipeline.

## Endpoint catalogue

### Meta

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Liveness/version; no envelope |

### Overview

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/overview/kpis` | Ten network KPI cards |
| GET | `/api/v1/overview/trends` | Patient volume, revenue and collections trends |
| GET | `/api/v1/overview/hospital-ranking` | Hospital ranking by selectable metric |
| GET | `/api/v1/overview/heatmap` | Hospital x KPI heatmap |
| GET | `/api/v1/overview/distribution` | Patient distribution by hospital/department/specialty |
| GET | `/api/v1/overview/operational` | Radar/normalised operational performance |

### Hospitals

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/hospitals` | Hospital list/profile summary |
| GET | `/api/v1/hospitals/{id}/kpis` | KPI cards for one hospital |
| GET | `/api/v1/hospitals/{id}/departments` | Departments with performance |
| GET | `/api/v1/hospitals/{id}/trends` | Hospital monthly trends |
| GET | `/api/v1/hospitals/{id}/profile` | Static profile details |

### Appointments & access

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/appointments/kpis` | Appointment KPI cards |
| GET | `/api/v1/appointments/trends` | Scheduled/completed/cancelled/no-show trend |
| GET | `/api/v1/appointments/no-shows` | No-show rate trend / breakdown |
| GET | `/api/v1/appointments/wait-times` | Waiting-time distribution |
| GET | `/api/v1/appointments/heatmap` | Day-of-week x hour heatmap |
| GET | `/api/v1/appointments/departments` | Department-level access metrics |
| GET | `/api/v1/appointments/records` | Filterable appointment records (paginated) |

### Emergency

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/emergency/kpis` | Emergency KPI cards |
| GET | `/api/v1/emergency/trend` | Visit and crowding trend |
| GET | `/api/v1/emergency/arrivals` | Hourly/weekday arrivals |
| GET | `/api/v1/emergency/flow` | Patient-flow stage data |
| GET | `/api/v1/emergency/records` | Emergency encounter records |

### Inpatient

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/inpatient/kpis` | Inpatient KPI cards |
| GET | `/api/v1/inpatient/occupancy` | Occupancy trend by hospital/ward |
| GET | `/api/v1/inpatient/los` | LOS distribution / by specialty |
| GET | `/api/v1/inpatient/bed-status` | Current bed state counts |
| GET | `/api/v1/inpatient/admissions` | Admission records |
| GET | `/api/v1/inpatient/records` | Admission detail records |

### Procedures

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/procedures/kpis` | Procedure KPI cards |
| GET | `/api/v1/procedures/volume` | Volume by specialty/hospital |
| GET | `/api/v1/procedures/utilization` | OR utilisation |
| GET | `/api/v1/procedures/records` | Procedure records |

### Diagnostics

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/diagnostics/kpis` | Lab KPI cards |
| GET | `/api/v1/diagnostics/tat` | Turnaround distribution/trend |
| GET | `/api/v1/diagnostics/volume` | Test volume by category/test |
| GET | `/api/v1/diagnostics/records` | Lab order/result records |

### Pharmacy

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/pharmacy/kpis` | Pharmacy KPI cards |
| GET | `/api/v1/pharmacy/trend` | Prescription/dispensing trend |
| GET | `/api/v1/pharmacy/records` | Prescription records |

### Finance

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/finance/kpis` | Finance KPI cards |
| GET | `/api/v1/finance/revenue-trend` | Revenue, collections, outstanding |
| GET | `/api/v1/finance/collections` | Collections trend |
| GET | `/api/v1/finance/receivables` | Receivables aging buckets |
| GET | `/api/v1/finance/revenue-by` | Revenue by department/specialty/service |
| GET | `/api/v1/finance/invoices` | Invoice records |
| GET | `/api/v1/finance/records` | Finance detail records |

### Claims

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/claims/kpis` | Claim KPI cards |
| GET | `/api/v1/claims/denials` | Denials and reasons |
| GET | `/api/v1/claims/payers` | Payer performance |
| GET | `/api/v1/claims/aging` | Pending-claim aging |
| GET | `/api/v1/claims/records` | Claim records |

### Workforce

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/workforce/kpis` | Workforce KPI cards |
| GET | `/api/v1/workforce/coverage` | Shift coverage |
| GET | `/api/v1/workforce/overtime` | Overtime trend/records |
| GET | `/api/v1/workforce/attendance` | Attendance records |
| GET | `/api/v1/workforce/records` | Shift records |

### Inventory

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/inventory/kpis` | Inventory KPI cards |
| GET | `/api/v1/inventory/stockouts` | Stockout items/trend |
| GET | `/api/v1/inventory/expiry` | Expiry/expired value |
| GET | `/api/v1/inventory/movements` | Movement history |
| GET | `/api/v1/inventory/records` | Inventory records |

### Experience

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/experience/kpis` | Experience KPI cards |
| GET | `/api/v1/experience/trend` | Satisfaction trend |
| GET | `/api/v1/experience/by-hospital` | Hospital comparison |
| GET | `/api/v1/experience/records` | Feedback records |

### Quality

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/quality/kpis` | Quality KPI cards |
| GET | `/api/v1/quality/trend` | Incident trend |
| GET | `/api/v1/quality/incidents` | Incidents by category/severity |
| GET | `/api/v1/quality/records` | Incident records |

### Data quality

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/data-quality/summary` | DQ score and category scores |
| GET | `/api/v1/data-quality/rules` | Rule catalogue |
| GET | `/api/v1/data-quality/failures` | Failed validation records |
| GET | `/api/v1/data-quality/datasets` | Per-dataset quality summary |

### Pipeline

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/pipeline/runs` | Run history |
| GET | `/api/v1/pipeline/runs/{run_id}` | Single run detail |
| GET | `/api/v1/pipeline/manifest` | Latest manifest |
| GET | `/api/v1/pipeline/lineage` | Source-to-gold lineage |

### Explorer

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/explorer/datasets` | Allowed datasets and row counts |
| GET | `/api/v1/explorer/{dataset}/records` | Paginated, filterable records |
| GET | `/api/v1/explorer/{dataset}/schema` | Column names, dtypes, descriptions |

### Exports

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/exports/csv?path=<endpoint>&filename=<name>` | Server-side CSV export of any registered GET data endpoint |

Exports reuse the source endpoint, so the same filters, sorting, SQL and KPI formulas apply.
The server enforces `MAX_EXPORT_ROWS = 5000` on both the source total and the exported row
count. A filtered result above the cap returns `EXPORT_LIMIT_EXCEEDED` (413); pagination cannot
be used to bypass it. Clients must show the returned `error.message` rather than silently
truncating rows.

### Glossary

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/kpis/glossary` | Full KPI registry from `analytics/kpi_definitions/kpis.json` |

## Example requests and responses

### Health

```http
GET /api/v1/health
```

```json
{ "status": "ok", "version": "1.0.0" }
```

### Filtered overview KPIs

```http
GET /api/v1/overview/kpis?hospital_id=H03&date_from=2026-07-01&date_to=2026-12-31
```

```json
{
  "data": {
    "total_patients": { "value": 1250, "previous": 1190, "change_pct": 5.0, "sparkline": [], "unit": "count" },
    "no_show_rate": { "value": 8.2, "previous": 9.1, "change_pct": -9.9, "sparkline": [], "unit": "%" },
    "average_occupancy": { "value": 81.4, "previous": 79.8, "change_pct": 2.0, "sparkline": [], "unit": "%" }
  },
  "metadata": {
    "date_from": "2026-07-01",
    "date_to": "2026-12-31",
    "hospital_ids": ["H03"],
    "generated_at": "2026-11-20T00:00:00Z"
  }
}
```

### Paginated records (no-show drill-down)

```http
GET /api/v1/appointments/records?hospital_id=H03&status=No-show&page=2&page_size=25&sort_by=appointment_date&sort_dir=desc
```

```json
{
  "data": [
    {
      "appointment_id": "APT0000123",
      "patient_id": "PAT0000456",
      "hospital_id": "H03",
      "department_id": "D023",
      "appointment_date": "2026-09-14",
      "status": "No-show",
      "waiting_minutes": null
    }
  ],
  "pagination": { "page": 2, "page_size": 25, "total_records": 76, "total_pages": 4 },
  "metadata": {
    "date_from": "2025-01-01",
    "date_to": "2026-12-31",
    "hospital_ids": ["H03"],
    "generated_at": "2026-11-20T00:00:00Z",
    "filters_applied": { "status": "No-show" }
  }
}
```

### Explorer schema

```http
GET /api/v1/explorer/appointments/schema
```

```json
{
  "data": {
    "table": "silver_appointments",
    "columns": [
      { "name": "appointment_id", "type": "VARCHAR", "description": "APT0000001.." },
      { "name": "patient_id", "type": "VARCHAR", "description": "FK patients" }
    ]
  },
  "metadata": { "date_from": null, "date_to": null, "hospital_ids": [], "generated_at": "2026-11-20T00:00:00Z" }
}
```

### KPI glossary

```http
GET /api/v1/kpis/glossary
```

Returns the full registry (163 definitions) with the fields documented in
[kpi_glossary.md](kpi_glossary.md): `id`, `name`, `category`, `business_definition`,
`formula`, `numerator`, `denominator`, `grain`, `date_field`, `exclusions`, `source_tables`,
`dimensions`, `unit`, `target`, `caveat` and `validation_test`.

## Notes for frontend consumers

- Always render `metadata.date_from`, `metadata.date_to` and `metadata.hospital_ids` with
  the data so a view is self-describing.
- Treat `null` metric values as "undefined for this filter" and show the documented empty
  state; never substitute `0`.
- Abort in-flight requests when filters change to avoid stale responses overwriting new ones.
- Exports use the same filters and are capped; the UI must communicate the cap.
