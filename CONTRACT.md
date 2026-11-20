# HOSPITAL 360 — Engineering Contract (single source of truth)

All layers import `generator/schema.py` for the canonical transactional schemas.
This document fixes the **gold tables**, **API responses** and **frontend pages** so
that independent modules remain compatible.

> Read `blueprint_clean.txt` (project root) for the full product specification.

---

## 1. Directory layout

```
hospital360/
  generator/    -> synthetic data (bronze CSVs + manifest)
  etl/          -> bronze/silver/gold + DuckDB load + quality + quarantine
  analytics/    -> SQL models + KPI definitions (JSON)
  api/          -> FastAPI app (reads DuckDB gold tables)
  web/          -> Next.js app (reads API)
  data/         -> bronze/, silver/, gold/, quarantine/, manifests/, hospital360.duckdb
  docs/         -> architecture, erd, data dictionary, KPI glossary, methodology
  tests/        -> pytest suites + playwright e2e
```

## 2. Data flow

`generator -> data/bronze/*.csv -> etl silver (parquet) -> etl gold (parquet) -> DuckDB -> FastAPI -> Next.js`

- Seed: 42. Window: 2025-01-01 .. 2026-12-31 (24 months).
- Every pipeline run writes `data/manifests/manifest_<run_id>.json`.
- Intentional DQ issues are recorded in the manifest, never silently dropped.

## 3. Gold tables (DuckDB)

All gold tables are materialised as tables (not just views) in `data/hospital360.duckdb`.
`month` is a DATE (first of month). All rates are percentages (0–100). Null denominators
produce NULL, never a fabricated zero.

### 3.1 `gold_network_daily`
`date DATE, encounters INT, admissions INT, appointments INT, completed_appointments INT,
no_show_appointments INT, revenue DOUBLE, collections DOUBLE, occupied_beds INT,
available_beds INT, avg_wait_minutes DOUBLE`

### 3.2 `gold_hospital_monthly` (the main workhorse)
`hospital_id VARCHAR, hospital_name VARCHAR, month DATE,
patients INT, encounters INT, admissions INT, discharges INT,
appointments INT, completed_appointments INT, cancelled_appointments INT,
no_show_appointments INT, no_show_rate DOUBLE, avg_wait_minutes DOUBLE,
occupied_bed_days DOUBLE, available_bed_days DOUBLE, occupancy_rate DOUBLE,
avg_los_days DOUBLE, readmissions INT, readmission_rate DOUBLE,
gross_revenue DOUBLE, net_revenue DOUBLE, collections DOUBLE,
outstanding_balance DOUBLE, collection_rate DOUBLE,
lab_orders INT, completed_lab_tests INT, avg_lab_tat_minutes DOUBLE, lab_sla_rate DOUBLE,
claims_submitted INT, claims_denied INT, denial_rate DOUBLE,
feedback_count INT, avg_satisfaction DOUBLE, complaint_count INT,
incidents_count INT, scheduled_hours DOUBLE, worked_hours DOUBLE,
overtime_hours DOUBLE, stockouts INT, inventory_value DOUBLE`

### 3.3 `gold_department_monthly`
`hospital_id, department_id, department_name, specialty_id, specialty_name, month,
patients INT, encounters INT, admissions INT, appointments INT, no_show_rate DOUBLE,
avg_wait_minutes DOUBLE, occupancy_rate DOUBLE, avg_los_days DOUBLE, revenue DOUBLE,
lab_orders INT, avg_lab_tat_minutes DOUBLE, denial_rate DOUBLE,
avg_satisfaction DOUBLE, incidents_count INT`

### 3.4 `gold_patient_access`
`hospital_id, department_id, month, scheduled INT, completed INT, cancelled INT, no_shows INT,
no_show_rate DOUBLE, avg_wait_minutes DOUBLE, avg_lead_days DOUBLE,
same_day_pct DOUBLE, reschedule_rate DOUBLE`

### 3.5 `gold_bed_utilization`
`hospital_id, ward, month, total_beds INT, occupied_bed_days DOUBLE,
available_bed_days DOUBLE, blocked_bed_days DOUBLE, occupancy_rate DOUBLE,
avg_los_days DOUBLE, discharges INT, bed_turnover DOUBLE, avg_boarding_hours DOUBLE`

