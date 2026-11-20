# HOSPITAL 360 - KPI Glossary

This glossary is the human-readable companion to the machine-readable KPI dictionary at
`analytics/kpi_definitions/kpis.json` (163 definitions). The JSON file is the canonical
registry consumed by the API (`GET /api/v1/kpis/glossary`) and the frontend KPI Glossary
page; this document explains each definition, its grain and its interpretation limits. If a
definition changes, update **both** files in the same change.

**Field-name mapping:** this document uses the blueprint labels. In `kpis.json` they appear
as `id` (KPI ID), `name`, `business_definition`, `formula`, `numerator`, `denominator`,
`grain`, `date_field`, `exclusions`, `source_tables` (Source), `dimensions`, `unit`,
`target`, `caveat` and `validation_test` (Validation), plus `category`.

No KPI value is hard-coded in the frontend. Every value comes from a gold table through the
API, with a comparison period, sparkline, unit and definition.

## Definition schema (blueprint section 12)

| Field | Meaning |
|---|---|
| KPI ID | Unique identifier, used verbatim as the API response key |
| Name | Display name |
| Business definition | What the metric means for hospital management |
| Formula | Calculation, expressed against numerator and denominator |
| Numerator | Top value of the ratio (or the summed measure for count KPIs) |
| Denominator | Bottom value of the ratio |
| Grain | Calculation grain (hospital x month, admission, claim, ...) |
| Date field | Date used for filtering and time series |
| Exclusions | What is deliberately left out |
| Source | Gold / silver tables and underlying transactional tables |
| Dimensions | Supported breakdowns |
| Target | Optional benchmark (targets here are illustrative, not measured facts) |
| Caveat | Interpretation limitation |
| Validation | Expected behaviour covered by `tests/test_kpis.py` |

> **Rate convention:** all rates are percentages in `0..100`. When a denominator is zero
> the database stores `NULL` (undefined), never `0`. This is a deliberate rule, not a
> missing-value defect.

---

## 1. Network KPIs

### `total_patients`
- **Name:** Total patients
- **Business definition:** Distinct synthetic patients with activity in the selected period.
- **Formula:** `COUNT(DISTINCT patient_id)`
- **Numerator:** Distinct `patient_id` values
- **Denominator:** n/a (count)
- **Grain:** Network x period (break down by hospital x month)
- **Date field:** earliest qualifying activity date (`registration_date` for registrations, otherwise the event date)
- **Exclusions:** duplicate bronze patient rows removed in silver; quarantined records
- **Source:** `gold_hospital_monthly.patients` <- `silver_patients`, `silver_encounters`, `silver_appointments`
- **Dimensions:** Hospital, department, specialty, month, patient type
- **Target:** 15,000+ over the full 24-month window (achieved count must be read from the manifest)
- **Caveat:** A patient counted at two hospitals in a period is distinct per hospital but deduplicated at network grain.
- **Validation:** unique IDs; date filter changes the count consistently; no double counting across grains.

### `total_encounters`
- **Name:** Total encounters
- **Business definition:** All outpatient, emergency and inpatient contacts.
- **Formula:** `COUNT(*)` of encounters
- **Numerator:** Encounter rows
- **Denominator:** n/a
- **Grain:** One row per encounter; aggregated to hospital x month
- **Date field:** `arrival_datetime`
- **Exclusions:** quarantined encounters with invalid patient/hospital references
- **Source:** `gold_hospital_monthly.encounters` <- `silver_encounters`
- **Dimensions:** Hospital, department, encounter type, triage category, month
- **Target:** 80,000+ over 24 months (target, not a measured result)
- **Caveat:** Encounter volume is not the same as unique patients; readmissions are separate encounters.
- **Validation:** volume reconciles between `gold_network_daily` and `gold_hospital_monthly`.

