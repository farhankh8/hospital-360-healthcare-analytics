# HOSPITAL 360 Phase 2 — KPI and Analytics Integrity Audit

Date: 2026-11-20  
Branch: `feature/phase2-kpi-integrity`  
Base: `9c659f8 Phase 1 data and schema integrity repair`  
Canonical contract: `analytics/kpi_definitions/kpis.json` (`phase2-kpi-integrity-v1`)

## 1. Executive summary

- Definitions audited: **190**; unique IDs: **190**.
- Consumer status: `active`=134, `alias`=29, `api_only`=26, `unused_definition_documented`=1.
- Units: `count`=76, `currency`=32, `days`=9, `hours`=7, `minutes`=16, `percent`=37, `ratio`=4, `score`=5, `seconds`=1, `text`=2, `visits/day`=1.
- Recorded audit findings: **154** across the 190 definitions.
- Formula strings containing division without an explicit `NULLIF`: **39** (all executable API specs use `NULLIF`).
- No KPI definition was deleted. One definition (`revenue_per_hospital_department`) is retained as a documented, unconsumed definition.
- Resolution counts: 190 canonicalised, 7 named conflicts resolved, 19 glossary pseudo-SQL formulas corrected, 3 date-field references disabled, 29 aliases documented, 1 unused definition retained, 0 deletions, 0 blocking decisions.
- Deprecated/deduplicated response keys are retained as documented aliases, including `avg_investigation_time` and `average_satisfaction_score`.
- No Phase 3, deployment, advanced analytics or machine-learning work was started.

## 2. Scope and method

Read-only source inspection plus read-only DuckDB reproduction against `data/hospital360.duckdb`.
Every layer was traced: `kpis.json`, all 12 gold SQL models, `analytics/kpis.py`,
`api/services/kpi_specs.py`, `api/services/metrics.py`, API routes, `web/lib/page-configs.ts`,
`web/lib/format.ts`, KPI cards, glossary pages and existing tests. The frontend performs no business calculation.
There is no Pydantic KPI response model: `api/core/responses.py` returns a generic envelope and
`web/lib/types.ts` types KPI values loosely. This was traced but not changed because strict response
schemas belong to the Phase 3 API contract work.

## 3. Requested-item coverage

1. All 190 definitions inventoried in section 9 including duplicates, aliases, missing columns, broken formulas, date fields, aggregation, units, percentage errors, zero-denominator risk, NULL handling, unused definitions and missing consumers.
2. One canonical contract exists in `kpis.json`; every definition carries ID, display name, business definition, formula, numerator, denominator, source tables/columns, aggregation, date column, filter behavior, units, precision, NULL handling, additivity, expected range, aliases, interpretation, consumer status and audit findings.
3. The seven named conflicts are resolved in section 4.
4. Gross, discounts, adjustments, refunds, net revenue, collections and outstanding balance are reconciled in section 5; gross is not forced to equal net.
5. One satisfaction scale is documented: 1-5 score for `average_satisfaction`, 0-100 percentage for `patient_satisfaction`.
6. Collection-rate semantics are documented as uncapped with >100% flagged, not silently clipped.
7. Date and filter behavior was validated for start/end date, hospital and department using the correct business date columns; dimension KPIs no longer claim a non-existent date column.
8. SQL, Python, API, glossary and dashboard values are reconciled by the contract tests described in section 7.
9. Frontend IDs and labels were updated without changing visual design.
10. No KPI definition was deleted and no unrelated API contract was changed.
11. Reconciliation tests cover filters, boundaries, empty/NULL/zero denominators and gross/net revenue.
12. Full gates were run and no Phase 1 regression was found (section 8).
13. Work stops here, before Phase 3.

## 4. Conflict resolution

| KPI | Canonical decision | Implementation |
|---|---|---|
| `total_patients` | COUNT(DISTINCT patient_id) on arrival_datetime; not additive across months. | No formula change; reconciliation test added. |
| `total_revenue` | Gross invoice revenue; `revenue` alias removed. | Gross remains on overview/hospital KPI cards under `total_revenue`. |
| `revenue` | Net invoice revenue; canonical API key on finance and charts. | All chart/trend responses now use net for `revenue`. |
| `collection_rate` | collections / net_revenue * 100, uncapped; >100 flagged. | Cap removed from both gold models, glossary, API and tests. |
| `patient_satisfaction` | AVG(rating)/5*100, unit percent. | Ambiguous percent alias `average_satisfaction` removed. |
| `average_satisfaction` | AVG(rating), unit score 1-5. | Kept as score on experience endpoint; `average_satisfaction_score` is an alias. |
| `average_investigation_time` | Canonical long-form ID; NULL durations excluded from weight. | API now emits long form plus `avg_investigation_time` alias; weighted-null bug fixed. |

Additional duplicate API IDs were resolved: `average_los` is discharge-weighted everywhere;
the quality-domain `readmission_rate` now uses the canonical readmissions/discharges formula;
`no_show_rate`, `total_beds`, `admissions` and `patient_satisfaction` duplicates share one definition at different grains.

## 5. Revenue, collection and satisfaction reconciliation

