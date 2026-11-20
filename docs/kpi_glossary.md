# HOSPITAL 360 - KPI Glossary

This glossary is the human-readable companion to the machine-readable KPI dictionary at
`analytics/kpi_definitions/kpis.json`. The JSON file is the canonical registry consumed by
the API (`GET /api/v1/kpis/glossary`) and the frontend KPI Glossary page; this document
explains each definition, its grain and its interpretation limits. If a definition changes,
update **both** files in the same change.

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
- **Name:** Patient satisfaction
- **Business definition:** Mean survey rating on a 1-5 scale.
- **Formula:** `AVG(rating)` (and `satisfaction_pct = share of ratings >= 4 * 100` in `gold_patient_experience`)
- **Numerator:** Sum of ratings; count of ratings >= 4
- **Denominator:** Count of feedback submissions
- **Grain:** Hospital x month / department x month
- **Date field:** `visit_date`
- **Exclusions:** feedback with invalid patient/hospital references
- **Source:** `gold_hospital_monthly.avg_satisfaction`, `gold_patient_experience.avg_rating` <- `silver_feedback`
- **Dimensions:** Hospital, department, category, month
- **Target:** n/a
- **Caveat:** Sentiment labels are synthetic, not AI analysis of real feedback. Response bias is not modelled.
- **Validation:** rating in 1..5; empty denominator -> `NULL`.

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
- **Caveat:** Cash and invoice dates differ; the rate is a period indicator, not a cohort collection curve. Values above 100% are possible if prior-period balances are collected and must be flagged, not clipped.
- **Validation:** recomputes from collections and net revenue; empty denominator -> `NULL`; refunds reduce the numerator.

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

The following KPIs appear on their module pages. The API keys match the `kpi_id` values in
`analytics/kpi_definitions/kpis.json`. All rates follow the `0..100` / NULL-denominator rule.