### `total_admissions`
- **Name:** Total admissions
- **Business definition:** Inpatient admissions started in the period.
- **Formula:** `COUNT(*)` of admissions
- **Numerator:** Admission rows
- **Denominator:** n/a
- **Grain:** One row per admission
- **Date field:** `admission_datetime`
- **Exclusions:** admissions without a valid encounter reference
- **Source:** `gold_hospital_monthly.admissions` <- `silver_admissions`
- **Dimensions:** Hospital, department, ward, admission type, month
- **Target:** 20,000+ over 24 months (target)
- **Caveat:** Admissions are counted at admission date; discharges in the same period are a separate measure.
- **Validation:** `admission_datetime <= discharge_datetime` for all discharged rows.

### `total_revenue`
- **Name:** Gross revenue
- **Business definition:** Gross charged amount before discounts, refunds and write-offs.
- **Formula:** `SUM(gross_amount)` of invoices
- **Numerator:** Gross invoice amounts
- **Denominator:** n/a
- **Grain:** One row per invoice; aggregated to hospital x month
- **Date field:** `invoice_date`
- **Exclusions:** negative/invalid amounts quarantined in silver; cancelled invoices
- **Source:** `gold_hospital_monthly.gross_revenue`, `gold_financial_performance.gross_revenue` <- `silver_invoices`
- **Dimensions:** Hospital, department, payer, service category, month
- **Target:** n/a (network total reported from data)
- **Caveat:** Gross revenue is not cash collected; do not confuse with `net_collections`.
- **Validation:** revenue reconciles between network-daily, hospital-monthly and finance gold tables.

### `revenue`
- **Name:** Revenue (net)
- **Business definition:** Net invoice revenue after discounts. This is the only meaning of the response key `revenue` across API endpoints.
- **Formula:** `SUM(net_amount)` of invoices
- **Numerator:** Invoice `net_amount`
- **Denominator:** n/a
- **Grain:** Hospital x month / department x month
- **Date field:** `invoice_date`
- **Exclusions:** negative/invalid amounts quarantined in silver; cancelled invoices
- **Source:** `gold_network_daily.revenue`, `gold_department_monthly.revenue`, `gold_hospital_monthly.net_revenue`
- **Dimensions:** Hospital, department, payer, service category, month
- **Target:** n/a
- **Caveat:** `total_revenue` is gross and must not be used interchangeably. `revenue` is no longer emitted as an alias of `total_revenue`.
- **Validation:** `gross_revenue = net_revenue + discounts + adjustments`; daily, hospital and department totals reconcile.

### `average_satisfaction`
- **Name:** Average Satisfaction Score
- **Business definition:** Mean survey rating on the documented 1-5 scale.
- **Formula:** `AVG(rating)`
- **Numerator:** Sum of ratings
- **Denominator:** Count of feedback submissions
- **Grain:** Hospital x month / department x month
- **Date field:** `visit_date`
- **Exclusions:** feedback with invalid patient/hospital references
- **Source:** `gold_patient_experience.avg_rating` <- `silver_feedback.rating`
- **Dimensions:** Hospital, department, category, month
- **Target:** 4.2 (illustrative)
- **Caveat:** Unit is `score`, never `percent`. `average_satisfaction_score` is a documented alias; `patient_satisfaction` is the percentage conversion.
- **Validation:** rating in 1..5; empty denominator -> `NULL`.

### `net_collections`
- **Name:** Net collections
- **Business definition:** Cash actually collected in the period.
- **Formula:** `SUM(paid_amount)` of cleared payments (refunds are negative)
- **Numerator:** Payment amounts, net of refunds
- **Denominator:** n/a
- **Grain:** One row per payment
- **Date field:** `payment_date`
- **Exclusions:** pending/failed payments; quarantined payments referencing absent invoices
- **Source:** `gold_hospital_monthly.collections`, `gold_financial_performance.collections` <- `silver_payments`
- **Dimensions:** Hospital, payer, payment method, month
- **Target:** n/a
- **Caveat:** Collections are cash-basis; revenue is accrual-basis. Refunds reduce the value.
- **Validation:** collection rate recomputes from the same collections and eligible net revenue.