### 3.6 `gold_financial_performance`
`hospital_id, department_id, month, gross_revenue DOUBLE, net_revenue DOUBLE,
collections DOUBLE, outstanding_balance DOUBLE, collection_rate DOUBLE,
avg_invoice_value DOUBLE, refunds DOUBLE, writeoffs DOUBLE, revenue_growth_pct DOUBLE`

### 3.7 `gold_claim_performance`
`hospital_id, payer_id, payer_name, month, claims INT, approved INT, denied INT,
denial_rate DOUBLE, claimed_amount DOUBLE, approved_amount DOUBLE, paid_amount DOUBLE,
avg_processing_days DOUBLE, appeals INT, appeal_success_rate DOUBLE`

### 3.8 `gold_lab_performance`
`hospital_id, test_code, test_name, month, orders INT, completed INT, pending INT,
cancelled INT, avg_tat_minutes DOUBLE, median_tat_minutes DOUBLE, sla_rate DOUBLE,
delayed INT, critical INT`

### 3.9 `gold_workforce`
`hospital_id, department_id, month, headcount INT, scheduled_hours DOUBLE,
worked_hours DOUBLE, overtime_hours DOUBLE, absence_rate DOUBLE,
coverage_pct DOUBLE, workforce_cost DOUBLE`

### 3.10 `gold_inventory`
`hospital_id, category, month, inventory_value DOUBLE, stockouts INT, low_stock INT,
expired_value DOUBLE, waste DOUBLE, turnover DOUBLE, purchase_orders INT,
procurement_value DOUBLE, supplier_on_time_rate DOUBLE`

### 3.11 `gold_patient_experience`
`hospital_id, department_id, month, feedback_count INT, avg_rating DOUBLE,
satisfaction_pct DOUBLE, promoters INT, detractors INT, nps DOUBLE,
complaints INT, complaint_resolution_days DOUBLE`

### 3.12 `gold_quality_safety`
`hospital_id, department_id, month, incidents INT, incident_rate DOUBLE, falls INT,
medication_incidents INT, infection_incidents INT, critical_incidents INT,
investigation_completion_rate DOUBLE, avg_investigation_days DOUBLE, readmission_rate DOUBLE`

Also load the **silver** transactional tables into DuckDB with the `silver_` prefix
(e.g. `silver_appointments`, `silver_encounters`, ...) to power the Data Explorer
and record-level drill-downs.

## 4. API contract

Base: `/api/v1`. All responses (except health) use:
```json
{ "data": <object|array>, "metadata": { "date_from": "...", "date_to": "...",
  "hospital_ids": ["H01"], "generated_at": "ISO8601Z" } }
```
Table responses add `"pagination": { "page":1, "page_size":50, "total_records":0, "total_pages":0 }`.

Common query params: `date_from`, `date_to`, `hospital_id` (repeatable), `department_id`,
`specialty_id`, `payer_id`, `encounter_type`, `patient_type`, `page`, `page_size`, `search`, `sort_by`, `sort_dir`.

### Endpoints (all GET)
| Group | Endpoints |
|---|---|
| meta | `/health` (no envelope: `{"status":"ok","version":"1.0.0"}`) |
| overview | `/overview/kpis`, `/overview/trends`, `/overview/hospital-ranking`, `/overview/heatmap`, `/overview/distribution`, `/overview/operational` |
| hospitals | `/hospitals`, `/hospitals/{id}/kpis`, `/hospitals/{id}/departments`, `/hospitals/{id}/trends`, `/hospitals/{id}/profile` |
| appointments | `/appointments/kpis`, `/appointments/trends`, `/appointments/no-shows`, `/appointments/wait-times`, `/appointments/heatmap`, `/appointments/departments`, `/appointments/records` |
| emergency | `/emergency/kpis`, `/emergency/trend`, `/emergency/arrivals`, `/emergency/flow`, `/emergency/records` |
| inpatient | `/inpatient/kpis`, `/inpatient/occupancy`, `/inpatient/los`, `/inpatient/bed-status`, `/inpatient/admissions`, `/inpatient/records` |
| procedures | `/procedures/kpis`, `/procedures/volume`, `/procedures/utilization`, `/procedures/records` |
| diagnostics | `/diagnostics/kpis`, `/diagnostics/tat`, `/diagnostics/volume`, `/diagnostics/records` |
| pharmacy | `/pharmacy/kpis`, `/pharmacy/trend`, `/pharmacy/records` |
| finance | `/finance/kpis`, `/finance/revenue-trend`, `/finance/collections`, `/finance/receivables`, `/finance/revenue-by`, `/finance/invoices`, `/finance/records` |
| claims | `/claims/kpis`, `/claims/denials`, `/claims/payers`, `/claims/aging`, `/claims/records` |
| workforce | `/workforce/kpis`, `/workforce/coverage`, `/workforce/overtime`, `/workforce/attendance`, `/workforce/records` |
| inventory | `/inventory/kpis`, `/inventory/stockouts`, `/inventory/expiry`, `/inventory/movements`, `/inventory/records` |
| experience | `/experience/kpis`, `/experience/trend`, `/experience/by-hospital`, `/experience/records` |
| quality | `/quality/kpis`, `/quality/trend`, `/quality/incidents`, `/quality/records` |
| data-quality | `/data-quality/summary`, `/data-quality/rules`, `/data-quality/failures`, `/data-quality/datasets` |
| pipeline | `/pipeline/runs`, `/pipeline/runs/{run_id}`, `/pipeline/manifest`, `/pipeline/lineage` |
| explorer | `/explorer/datasets`, `/explorer/{dataset}/records`, `/explorer/{dataset}/schema` |
| glossary | `/kpis/glossary` |