| Module | KPI ID | Formula / measure | Grain & date field | Exclusions / caveat | Validation focus |
|---|---|---|---|---|---|
| Appointments | `scheduled_appointments` | `COUNT(*)` | hospital x month, `appointment_date` | none | volume reconciles across appointment gold tables |
| Appointments | `completed_appointments` | `COUNT(*) WHERE status='Completed'` | hospital x month | cancelled / no-show excluded | completed + no-show + cancelled = scheduled |
| Appointments | `cancelled_appointments` | `COUNT(*) WHERE status='Cancelled'` | hospital x month | must carry reason | cancellation reason present |
| Appointments | `no_show_appointments` | `COUNT(*) WHERE status='No-show'` | hospital x month | cancelled excluded | drill-down returns matching records |
| Appointments | `avg_wait_minutes` | `AVG(waiting_minutes)` | hospital x month | null waits excluded | non-negative |
| Appointments | `avg_lead_days` | `AVG(lead_days)` | hospital x month | negative lead days quarantined | `lead_days = appointment - booking` |
| Appointments | `same_day_pct` | `COUNT(lead_days=0)/scheduled*100` | hospital x month | cancelled excluded | 0..100 or NULL |
| Appointments | `reschedule_rate` | `COUNT(rescheduled_flag)/scheduled*100` | hospital x month | cancelled excluded | 0..100 or NULL |
| Emergency | `emergency_visits` | `COUNT(*) WHERE encounter_type='Emergency'` | hospital x month, `arrival_datetime` | n/a | matches encounter module totals |
| Emergency | `avg_triage_minutes` | `AVG(triage_datetime - arrival_datetime)` | hospital x month | missing timestamps excluded | non-negative, triage after arrival |
| Emergency | `avg_treatment_minutes` | `AVG(treatment_minutes)` | hospital x month | n/a | non-negative |
| Emergency | `lwbs_count` | `COUNT(*) WHERE disposition='LWBS'` | hospital x month | n/a | disposition allowlist |
| Emergency | `critical_volume` | `COUNT(*) WHERE critical_flag` | hospital x month | n/a | boolean flag only |
| Inpatient | `occupancy_rate` | occupied bed-days / available bed-days x100 | hospital x ward x month, `snapshot_datetime` | blocked beds excluded | 0/100/NULL cases; duplicates detected |
| Inpatient | `bed_turnover` | discharges / available beds | hospital x ward x month | blocked beds excluded | non-negative |
| Inpatient | `boarding_hours` | `AVG(boarding_hours)` | admission grain | open admissions excluded | non-negative |
| Inpatient | `available_beds` | snapshot state `Available` | hospital x ward x month | blocked beds excluded | snapshot dedup |
| Procedures | `procedure_volume` | `COUNT(*)` | hospital x month, `scheduled_start` | n/a | completed + cancelled + delayed = scheduled |
| Procedures | `cancellation_rate` | cancelled / scheduled x100 | hospital x month | n/a | 0..100 or NULL |
| Procedures | `or_utilization` | procedure minutes / available OR minutes x100 | hospital x OR x month | cancelled procedures excluded | denominator documented; 0..100 or NULL |
| Procedures | `procedure_delay_minutes` | `AVG(delay_minutes)` | hospital x month | null delays excluded | non-negative |
| Diagnostics | `lab_orders` | `COUNT(*)` | hospital x month, `ordered_at` | n/a | matches lab gold volume |
| Diagnostics | `completed_tests` | `COUNT(labs status='Completed')` | hospital x test x month | held at result level | completion reconciles with `lab_orders` |
| Diagnostics | `avg_tat_minutes` | `AVG(tat_minutes)` | hospital x test x month | pending/cancelled excluded | result time >= order time |
| Diagnostics | `sla_rate` | `COUNT(tat <= sla_minutes)/completed*100` | hospital x test x month | pending excluded | 0..100 or NULL |
| Diagnostics | `critical_results` | `COUNT(is_critical)` | hospital x test x month | synthetic flag | boolean flag only |
| Pharmacy | `prescriptions` | `COUNT(*)` | hospital x month, `prescribed_date` | n/a | prescription -> dispensing link valid |
| Pharmacy | `dispensing_completion_rate` | dispensed / prescribed x100 | hospital x month | cancelled prescriptions excluded | 0..100 or NULL |
| Pharmacy | `avg_prescription_value` | `AVG(amount)` | hospital x month | negative amounts quarantined | non-negative |
| Finance | `net_revenue` | `SUM(net_amount)` | hospital x month, `invoice_date` | refunds/write-offs documented | net = gross - discount |
| Finance | `outstanding_balance` | `SUM(balance_amount)` | hospital x month | n/a | balance = net - paid |
| Finance | `avg_invoice_value` | `AVG(net_amount)` | hospital x month | n/a | non-negative |
| Finance | `refunds` | `SUM(-amount) WHERE type='Refund'` | hospital x month, `payment_date` | n/a | refunds are negative payments |
| Finance | `writeoffs` | documented write-off amount | hospital x month | not in payment fact unless present | reconciles with finance gold |
| Finance | `revenue_growth_pct` | (current - prior)/prior x100 | hospital x month | no prior period -> NULL | sign and NULL handling |
| Claims | `claims_submitted` | `COUNT(*)` | hospital x payer x month, `claim_date` | n/a | header count matches claims fact |
| Claims | `claims_approved` | `COUNT(status='Approved')` | hospital x payer x month | adjudicated only | payer breakdown reconciles |
| Claims | `claims_denied` | `COUNT(status='Denied')` | hospital x payer x month | adjudicated only | denial reason present |
| Claims | `avg_processing_days` | `AVG(processing_days)` | hospital x payer x month | pending claims excluded | non-negative |
| Claims | `appeal_success_rate` | successful appeals / appeals x100 | hospital x payer x month | no appeals -> NULL | 0..100 or NULL |
| Workforce | `scheduled_hours` | `SUM(scheduled_hours)` | hospital x dept x month, `shift_date` | n/a | non-negative |
| Workforce | `overtime_hours` | `SUM(overtime_hours)` | hospital x dept x month | n/a | overtime <= worked hours |
| Workforce | `absence_rate` | absent attendance / scheduled attendance x100 | hospital x dept x month | leave excluded per definition | 0..100 or NULL |
| Workforce | `coverage_pct` | worked hours / scheduled hours x100 | hospital x dept x month | n/a | 0..100 or NULL |
| Workforce | `workforce_cost` | `SUM(hours * hourly_rate)` | hospital x dept x month | n/a | matches staff rates |
| Inventory | `inventory_value` | `SUM(on_hand * unit_cost)` | hospital x category x month, `movement_date` | n/a | movements net correctly |
| Inventory | `stockouts` | count of stockout events | hospital x category x month | n/a | non-negative |
| Inventory | `expired_value` | value of `Expiry` movements | hospital x category x month | n/a | non-negative |
| Inventory | `supplier_on_time_rate` | on-time receipts / receipts x100 | hospital x supplier x month | no receipts -> NULL | 0..100 or NULL |
| Inventory | `turnover` | issues / average inventory value | hospital x category x month | n/a | denominator > 0 else NULL |
| Experience | `feedback_count` | `COUNT(*)` | hospital x dept x month, `visit_date` | invalid references excluded | matches gold count |
| Experience | `nps` | promoters% - detractors% | hospital x month | no feedback -> NULL | range -100..100 or NULL |
| Experience | `complaints` | `COUNT(complaint_flag)` | hospital x month | n/a | complaint text synthetic |
| Experience | `complaint_resolution_days` | `AVG(resolution_days)` | hospital x month | open complaints excluded | non-negative |
| Quality | `incidents` | `COUNT(*)` | hospital x dept x month, `incident_date` | n/a | severity allowlist |
| Quality | `incident_rate` | incidents / encounters x100 | hospital x month | encounters = 0 -> NULL | 0..100 or NULL |
| Quality | `investigation_completion_rate` | completed investigations / incidents x100 | hospital x month | open incidents included in denominator | 0..100 or NULL |
| Quality | `avg_investigation_days` | `AVG(investigation_days)` | hospital x month | incomplete investigations excluded | non-negative |

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