### `average_occupancy`
- **Name:** Average occupancy rate
- **Business definition:** Share of available staffed bed capacity occupied during the period.
- **Formula:** `SUM(occupied_bed_days) / SUM(available_bed_days) * 100`
- **Numerator:** Occupied bed-days from bed snapshots
- **Denominator:** Available bed-days (occupied + available; **blocked beds excluded**)
- **Grain:** Hospital x month (also ward x month in `gold_bed_utilization`)
- **Date field:** `snapshot_datetime` rolled up to `month`
- **Exclusions:** blocked beds, duplicate snapshots, quarantined snapshots
- **Source:** `gold_hospital_monthly.occupancy_rate`, `gold_bed_utilization.occupancy_rate` <- `silver_bed_snapshots`
- **Dimensions:** Hospital, ward, bed type, month
- **Target:** illustrative 80-85% (not a measured result)
- **Caveat:** Denominator definition must be consistent; closed or blocked beds must not enter it. Duplicate snapshots inflate numerator and denominator alike and are detected in silver.
- **Validation:** occupied = available -> 100%; occupied = 0 -> 0%; no available bed-days -> `NULL`; blocked beds excluded; duplicates detected.

### `average_los`
- **Name:** Average length of stay
- **Business definition:** Mean inpatient days for **discharged** admissions.
- **Formula:** `SUM(los_days) / COUNT(discharged admissions)`
- **Numerator:** Total inpatient days of discharged admissions
- **Denominator:** Count of admissions with a discharge datetime
- **Grain:** One row per admission; aggregated to hospital x month
- **Date field:** `discharge_datetime` (period attribution by discharge)
- **Exclusions:** still-open admissions (no discharge); invalid date ordering
- **Source:** `gold_hospital_monthly.avg_los_days`, `gold_bed_utilization.avg_los_days` <- `silver_admissions`
- **Dimensions:** Hospital, department, ward, specialty, month
- **Target:** n/a
- **Caveat:** Excluding open admissions avoids censoring bias but means the metric lags current occupancy.
- **Validation:** open admissions do not affect the denominator; `los_days = discharge - admission`.

### `patient_satisfaction`
- **Name:** Patient satisfaction (percentage)
- **Business definition:** Mean 1-5 rating converted to a 0-100 scale. The raw 1-5 score is the separate `average_satisfaction` KPI.
- **Formula:** `AVG(rating) / 5 * 100`
- **Numerator:** Feedback-weighted mean of `satisfaction_pct`
- **Denominator:** Constant `5` (maximum rating), then feedback count for weighting
- **Grain:** Hospital x month / department x month
- **Date field:** `visit_date` at source; API filters the gold `month` column derived from it
- **Exclusions:** feedback with invalid patient/hospital references
- **Source:** `gold_patient_experience.satisfaction_pct` <- `silver_feedback.rating`
- **Dimensions:** Hospital, department, category, month
- **Target:** 80 percent (illustrative)
- **Caveat:** `average_satisfaction` is never an alias for this percentage. Sentiment labels are synthetic; response bias is not modelled.
- **Validation:** rating in 1..5; `satisfaction_pct = avg_rating / 5 * 100`; empty denominator -> `NULL`.

### `no_show_rate`
- **Name:** Appointment no-show rate
- **Business definition:** Share of eligible scheduled appointments that were not attended.
- **Formula:** `no_show_appointments / (completed + no_show) * 100`
- **Numerator:** Appointments with status `No-show`
- **Denominator:** Eligible scheduled appointments (`Completed` + `No-show`)
- **Grain:** Hospital x month (`gold_patient_access`), also department / specialty
- **Date field:** `appointment_date`
- **Exclusions:** `Cancelled` and future `Scheduled` appointments
- **Source:** `gold_hospital_monthly.no_show_rate`, `gold_patient_access.no_show_rate` <- `silver_appointments`
- **Dimensions:** Hospital, department, specialty, doctor, appointment type, month
- **Target:** lower is better; illustrative < 10%
- **Caveat:** Green means favourable here; lower is better. Excluding cancellations is a deliberate business rule.
- **Validation:** all completed -> 0%; all no-show -> 100%; cancelled excluded; empty denominator -> `NULL`; date filter changes both sides consistently.