- `gross_revenue = net_revenue + discounts + adjustments` (adjustments = 0 in generated data).
- `discounts = gross_amount - net_amount`; `net_revenue = invoice_paid_amount + balance_amount`.
- `payments_collected = cleared positive payments - cleared refunds`; cash-basis, therefore not equal to invoice paid across different date windows.
- `collection_rate = payments_collected / net_revenue * 100`, uncapped; >100% is valid and flagged.
- `patient_satisfaction = average_satisfaction / 5 * 100`; both values come from the same `silver_feedback.rating` field.
- `average_investigation_time` excludes NULL durations from numerator and denominator.

Reproduced against the regenerated DuckDB (`RUN_20261120_010`):

| Measure | Value |
|---|---:|
| Distinct encounter patients | 15,119 |
| Gross revenue | 127,704,922.53 |
| Discounts (gross - net) | 9,561,719.77 |
| Net revenue | 118,143,202.76 |
| Invoice paid amount | 76,092,132.66 |
| Invoice outstanding balance | 42,051,070.10 |
| Cleared collections net of refunds | 65,336,298.37 |
| Aggregate collection rate | 55.3026% (uncapped) |
| Department-month rows >100% | 279 (flagged, not clipped) |
| Hospital-month rows >100% | 0 |
| Gold satisfaction score / percentage | 3.836235 / 76.720902 |
| Null-excluded investigation mean (days) | 7.062766 |

Before/after reconciliation examples:

| KPI | Before | After |
|---|---|---|
| `total_patients` | Monthly gold values summed to 80,877, double-counting return patients | `COUNT(DISTINCT patient_id)` = 15,119 |
| `revenue` / `total_revenue` | `revenue` emitted gross 127,704,922.53 as an alias | `total_revenue` = gross 127,704,922.53; `revenue` = net 118,143,202.76 |
| `collection_rate` | Capped at 100; 279 department-month values hidden; capped monthly mean 55.4734 | Uncapped aggregate 55.3026; 279 values above 100 flagged, not clipped |
| `average_satisfaction` | Percent (77.169231) and score (3.858462) shared one name | `average_satisfaction` = score 3.836235; `patient_satisfaction` = percent 76.720902 |
| Investigation time | API returned 6.419165 days by counting NULL-duration incidents in the weight | Canonical long-form ID returns 7.062766 days; short ID is an alias |

## 6. Files changed

- `analytics/kpi_definitions/kpis.json`
- `analytics/kpi_definitions/canonicalize.py`
- `analytics/kpi_definitions/write_audit_report.py`
- `analytics/sql/02_gold_hospital_monthly.sql`
- `analytics/sql/05_gold_bed_utilization.sql`
- `analytics/sql/06_gold_financial_performance.sql`
- `api/services/kpi_specs.py`
- `api/routes/overview.py`
- `api/routes/hospitals.py`
- `etl/db.py`
- `etl/pipeline.py`
- `etl/quality.py`
- `web/lib/page-configs.ts`
- `web/lib/format.ts`
- `web/components/KpiGlossaryPage.tsx`
- `docs/kpi_glossary.md`
- `docs/kpi_integrity_audit.md`
- `CONTRACT.md`
- `tests/test_kpi_contract.py`
- `tests/test_gold.py`

## 7. Reconciliation tests

`tests/test_kpi_contract.py` asserts: contract completeness and uniqueness; alias collisions;
API/frontend/contract coverage; every configured frontend KPI key exists in its page API response;
gross vs net KPI identity; distinct-patient count; satisfaction scale; collection-rate cap removal
and NULL denominator; investigation ID/weighted-null correctness; hospital/date/department filters;
boundary and empty date ranges; glossary contract fields; date-filter column validity; revenue
reconciliation from silver invoices; and API-vs-gold value equality.
`tests/test_gold.py` no longer treats `collection_rate` as bounded by 100 and instead checks non-negative plus NULL denominator behavior.

## 8. Gate evidence

- `ruff check .`: PASS (0 errors).
- `python -m pytest -q`: PASS (108 passed, 2 non-failing deprecation warnings).
- `python scripts/verify_project.py`: PASS (bronze, manifest, DuckDB and all API endpoints).
- Pipeline `RUN_20261120_010`: SUCCESS; 1,588,637 source rows; 1,585,818 valid rows; 2,819 quarantined rows; 304/304 DQ rules pass; 12 gold models materialised.
- `npm run lint`, `npm run typecheck`, `npm run build`: PASS.
- Playwright (`npx playwright test --config=e2e/playwright.config.ts`): PASS (18 passed, chromium + mobile).
- Frontend contract resolution: all 15 configured page KPI endpoints return every configured frontend KPI key.

## 9. Full 190-KPI inventory