`kpis` endpoints return an object keyed by KPI id:
```json
"data": { "total_encounters": {"value": 24836, "previous": 22911, "change_pct": 8.4,
  "sparkline": [ ... 12 monthly values ... ], "unit": "count"}, ... }
```
`trends`/`ranking`/`heatmap` endpoints return arrays of objects suitable for ECharts.

KPI ids (use exactly these keys): `total_patients, total_encounters, total_admissions,
total_revenue, net_collections, average_occupancy, average_los, patient_satisfaction,
no_show_rate, claim_denial_rate, collection_rate, ...` (module-specific ids in
`analytics/kpi_definitions/kpis.json`).

Canonical semantics (Phase 2): `total_revenue` is gross, `revenue` is net and is
never an alias of `total_revenue`; `patient_satisfaction` is a 0-100 percentage and
`average_satisfaction` is the 1-5 score; `average_investigation_time` is canonical
with `avg_investigation_time` as a documented alias; `collection_rate` is uncapped
and values above 100% are flagged, not clipped. The KPI JSON file is the single
definition contract; every API spec and frontend id is validated against it.

## 5. Frontend pages (21)

Route | Page | Primary API
---|---|---
`/overview` | Network Overview | overview/*
`/hospitals` | Hospital Comparison | hospitals, overview/hospital-ranking
`/hospitals/[id]` | Hospital Profile | hospitals/{id}/*
`/appointments` | Appointments & Access | appointments/*
`/emergency` | Emergency & Patient Flow | emergency/*
`/inpatient` | Inpatient & Beds | inpatient/*
`/procedures` | Surgery & Procedures | procedures/*
`/diagnostics` | Diagnostics & Laboratory | diagnostics/*
`/pharmacy` | Pharmacy | pharmacy/*
`/finance` | Finance & Revenue | finance/*
`/claims` | Insurance & Claims | claims/*
`/workforce` | Workforce | workforce/*
`/inventory` | Inventory & Procurement | inventory/*
`/experience` | Patient Experience | experience/*
`/quality` | Quality & Safety | quality/*
`/explorer` | Data Explorer | explorer/*
`/patient-journey` | Patient Journey | explorer + records
`/data-quality` | Data Quality | data-quality/*
`/pipeline` | Data Pipeline | pipeline/*
`/kpi-glossary` | KPI Glossary | kpis/glossary
`/methodology` | Methodology | static

Shared components: `KpiCard`, `ChartContainer`, `FilterBar`, `DataTable`, `DrilldownDrawer`,
`AppShell` (collapsible sidebar + header + global filters). Global filter state is stored
in URL query params and React context. No hard-coded metric values.

Design: restrained enterprise healthcare palette — navy primary, teal secondary,
green/amber/red semantic status, light neutral background, white cards, dark slate text.
Responsive: desktop 4–6 KPI cards/row, tablet 2–3, mobile 1–2 with filter drawer.

## 6. Testing
- pytest: generator uniqueness/relationships, silver/gold validity, KPI edge cases, API.
- Playwright e2e: open overview -> filter H03 -> change date -> click KPI -> export.