### `claim_denial_rate`
- **Name:** Claim denial rate
- **Business definition:** Share of adjudicated claims that were denied.
- **Formula:** `denied / (approved + denied) * 100`
- **Numerator:** Claims with status `Denied`
- **Denominator:** Adjudicated claims (`Approved` + `Denied`)
- **Grain:** Hospital x payer x month
- **Date field:** `claim_date`
- **Exclusions:** `Pending`, `Under review`, `Appealed` claims (not yet adjudicated)
- **Source:** `gold_hospital_monthly.denial_rate`, `gold_claim_performance.denial_rate` <- `silver_claims`
- **Dimensions:** Hospital, payer, claim type, denial reason, month
- **Target:** lower is better; illustrative < 5%
- **Caveat:** Denied-then-approved-on-appeal claims remain denied at header status; appeal outcomes are tracked separately.
- **Validation:** all approved -> 0%; all denied -> 100%; pending excluded; empty denominator -> `NULL`.

### `collection_rate`
- **Name:** Collection rate
- **Business definition:** Share of eligible net revenue collected in the period.
- **Formula:** `collections / net_revenue * 100`
- **Numerator:** Payments collected (net of refunds)
- **Denominator:** Eligible net revenue (`net_amount` of invoices)
- **Grain:** Hospital x month / department x month
- **Date field:** `payment_date` for numerator, `invoice_date` for denominator (documented mixed basis)
- **Exclusions:** pending payments; write-offs and credit notes are documented, not silently removed from net revenue
- **Source:** `gold_hospital_monthly.collection_rate`, `gold_financial_performance.collection_rate` <- `silver_payments`, `silver_invoices`
- **Dimensions:** Hospital, payer, department, month
- **Target:** illustrative >= 95% (not a measured result)
- **Caveat:** Cash and invoice dates differ; the rate is a period indicator, not a cohort collection curve. Values above 100% are valid when prior-period balances are collected and are flagged, never capped. Gold tables, KPI specs and charts are all uncapped.
- **Validation:** recomputes from collections and net revenue; empty denominator -> `NULL`; refunds reduce the numerator; API value equals the unrounded gold expression at the same grain.

### `readmission_rate`
- **Name:** 30-day readmission rate
- **Business definition:** Share of discharges followed by another admission within 30 days.
- **Formula:** `readmissions / discharges * 100`
- **Numerator:** Discharged admissions with `readmission_flag = true`
- **Denominator:** Discharged admissions
- **Grain:** Hospital x month
- **Date field:** `discharge_datetime`
- **Exclusions:** open admissions; readmissions outside the 30-day window
- **Source:** `gold_hospital_monthly.readmission_rate`, `gold_quality_safety.readmission_rate` <- `silver_admissions`
- **Dimensions:** Hospital, department, specialty, month
- **Target:** lower is better
- **Caveat:** Synthetic flag is generated, not a linked clinical outcome.
- **Validation:** discharged-only denominator; empty denominator -> `NULL`.

---

## 2. Module-level KPIs

The table below uses the exact `id` values from `analytics/kpi_definitions/kpis.json`, which
is the authoritative registry for API response keys. All rates follow the `0..100` /
NULL-denominator rule. Full definitions (numerator, denominator, exclusions, dimensions,
target, caveat and validation test) for every row live in the JSON registry.