| ID | Name | Unit | Formula | Source tables | Date column | Aliases | Status | Findings |
|---|---|---|---|---|---|---|---|---|
| `total_patients` | Total Patients | count | `COUNT(DISTINCT patient_id)` | silver_encounters | arrival_datetime | — | active | none |
| `total_encounters` | Total Encounters | count | `COUNT(encounter_id)` | silver_encounters | arrival_datetime | patient_volume | active | none |
| `total_admissions` | Total Admissions | count | `COUNT(admission_id)` | silver_admissions | admission_datetime | — | active | none |
| `total_revenue` | Total Revenue | currency | `SUM(gross_amount)` | silver_invoices | invoice_date | — | active | none |
| `net_collections` | Net Collections | currency | `SUM(CASE WHEN LOWER(COALESCE(status,'')) = 'cleared' THEN COALESCE(amount,0) ELSE 0 END) - SUM(CASE WHEN LOWER(COALES...` | silver_payments, silver_invoices | payment_date | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `average_occupancy` | Average Occupancy | percent | `occupied_bed_days / available_bed_days * 100` | silver_bed_snapshots | snapshot_datetime | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `average_los` | Average Length of Stay | days | `AVG(los_days) FILTER (discharge_datetime IS NOT NULL)` | silver_admissions | discharge_datetime | los | active | none |
| `patient_satisfaction` | Patient Satisfaction | percent | `AVG(rating)/5*100` | silver_feedback | visit_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `no_show_rate` | No-Show Rate | percent | `COUNT(*) FILTER (WHERE status = 'No-show') * 100.0 / NULLIF(COUNT(*) FILTER (WHERE status IN ('Completed','No-show'))...` | silver_appointments | appointment_date | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `claim_denial_rate` | Claim Denial Rate | percent | `denied / (approved + denied) * 100` | silver_claims | claim_date | — | alias | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `collection_rate` | Collection Rate | percent | `collections / net_revenue * 100` | silver_payments, silver_invoices | payment_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `hospitals_selected` | Hospitals Selected | count | `COUNT(DISTINCT hospital_id)` | dim_hospital | — | — | active | none |
| `total_beds` | Total Beds | count | `SUM(beds)` | dim_hospital | — | — | active | none |
| `patients` | Patients | count | `COUNT(DISTINCT patient_id)` | silver_encounters | arrival_datetime | — | active | none |
| `patient_volume` | Patient Volume | count | `COUNT(encounter_id)` | silver_encounters | arrival_datetime | — | alias | none |
| `revenue` | Revenue | currency | `SUM(net_amount)` | silver_invoices | invoice_date | — | api_only | Backend producer has no explicit frontend card (chart/table or API-only consumer). |
| `average_satisfaction` | Average Satisfaction Score | score | `AVG(rating)` | silver_feedback | visit_date | average_satisfaction_score | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `occupancy` | Occupancy Rate | percent | `occupied_bed_days / available_bed_days * 100` | silver_bed_snapshots | snapshot_datetime | occupancy_rate | active | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `los` | Length of Stay | days | `AVG(los_days) discharged only` | silver_admissions | discharge_datetime | — | alias | none |
| `staff_count` | Staff Count | count | `COUNT(DISTINCT staff_id)` | silver_shifts | shift_date | — | active | none |
| `scheduled_appointments` | Scheduled Appointments | count | `COUNT(appointment_id)` | silver_appointments | appointment_date | — | active | none |
| `completed_appointments` | Completed Appointments | count | `COUNT(*) FILTER (status='Completed')` | silver_appointments | appointment_date | — | active | none |
| `cancelled_appointments` | Cancelled Appointments | count | `COUNT(*) FILTER (status='Cancelled')` | silver_appointments | appointment_date | — | active | none |
| `no_show_appointments` | No-Show Appointments | count | `COUNT(*) FILTER (status='No-show')` | silver_appointments | appointment_date | — | active | none |
| `average_wait_for_appointment` | Average Wait for Appointment | days | `AVG(lead_days)` | silver_appointments | appointment_date | avg_wait_appointment | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `average_checkin_waiting_time` | Average Check-in Waiting Time | minutes | `AVG(waiting_minutes)` | silver_appointments | appointment_date | avg_checkin_wait | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `appointment_utilization` | Appointment Utilization | percent | `completed / scheduled * 100` | silver_appointments | appointment_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `same_day_appointment_pct` | Same-Day Appointment Percentage | percent | `COUNT(lead_days=0) / scheduled * 100` | silver_appointments | appointment_date | — | alias | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `rescheduling_rate` | Rescheduling Rate | percent | `COUNT(rescheduled_flag) / scheduled * 100` | silver_appointments | appointment_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `emergency_visits` | Emergency Visits | count | `COUNT(*) FILTER (encounter_type='Emergency')` | silver_encounters | arrival_datetime | — | active | none |
| `average_triage_time` | Average Triage Time | minutes | `AVG(triage_datetime - arrival_datetime)/60 min` | silver_encounters | arrival_datetime | avg_triage_time | alias | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `average_waiting_time` | Average Waiting Time | minutes | `AVG(waiting_minutes)` | silver_encounters | arrival_datetime | avg_waiting_time | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `average_treatment_time` | Average Treatment Time | minutes | `AVG(treatment_minutes)` | silver_encounters | arrival_datetime | avg_treatment_time | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `patients_admitted` | Patients Admitted | count | `COUNT(*) FILTER (disposition='Admit')` | silver_encounters | arrival_datetime | — | active | none |
| `patients_discharged` | Patients Discharged | count | `COUNT(*) FILTER (disposition='Discharge')` | silver_encounters | arrival_datetime | — | active | none |
| `patients_transferred` | Patients Transferred | count | `COUNT(*) FILTER (disposition='Transfer')` | silver_encounters | arrival_datetime | — | active | none |
| `left_without_being_seen` | Left Without Being Seen | count | `COUNT(*) FILTER (disposition='LWBS')` | silver_encounters | arrival_datetime | left_without_seen | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `emergency_throughput` | Emergency Throughput | visits/day | `emergency_visits / days_in_period` | silver_encounters | arrival_datetime | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `critical_patient_volume` | Critical Patient Volume | count | `COUNT(*) FILTER (critical_flag)` | silver_encounters | arrival_datetime | — | active | none |
| `available_beds` | Available Beds | count | `SUM(CASE WHEN NOT COALESCE(blocked_flag, FALSE) THEN 1 ELSE 0 END)` | silver_bed_snapshots | snapshot_datetime | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `occupied_beds` | Occupied Beds | count | `COUNT(*) FILTER (status='Occupied')` | silver_bed_snapshots | snapshot_datetime | — | active | none |
| `blocked_beds` | Blocked Beds | count | `COUNT(*) FILTER (status='Blocked')` | silver_bed_snapshots | snapshot_datetime | — | active | none |
| `occupancy_rate` | Occupancy Rate | percent | `occupied_bed_days / available_bed_days * 100` | silver_bed_snapshots | snapshot_datetime | occupancy | active | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `bed_turnover_rate` | Bed Turnover Rate | ratio | `discharges / total_beds` | silver_admissions, silver_bed_snapshots | discharge_datetime | — | alias | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `average_discharge_time` | Average Discharge Time | minutes | `AVG(date_part('hour', discharge_datetime))` | silver_admissions | discharge_datetime | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `discharges` | Discharges | count | `COUNT(discharge_datetime)` | silver_admissions | discharge_datetime | — | active | none |
| `admissions` | Admissions | count | `COUNT(admission_id)` | silver_admissions | admission_datetime | — | active | none |
| `readmission_rate` | Readmission Rate | percent | `readmissions / discharges * 100` | silver_admissions | discharge_datetime | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `average_boarding_time` | Average Boarding Time | hours | `AVG(boarding_hours)` | silver_admissions | admission_datetime | boarding_hours | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `scheduled_procedures` | Scheduled Procedures | count | `COUNT(procedure_id)` | silver_procedures | scheduled_start | — | active | none |
| `completed_procedures` | Completed Procedures | count | `COUNT(*) FILTER (status='Completed')` | silver_procedures | scheduled_start | — | active | none |
| `cancelled_procedures` | Cancelled Procedures | count | `COUNT(*) FILTER (status='Cancelled')` | silver_procedures | scheduled_start | — | active | none |
| `cancellation_rate` | Procedure Cancellation Rate | percent | `cancelled / scheduled * 100` | silver_procedures | scheduled_start | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `average_procedure_duration` | Average Procedure Duration | minutes | `AVG(duration_minutes)` | silver_procedures | actual_start | avg_procedure_duration | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `or_utilization` | OR Utilization | percent | `SUM(duration_minutes) / (rooms * available_minutes) * 100` | silver_procedures | actual_start | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `first_case_on_time_start_rate` | First-Case On-Time Start Rate | percent | `COUNT(delay_minutes<=15) / first_cases * 100` | silver_procedures | scheduled_start | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `procedure_turnaround_time` | Procedure Turnaround Time | minutes | `AVG(date_diff('minute', actual_end, (SELECT MIN(s2.scheduled_start) FROM silver_procedures s2 WHERE s2.or_room = silv...` | silver_procedures | actual_end | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `delayed_procedures` | Delayed Procedures | count | `COUNT(*) FILTER (delay_minutes>0)` | silver_procedures | scheduled_start | — | active | none |
| `procedure_revenue` | Procedure Revenue | currency | `SUM(revenue)` | silver_procedures | actual_start | — | active | none |
| `total_lab_orders` | Total Lab Orders | count | `COUNT(lab_order_id)` | silver_lab_orders | ordered_at | — | active | none |
| `completed_tests` | Completed Tests | count | `COUNT(*) FILTER (status='Completed')` | silver_lab_orders | ordered_at | — | active | none |
| `pending_tests` | Pending Tests | count | `COUNT(*) FILTER (status='Pending')` | silver_lab_orders | ordered_at | — | active | none |
| `cancelled_tests` | Cancelled Tests | count | `COUNT(*) FILTER (status='Cancelled')` | silver_lab_orders | ordered_at | — | active | none |
| `average_turnaround_time` | Average Turnaround Time | minutes | `AVG(tat_minutes)` | silver_lab_results | result_at | avg_tat | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `median_turnaround_time` | Median Turnaround Time | minutes | `MEDIAN(tat_minutes)` | silver_lab_results | result_at | median_tat | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `sla_compliance_rate` | SLA Compliance Rate | percent | `results_within_sla / timed_results * 100` | silver_lab_results, dim_lab_test | result_at | sla_compliance | alias | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `delayed_results` | Delayed Results | count | `COUNT(*) FILTER (tat_minutes > sla_minutes)` | silver_lab_results, dim_lab_test | result_at | — | active | none |
| `critical_results` | Critical Results | count | `COUNT(*) FILTER (is_critical)` | silver_lab_results | result_at | — | active | none |
| `laboratory_revenue` | Laboratory Revenue | currency | `SUM(invoice_lines.line_amount) FILTER (service_category='Diagnostics')` | silver_invoice_lines, silver_invoices | invoice_date | — | active | none |
| `prescriptions` | Prescriptions | count | `COUNT(prescription_id)` | silver_prescriptions | prescribed_date | — | active | none |
| `items_prescribed` | Items Prescribed | count | `SUM(quantity)` | silver_prescriptions | prescribed_date | — | active | none |
| `items_dispensed` | Items Dispensed | count | `SUM(quantity_dispensed)` | silver_dispensing | dispensed_date | — | active | none |
| `pending_prescriptions` | Pending Prescriptions | count | `COUNT(*) FILTER (status='Pending')` | silver_prescriptions | prescribed_date | — | active | none |
| `dispensing_completion_rate` | Dispensing Completion Rate | percent | `items_dispensed / items_prescribed * 100` | silver_dispensing, silver_prescriptions | dispensed_date | dispensing_completion | alias | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `medication_revenue` | Medication Revenue | currency | `SUM(prescriptions.amount)` | silver_prescriptions | prescribed_date | — | active | none |
| `average_prescription_value` | Average Prescription Value | currency | `AVG(amount)` | silver_prescriptions | prescribed_date | avg_prescription_value | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `stockout_medication_count` | Stockout Medication Count | count | `SUM(stockouts) FILTER (WHERE category = 'Pharmacy')` | silver_inventory_movements | movement_date | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `expired_medication_value` | Expired Medication Value | currency | `SUM(ABS(quantity)*unit_cost) FILTER (movement_type='Expiry')` | silver_inventory_movements | movement_date | — | active | none |
| `pharmacy_waste` | Pharmacy Waste | currency | `SUM(ABS(quantity)*unit_cost) FILTER (movement_type='Waste')` | silver_inventory_movements | movement_date | — | active | none |
| `gross_revenue` | Gross Revenue | currency | `SUM(gross_amount)` | silver_invoices | invoice_date | — | active | none |
| `net_revenue` | Net Revenue | currency | `SUM(net_amount)` | silver_invoices | invoice_date | — | active | none |
| `total_billed` | Total Billed | currency | `SUM(gross_amount)` | silver_invoices | invoice_date | — | active | none |
| `total_collected` | Total Collected | currency | `SUM(CASE WHEN LOWER(COALESCE(status,'')) = 'cleared' THEN COALESCE(amount,0) ELSE 0 END)` | silver_payments | payment_date | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `outstanding_receivables` | Outstanding Receivables | currency | `SUM(balance_amount)` | silver_invoices | invoice_date | — | active | none |
| `average_revenue_per_encounter` | Average Revenue per Encounter | currency | `net_revenue / encounters` | silver_invoices, silver_encounters | invoice_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `average_invoice_value` | Average Invoice Value | currency | `AVG(net_amount)` | silver_invoices | invoice_date | avg_invoice_value | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `refund_amount` | Refund Amount | currency | `SUM(ABS(amount)) FILTER (payment_type='Refund')` | silver_payments | payment_date | — | active | none |
| `writeoff_amount` | Write-off Amount | currency | `SUM(balance_amount) FILTER (invoice_status='Overdue')` | silver_invoices | invoice_date | — | active | none |
| `revenue_growth` | Revenue Growth | percent | `(net_revenue - LAG(net_revenue)) / LAG(net_revenue) * 100` | silver_invoices | invoice_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `revenue_per_hospital_department` | Revenue per Hospital Department | currency | `SUM(net_amount) OVER (PARTITION BY hospital_id, department_id)` | silver_invoices, silver_encounters | invoice_date | — | unused_definition_documented | Glossary pseudo-SQL was corrected to executable form.; No backend producer and no frontend card; retained and recorde... |
| `claims_submitted` | Claims Submitted | count | `COUNT(claim_id)` | silver_claims | claim_date | — | active | none |
| `claims_approved` | Claims Approved | count | `COUNT(*) FILTER (status='Approved')` | silver_claims | claim_date | — | active | none |
| `claims_denied` | Claims Denied | count | `COUNT(*) FILTER (status='Denied')` | silver_claims | claim_date | — | active | none |
| `denial_rate` | Denial Rate | percent | `denied / (approved + denied) * 100` | silver_claims | claim_date | claim_denial_rate | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `pending_claims` | Pending Claims | count | `COUNT(*) FILTER (status IN ('Pending','Under review'))` | silver_claims | claim_date | — | active | none |
| `total_claimed_amount` | Total Claimed Amount | currency | `SUM(claim_amount)` | silver_claims | claim_date | — | active | none |
| `approved_amount` | Approved Amount | currency | `SUM(approved_amount)` | silver_claims | claim_date | — | active | none |
| `denied_amount` | Denied Amount | currency | `SUM(claim_amount - approved_amount) FILTER (status='Denied')` | silver_claims | claim_date | — | active | none |
| `paid_amount` | Paid Amount | currency | `SUM(paid_amount)` | silver_claims | claim_date | — | active | none |
| `average_processing_time` | Average Processing Time | days | `AVG(processing_days)` | silver_claims | claim_date | avg_processing_time | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `appeal_success_rate` | Appeal Success Rate | percent | `approved_appeals / appeals * 100` | silver_claim_events, silver_claims | event_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `outstanding_claim_value` | Outstanding Claim Value | currency | `SUM(claim_amount - paid_amount)` | silver_claims | claim_date | — | active | none |
| `total_employees` | Total Employees | count | `COUNT(DISTINCT staff_id)` | silver_shifts | shift_date | — | active | none |
| `active_employees` | Active Employees | count | `COUNT(*) FILTER (status='Active')` | dim_staff | — | — | active | none |
| `scheduled_hours` | Scheduled Hours | hours | `SUM(scheduled_hours)` | silver_shifts | shift_date | — | active | none |
| `worked_hours` | Worked Hours | hours | `SUM(actual_hours)` | silver_shifts | shift_date | — | active | none |
| `overtime_hours` | Overtime Hours | hours | `SUM(overtime_hours)` | silver_shifts | shift_date | — | active | none |
| `absence_rate` | Absence Rate | percent | `SUM(absence_rate * headcount) / NULLIF(SUM(headcount), 0)` | silver_attendance, silver_shifts | attendance_date | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `shift_coverage` | Shift Coverage | percent | `SUM(coverage_pct * headcount) / NULLIF(SUM(headcount), 0)` | silver_shifts | shift_date | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `staffing_shortage` | Staffing Shortage | hours | `SUM(CASE WHEN coverage_pct < 100 THEN 1 ELSE 0 END)` | silver_shifts | shift_date | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `nurse_to_patient_ratio` | Nurse-to-Patient Ratio | ratio | `nurse_headcount / encounters` | silver_shifts, dim_staff, silver_encounters | shift_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `physician_utilization` | Physician Utilization | percent | `worked_doctors / scheduled_doctors * 100` | silver_shifts, dim_doctor | shift_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `workforce_cost` | Workforce Cost | currency | `SUM(actual_hours * hourly_rate)` | silver_shifts, dim_staff | shift_date | — | active | none |
| `open_staffing_gaps` | Open Staffing Gaps | hours | `SUM(GREATEST(100 - coverage_pct, 0) / 100.0)` | silver_shifts | shift_date | — | active | Glossary pseudo-SQL was corrected to executable form.; Formula text lacks an explicit NULLIF; executable specs use NU... |
| `inventory_value` | Inventory Value | currency | `SUM(GREATEST(cum_qty,0)*unit_cost)` | silver_inventory_movements, dim_inventory_item | movement_date | — | active | none |
| `total_skus` | Total SKUs | count | `COUNT(DISTINCT item_id)` | silver_inventory_movements | movement_date | — | active | none |
| `stock_available` | Stock Available | count | `COUNT(DISTINCT item_id) FILTER (cum_qty>0)` | silver_inventory_movements | movement_date | — | active | none |
| `low_stock_items` | Low-Stock Items | count | `COUNT(DISTINCT item_id) FILTER (cum_qty<=reorder_level)` | silver_inventory_movements, dim_inventory_item | movement_date | low_stock | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `stockout_items` | Stockout Items | count | `COUNT(DISTINCT item_id) FILTER (cum_qty<=0)` | silver_inventory_movements | movement_date | stockouts | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `expiring_items` | Expiring Items | count | `COUNT(DISTINCT item_id) FILTER (WHERE CAST(expiry_date AS DATE) <= CAST($date_to AS DATE) + INTERVAL '90' DAY)` | silver_inventory_movements | expiry_date | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `expired_inventory_value` | Expired Inventory Value | currency | `SUM(ABS(quantity)*unit_cost) FILTER (movement_type='Expiry')` | silver_inventory_movements | movement_date | — | active | none |
| `inventory_turnover` | Inventory Turnover | ratio | `issue_value / inventory_value` | silver_inventory_movements | movement_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `purchase_orders` | Purchase Orders | count | `COUNT(po_id)` | silver_purchase_orders | order_date | — | active | none |
| `procurement_value` | Procurement Value | currency | `SUM(total_amount)` | silver_purchase_orders | order_date | — | active | none |
| `supplier_delivery_performance` | Supplier Delivery Performance | percent | `SUM(supplier_on_time_rate * inventory_value) / NULLIF(SUM(inventory_value), 0)` | silver_purchase_orders | received_date | supplier_delivery | alias | Duplicate display name; disambiguated by canonical ID and unit.; Glossary pseudo-SQL was corrected to executable form. |
| `inventory_waste` | Inventory Waste | currency | `SUM(ABS(quantity)*unit_cost) FILTER (movement_type='Waste')` | silver_inventory_movements | movement_date | — | active | none |
| `total_feedback` | Total Feedback | count | `COUNT(feedback_id)` | silver_feedback | visit_date | — | active | none |
| `average_satisfaction_score` | Average Satisfaction Score | score | `AVG(rating)` | silver_feedback | visit_date | average_satisfaction | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `satisfaction_percentage` | Satisfaction Percentage | percent | `AVG(rating)/5*100` | silver_feedback | visit_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `net_promoter_score` | Net Promoter Score | score | `(promoters - detractors) / total * 100` | silver_feedback | visit_date | nps | alias | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `positive_feedback_percentage` | Positive Feedback Percentage | percent | `COUNT(*) FILTER (WHERE sentiment_label ILIKE '%Positive%') * 100.0 / NULLIF(COUNT(*), 0)` | silver_feedback | visit_date | positive_feedback | alias | Duplicate display name; disambiguated by canonical ID and unit.; Glossary pseudo-SQL was corrected to executable form. |
| `negative_feedback_percentage` | Negative Feedback Percentage | percent | `COUNT(*) FILTER (WHERE sentiment_label ILIKE '%Negative%') * 100.0 / NULLIF(COUNT(*), 0)` | silver_feedback | visit_date | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `complaints` | Complaints | count | `COUNT(*) FILTER (complaint_flag)` | silver_feedback | visit_date | — | active | none |
| `complaint_resolution_time` | Complaint Resolution Time | days | `AVG(resolution_days) FILTER (complaint_flag)` | silver_feedback | visit_date | — | active | none |
| `response_rate` | Response Rate | percent | `COUNT(*) FILTER (WHERE resolution_status IS NOT NULL AND resolution_status <> '') * 100.0 / NULLIF(COUNT(*), 0)` | silver_feedback | visit_date | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `experience_trend` | Experience Trend | percent | `satisfaction_pct month over month` | silver_feedback | visit_date | — | active | none |
| `total_incidents` | Total Incidents | count | `COUNT(incident_id)` | silver_incidents | incident_date | — | active | none |
| `incident_rate` | Incident Rate | percent | `incidents / encounters * 100` | silver_incidents, silver_encounters | incident_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `falls_reported` | Falls Reported | count | `COUNT(*) FILTER (category='Fall')` | silver_incidents | incident_date | falls | alias | Duplicate display name; disambiguated by canonical ID and unit. |
| `medication_incidents` | Medication Incidents | count | `COUNT(*) FILTER (category='Medication')` | silver_incidents | incident_date | — | active | none |
| `infection_incidents` | Infection Incidents | count | `COUNT(*) FILTER (category='Infection')` | silver_incidents | incident_date | — | active | none |
| `incident_severity_distribution` | Incident Severity Distribution | count | `COUNT(*) GROUP BY severity` | silver_incidents | incident_date | — | active | none |
| `investigation_completion_rate` | Investigation Completion Rate | percent | `COUNT(investigation_complete_flag) / incidents * 100` | silver_incidents | incident_date | investigation_completion | alias | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `average_investigation_time` | Average Investigation Time | days | `AVG(investigation_days)` | silver_incidents | incident_date | avg_investigation_time | active | Duplicate display name; disambiguated by canonical ID and unit. |
| `compliance_indicator` | Compliance Indicator | percent | `COUNT(status IN ('Resolved','Closed')) / incidents * 100` | silver_incidents | incident_date | — | active | Formula text lacks an explicit NULLIF; executable specs use NULLIF. |
| `total_records_processed` | Total Records Processed | count | `SUM(silver.input_rows)` | manifests/pipeline_*.json | bronze manifest | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `valid_records` | Valid Records | count | `SUM(silver.output_rows)` | silver_*, manifests/pipeline_*.json | pipeline_runs | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `invalid_records` | Invalid Records | count | `SUM(quarantined_records)` | dq_failures | dq_failures | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `data_quality_score` | Data Quality Score | score | `SUM(category_weight * severity_weighted_pass_ratio)` | dq_results.json | json | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `duplicate_records` | Duplicate Records | count | `COUNT(*) FILTER (rule_id='PK_DUPLICATE')` | dq_failures | dq_failures | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `missing_values` | Missing Values | count | `COUNT(*) FILTER (category='Completeness')` | dq_rules, dq_failures | dq_failures | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `referential_integrity_violations` | Referential Integrity Violations | count | `COUNT(*) FILTER (category='Referential integrity')` | dq_rules, dq_failures | dq_failures | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `invalid_dates` | Invalid Dates | count | `COUNT(*) FILTER (rule_id IN ('REQUIRED_DATE_INVALID','DATE_ORDER_INVALID'))` | dq_failures | dq_failures | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `failed_checks` | Failed Checks | count | `COUNT(*) FILTER (passed=false)` | dq_results.json | json | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `quarantined_records` | Quarantined Records | count | `COUNT(*) FROM quarantine` | quarantine/*.jsonl | quarantine | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `latest_run` | Latest Run | text | `MAX(run_id)` | pipeline_runs | pipeline_runs | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `total_source_records` | Total Source Records | count | `source_records FROM pipeline_runs` | pipeline_runs | pipeline_runs | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `bronze_records` | Bronze Records | count | `SUM(bronze.tables.row_count)` | manifests/pipeline_*.json | bronze manifest | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `silver_records` | Silver Records | count | `valid_records FROM pipeline_runs` | pipeline_runs | pipeline_runs | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `gold_records` | Gold Records | count | `SUM(row_counts) FROM pipeline manifest` | manifests/pipeline_*.json | pipeline manifest | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `processing_duration` | Processing Duration | seconds | `end_time - start_time` | pipeline_runs | pipeline_runs | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `failed_stages` | Failed Stages | count | `COUNT(stage where status='failed')` | manifests/pipeline_*.json | pipeline manifest | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `last_successful_run` | Last Successful Run | text | `MAX(run_id) FILTER (status='success')` | pipeline_runs | pipeline_runs | — | active | Pipeline/DQ artifact, not an executable gold/silver KPI; emitted by system routes. |
| `avg_checkin_wait` | Average Check-in Waiting Time | minutes | `AVG(waiting_minutes)` | silver_appointments | appointment_date | average_checkin_waiting_time | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `avg_investigation_time` | Average Investigation Time | days | `AVG(investigation_days)` | silver_incidents | incident_date | average_investigation_time | alias | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `avg_invoice_value` | Average Invoice Value | currency | `AVG(net_amount)` | silver_invoices | invoice_date | average_invoice_value | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `avg_prescription_value` | Average Prescription Value | currency | `AVG(amount)` | silver_prescriptions | prescribed_date | average_prescription_value | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `avg_procedure_duration` | Average Procedure Duration | minutes | `AVG(duration_minutes)` | silver_procedures | actual_start | average_procedure_duration | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `avg_processing_time` | Average Processing Time | days | `AVG(processing_days)` | silver_claims | claim_date | average_processing_time | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `avg_tat` | Average Turnaround Time | minutes | `AVG(tat_minutes)` | silver_lab_results | result_at | average_turnaround_time | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `avg_treatment_time` | Average Treatment Time | minutes | `AVG(treatment_minutes)` | silver_encounters | arrival_datetime | average_treatment_time | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `avg_triage_time` | Average Triage Time | minutes | `AVG(triage_datetime - arrival_datetime)/60 min` | silver_encounters | arrival_datetime | average_triage_time | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `avg_wait_appointment` | Average Wait for Appointment | days | `AVG(lead_days)` | silver_appointments | appointment_date | average_wait_for_appointment | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `avg_waiting_time` | Average Waiting Time | minutes | `AVG(waiting_minutes)` | silver_encounters | arrival_datetime | average_waiting_time | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `bed_turnover` | Bed Turnover | ratio | `discharges / total_beds` | silver_admissions, silver_bed_snapshots | discharge_datetime | bed_turnover_rate | api_only | Formula text lacks an explicit NULLIF; executable specs use NULLIF.; Backend producer has no explicit frontend card (... |
| `boarding_hours` | Average Boarding Time | hours | `AVG(boarding_hours)` | silver_admissions | admission_datetime | average_boarding_time | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `dispensing_completion` | Dispensing Completion Rate | percent | `items_dispensed / items_prescribed * 100` | silver_dispensing, silver_prescriptions | dispensed_date | dispensing_completion_rate | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `encounters` | Encounters | count | `COUNT(encounter_id)` | silver_encounters | arrival_datetime | — | active | none |
| `falls` | Falls Reported | count | `COUNT(*) FILTER (category='Fall')` | silver_incidents | incident_date | falls_reported | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `investigation_completion` | Investigation Completion Rate | percent | `COUNT(investigation_complete_flag) / incidents * 100` | silver_incidents | incident_date | investigation_completion_rate | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `left_without_seen` | Left Without Being Seen | count | `COUNT(*) FILTER (disposition='LWBS')` | silver_encounters | arrival_datetime | left_without_being_seen | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `low_stock` | Low-Stock Items | count | `COUNT(DISTINCT item_id) FILTER (cum_qty<=reorder_level)` | silver_inventory_movements, dim_inventory_item | movement_date | low_stock_items | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `median_tat` | Median Turnaround Time | minutes | `MEDIAN(tat_minutes)` | silver_lab_results | result_at | median_turnaround_time | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `nps` | Net Promoter Score | score | `(promoters - detractors) / total * 100` | silver_feedback | visit_date | net_promoter_score | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `positive_feedback` | Positive Feedback Percentage | percent | `COUNT(sentiment_label='Positive') / feedback * 100` | silver_feedback | visit_date | positive_feedback_percentage | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `revenue_per_hospital` | Revenue per Hospital | currency | `SUM(net_amount) / NULLIF(COUNT(DISTINCT hospital_id), 0)` | silver_invoices, silver_encounters | invoice_date | — | active | Glossary pseudo-SQL was corrected to executable form. |
| `same_day_pct` | Same-Day Appointments | percent | `COUNT(lead_days=0) / scheduled * 100` | silver_appointments | appointment_date | same_day_appointment_pct | api_only | Formula text lacks an explicit NULLIF; executable specs use NULLIF.; Backend producer has no explicit frontend card (... |
| `sla_compliance` | SLA Compliance Rate | percent | `results_within_sla / timed_results * 100` | silver_lab_results, dim_lab_test | result_at | sla_compliance_rate | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Formula text lacks an explicit NULLIF; executable sp... |
| `stockouts` | Stockout Items | count | `COUNT(DISTINCT item_id) FILTER (cum_qty<=0)` | silver_inventory_movements | movement_date | stockout_items | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Backend producer has no explicit frontend card (char... |
| `supplier_delivery` | Supplier Delivery Performance | percent | `SUM(supplier_on_time_rate * inventory_value) / NULLIF(SUM(inventory_value), 0)` | silver_purchase_orders | received_date | supplier_delivery_performance | api_only | Duplicate display name; disambiguated by canonical ID and unit.; Glossary pseudo-SQL was corrected to executable form... |

## 10. Remaining issues and Phase 3 recommendation

Remaining issues, all non-blocking for Phase 2:

1. `revenue_per_hospital_department` is retained as an unused definition because the Phase 2 rule forbids deletion without a decision; it is documented in the inventory.
2. 39 glossary formula strings still contain `/` without the literal token `NULLIF`. Every executable API spec uses `NULLIF`, so there is no runtime zero-denominator risk; normalising the remaining prose is a documentation-only cleanup.
3. There is no Pydantic KPI response model. The generic envelope and loose TypeScript types were traced and deliberately left for the Phase 3 API contract work.
4. No public deployment URL exists; that belongs to Phase 5.

Exact Phase 3 recommendation: begin `feature/phase3-api-contract` from commit `49cd05d`, preserve every Phase 2 commit, and limit work to pagination, error envelopes, export limits, filtering contract and Docker configuration. Do not change a KPI definition without reopening this canonical contract and adding a reconciliation test.