| Module | KPI ID | Formula / measure | Grain & date field | Exclusions / caveat | Validation focus |
|---|---|---|---|---|---|
| Access | `scheduled_appointments` | `COUNT(*)` | hospital x month, `appointment_date` | none | volume reconciles across appointment gold tables |
| Access | `completed_appointments` | `COUNT(*) WHERE status='Completed'` | hospital x month | cancelled / no-show excluded | completed + no-show + cancelled = scheduled |
| Access | `cancelled_appointments` | `COUNT(*) WHERE status='Cancelled'` | hospital x month | must carry reason | cancellation reason present |
| Access | `no_show_appointments` | `COUNT(*) WHERE status='No-show'` | hospital x month | cancelled excluded | drill-down returns matching records |
| Access | `average_wait_for_appointment` | `AVG(waiting_minutes)` | hospital x month | null waits excluded | non-negative |
| Access | `average_checkin_waiting_time` | `AVG(waiting_minutes)` at check-in | hospital x month | null waits excluded | non-negative |
| Access | `appointment_utilization` | completed / scheduled x100 | hospital x month | cancelled excluded | 0..100 or NULL |
| Access | `same_day_appointment_pct` | `COUNT(lead_days=0)/scheduled*100` | hospital x month | cancelled excluded | 0..100 or NULL |
| Access | `rescheduling_rate` | `COUNT(rescheduled_flag)/scheduled*100` | hospital x month | cancelled excluded | 0..100 or NULL |
| Emergency | `emergency_visits` | `COUNT(*) WHERE encounter_type='Emergency'` | hospital x month, `arrival_datetime` | n/a | matches encounter module totals |
| Emergency | `average_triage_time` | `AVG(triage_datetime - arrival_datetime)` | hospital x month | missing timestamps excluded | non-negative, triage after arrival |
| Emergency | `average_waiting_time` | `AVG(waiting_minutes)` | hospital x month | n/a | non-negative |
| Emergency | `average_treatment_time` | `AVG(treatment_minutes)` | hospital x month | n/a | non-negative |
| Emergency | `patients_admitted` | `COUNT(disposition='Admit')` | hospital x month | n/a | disposition allowlist |
| Emergency | `patients_discharged` | `COUNT(disposition='Discharge')` | hospital x month | n/a | disposition allowlist |
| Emergency | `patients_transferred` | `COUNT(disposition='Transfer')` | hospital x month | n/a | disposition allowlist |
| Emergency | `left_without_being_seen` | `COUNT(disposition='LWBS')` | hospital x month | n/a | disposition allowlist |
| Emergency | `critical_patient_volume` | `COUNT(critical_flag)` | hospital x month | n/a | boolean flag only |
| Inpatient | `total_beds` | licensed capacity | hospital, `dim_hospital.beds` | n/a | matches 3,450 network capacity |
| Inpatient | `available_beds` | snapshot state `Available` | hospital x ward x month, `snapshot_datetime` | blocked beds excluded | snapshot dedup |
| Inpatient | `occupied_beds` | snapshot state `Occupied` | hospital x ward x month | n/a | snapshot dedup |
| Inpatient | `blocked_beds` | snapshot state `Blocked` | hospital x ward x month | excluded from occupancy denominator | non-negative |
| Inpatient | `occupancy_rate` | occupied bed-days / available bed-days x100 | hospital x ward x month | blocked beds excluded | 0/100/NULL cases; duplicates detected |
| Inpatient | `bed_turnover_rate` | discharges / available beds | hospital x ward x month | blocked beds excluded | non-negative |
| Inpatient | `average_discharge_time` | mean discharge clock time | hospital x month | open admissions excluded | time within day bounds |
| Inpatient | `admissions`, `discharges` | admission / discharge counts | hospital x month | n/a | admit vs discharge reconcile |
| Inpatient | `readmission_rate` | readmissions / discharges x100 | hospital x month | discharged only | 0..100 or NULL |
| Inpatient | `average_boarding_time` | `AVG(boarding_hours)` | admission grain | open admissions excluded | non-negative |
| Procedures | `scheduled_procedures` | `COUNT(*)` | hospital x month, `scheduled_start` | n/a | scheduled = completed + cancelled + delayed |
| Procedures | `completed_procedures` | `COUNT(status='Completed')` | hospital x month | n/a | matches procedure fact |
| Procedures | `cancelled_procedures` | `COUNT(status='Cancelled')` | hospital x month | reason required | cancellation reason present |
| Procedures | `cancellation_rate` | cancelled / scheduled x100 | hospital x month | n/a | 0..100 or NULL |
| Procedures | `average_procedure_duration` | `AVG(duration_minutes)` | hospital x month | cancelled excluded | non-negative |
| Procedures | `or_utilization` | procedure minutes / available OR minutes x100 | hospital x OR x month | cancelled excluded | denominator documented; 0..100 or NULL |
| Procedures | `first_case_on_time_start_rate` | on-time first cases / first cases x100 | hospital x OR x month | n/a | 0..100 or NULL |
| Procedures | `procedure_turnaround_time` | mean room turnaround | hospital x OR x month | n/a | non-negative |
| Procedures | `delayed_procedures` | `COUNT(delay_minutes > 0)` | hospital x month | n/a | non-negative |
| Procedures | `procedure_revenue` | `SUM(revenue)` | hospital x month | cancelled excluded | non-negative |
| Diagnostics | `total_lab_orders` | `COUNT(*)` | hospital x month, `ordered_at` | n/a | matches lab gold volume |
| Diagnostics | `completed_tests` | `COUNT(status='Completed')` | hospital x test x month | held at result level | reconciles with `total_lab_orders` |
| Diagnostics | `pending_tests`, `cancelled_tests` | status counts | hospital x test x month | n/a | status allowlist |
| Diagnostics | `average_turnaround_time` | `AVG(tat_minutes)` | hospital x test x month | pending/cancelled excluded | result time >= order time |
| Diagnostics | `median_turnaround_time` | `MEDIAN(tat_minutes)` | hospital x test x month | pending excluded | <= max TAT |
| Diagnostics | `sla_compliance_rate` | `COUNT(tat <= sla_minutes)/completed*100` | hospital x test x month | pending excluded | 0..100 or NULL |
| Diagnostics | `delayed_results` | count breaching SLA | hospital x test x month | n/a | non-negative |
| Diagnostics | `critical_results` | `COUNT(is_critical)` | hospital x test x month | synthetic flag | boolean flag only |
| Pharmacy | `prescriptions` | `COUNT(*)` | hospital x month, `prescribed_date` | n/a | prescription -> dispensing link valid |
| Pharmacy | `items_prescribed`, `items_dispensed` | quantity sums | hospital x medication x month | cancelled excluded | dispensed <= prescribed |
| Pharmacy | `pending_prescriptions` | `COUNT(status='Pending')` | hospital x month | n/a | status allowlist |
| Pharmacy | `dispensing_completion_rate` | dispensed / prescribed x100 | hospital x month | cancelled excluded | 0..100 or NULL |
| Pharmacy | `medication_revenue` | `SUM(amount)` | hospital x month | negative amounts quarantined | non-negative |
| Pharmacy | `average_prescription_value` | `AVG(amount)` | hospital x month | n/a | non-negative |
| Pharmacy | `stockout_medication_count`, `expired_medication_value`, `pharmacy_waste` | stock events / values | hospital x month | n/a | non-negative |
| Finance | `net_revenue`, `total_billed`, `total_collected` | invoice / payment sums | hospital x month, `invoice_date` | refunds documented | net = gross - discount |
| Finance | `outstanding_receivables` | `SUM(balance_amount)` | hospital x month | n/a | balance = net - paid |
| Finance | `average_revenue_per_encounter` | net revenue / encounters | hospital x month | encounters = 0 -> NULL | non-negative |
| Finance | `average_invoice_value` | `AVG(net_amount)` | hospital x month | n/a | non-negative |
| Finance | `refund_amount`, `writeoff_amount` | refund / write-off totals | hospital x month, `payment_date` | refunds are negative payments | non-negative magnitude |
| Finance | `revenue_growth` | (current - prior)/prior x100 | hospital x month | no prior -> NULL | sign and NULL handling |
| Finance | `revenue_per_hospital_department` | net revenue by department | hospital x dept x month | n/a | reconciles with hospital total |
| Claims | `claims_submitted` | `COUNT(*)` | hospital x payer x month, `claim_date` | n/a | header count matches claims fact |
| Claims | `claims_approved`, `claims_denied` | adjudicated status counts | hospital x payer x month | pending excluded | payer breakdown reconciles |
| Claims | `denial_rate` | denied / (approved + denied) x100 | hospital x payer x month | pending excluded | 0..100 or NULL |
| Claims | `pending_claims` | `COUNT(status='Pending')` | hospital x payer x month | n/a | aging buckets reconcile |
| Claims | `total_claimed_amount`, `approved_amount`, `denied_amount`, `paid_amount` | amount sums | hospital x payer x month | n/a | paid <= approved <= claimed |
| Claims | `average_processing_time` | `AVG(processing_days)` | hospital x payer x month | pending excluded | non-negative |
| Claims | `appeal_success_rate` | successful appeals / appeals x100 | hospital x payer x month | no appeals -> NULL | 0..100 or NULL |
| Claims | `outstanding_claim_value` | claimed - paid | hospital x payer x month | n/a | non-negative |
| Workforce | `staff_count`, `total_employees`, `active_employees` | distinct staff counts | hospital x dept x month | n/a | active <= total |
| Workforce | `scheduled_hours`, `worked_hours`, `overtime_hours` | hour sums | hospital x dept x month, `shift_date` | n/a | overtime <= worked |
| Workforce | `absence_rate` | absent / scheduled x100 | hospital x dept x month | leave per definition | 0..100 or NULL |
| Workforce | `shift_coverage` | worked / scheduled x100 | hospital x dept x month | n/a | 0..100 or NULL |
| Workforce | `staffing_shortage`, `open_staffing_gaps` | uncovered demand | hospital x dept x month | n/a | non-negative |
| Workforce | `nurse_to_patient_ratio` | nurses / patients | hospital x month | patients = 0 -> NULL | non-negative |
| Workforce | `physician_utilization` | worked / available physician hours x100 | hospital x dept x month | n/a | 0..100 or NULL |
| Workforce | `workforce_cost` | `SUM(hours * hourly_rate)` | hospital x dept x month | n/a | matches staff rates |
| Inventory | `inventory_value` | `SUM(on_hand * unit_cost)` | hospital x category x month, `movement_date` | n/a | movements net correctly |
| Inventory | `total_skus`, `stock_available`, `low_stock_items`, `stockout_items`, `expiring_items` | stock-state counts | hospital x category x month | n/a | non-negative |
| Inventory | `expired_inventory_value`, `inventory_waste` | `Expiry` / `Waste` movement values | hospital x category x month | n/a | non-negative |
| Inventory | `inventory_turnover` | issues / average inventory value | hospital x category x month | denominator 0 -> NULL | non-negative |
| Inventory | `purchase_orders`, `procurement_value` | PO count / value | hospital x supplier x month | n/a | reconciles with PO lines |
| Inventory | `supplier_delivery_performance` | on-time receipts / receipts x100 | hospital x supplier x month | no receipts -> NULL | 0..100 or NULL |
| Experience | `total_feedback` | `COUNT(*)` | hospital x dept x month, `visit_date` | invalid refs excluded | matches gold count |
| Experience | `average_satisfaction` / `average_satisfaction_score` | `AVG(rating)` | hospital x dept x month | rating 1..5 | range 1..5 or NULL |
| Experience | `patient_satisfaction` / `satisfaction_percentage` | `AVG(rating)/5*100` | hospital x month | n/a | 0..100 or NULL |
| Experience | `net_promoter_score` | promoters% - detractors% | hospital x month | no feedback -> NULL | -100..100 or NULL |
| Experience | `positive_feedback_percentage`, `negative_feedback_percentage` | sentiment shares | hospital x month | synthetic labels | 0..100 or NULL |
| Experience | `complaints` | `COUNT(complaint_flag)` | hospital x month | n/a | complaint text synthetic |
| Experience | `complaint_resolution_time` | `AVG(resolution_days)` | hospital x month | open complaints excluded | non-negative |
| Experience | `response_rate` | resolved feedback / feedback x100 | hospital x month | no feedback -> NULL | 0..100 or NULL |
| Quality | `total_incidents` | `COUNT(*)` | hospital x dept x month, `incident_date` | n/a | severity allowlist |
| Quality | `incident_rate` | incidents / encounters x100 | hospital x month | encounters = 0 -> NULL | 0..100 or NULL |
| Quality | `falls_reported`, `medication_incidents`, `infection_incidents` | category counts | hospital x dept x month | n/a | category allowlist |
| Quality | `incident_severity_distribution` | counts by severity | hospital x month | n/a | severity allowlist |
| Quality | `investigation_completion_rate` | completed / incidents x100 | hospital x month | open incidents in denominator | 0..100 or NULL |
| Quality | `average_investigation_time` / `avg_investigation_time` | incident-weighted `AVG(investigation_days)` | hospital x dept x month | incomplete excluded from numerator and denominator | non-negative |
| Quality | `compliance_indicator` | documented composite | hospital x month | no clinical use | documented formula |

## Revenue reconciliation (Phase 2)

Invoices are the accrual source. The following definitions and identities are
tested against `silver_invoices` and the gold models; none of them forces gross
to equal net:

- **Gross revenue** — `SUM(gross_amount)`, the full charged amount before discounts.
- **Discounts** — `SUM(gross_amount - net_amount)`, contractual/payer reductions applied on the invoice.
- **Adjustments** — post-discount changes to the invoice amount. The generated data has no separate adjustment column, so this is defined as 0 rather than invented.
- **Refunds** — negative cash payments returned to a payer/patient. They reduce `payments_collected`; they are not invoice discounts.
- **Net revenue** — `SUM(net_amount)`, gross revenue less discounts and adjustments.
- **Payments collected** — cleared positive payments minus cleared refunds, on the payment date; a cash-basis measure.
- **Outstanding balance** — `SUM(balance_amount)` from invoices at the invoice grain.

- `gross_revenue = net_revenue + discounts + adjustments`
- `discounts = SUM(gross_amount - net_amount)`; generated data has no separate
  post-discount adjustment column, so `adjustments = 0` and is documented rather
  than invented.
- `net_revenue = invoice_paid_amount + invoice_balance_amount`
- `payments_collected = cleared positive payments - cleared refunds`; this is a
  cash-basis measure and is deliberately not equal to `invoice_paid_amount` when
  payment dates differ from invoice dates.
- `outstanding_balance = SUM(balance_amount)` from invoices; it is not
  `net_revenue - payments_collected` across different date windows.
- `collection_rate = payments_collected / net_revenue * 100`, uncapped. A value
  above 100% means prior-period balances were collected in the period and is
  flagged for review, not clipped.

## Interpretation rules

1. **Lower-is-better KPIs** (no-show, denial, absence, stockouts, LOS where context dictates):
   favourable direction is reversed in UI colouring. Green must never imply "more is better".
2. **NULL means undefined**, not zero. A card with a NULL denominator renders an empty
   state with the reason, not `0%`.
3. **Comparison periods** shift the date window by an equal number of days; they never
   mutate filters or the current selection.
4. **Drill-downs preserve context**: clicking a KPI carries date range, hospital and
   relevant department filters into the detail table and export.
5. **Synthetic-only caveat**: no KPI describes a real hospital and no KPI supports a
   clinical or operational decision in a real facility. See [methodology.md](methodology.md).
