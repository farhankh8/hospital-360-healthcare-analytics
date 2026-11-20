# HOSPITAL 360 - Data Dictionary

> **Source of truth:** `generator/schema.py` (`TABLES`). This document is generated
> from that module; if a column changes there, update this file in the same change.

## Conventions

- **Dtypes:** `string`, `int64`, `float64`, `bool`, `date`, `datetime64[ns]`
  (pandas tokens exactly as declared in `schema.py`).
- **Key:** `PK` = primary key, `FK` = foreign key (target table in parentheses).
- Bronze CSVs use these exact column names; silver keeps them after type/dedup/status
  cleaning; gold tables re-aggregate them (see `CONTRACT.md` section 3).
- Dates follow `START_DATE..END_DATE` (2025-01-01 .. 2026-12-31) unless noted.
- All data is synthetic. `birth_date`, contact-style fields and identifiers are fictional.

## Table index

| Layer | Tables |
|---|---|
| Dimensions | 16 |
| Transactional / fact-like | 23 |
| **Total** | **39** |

## Dimension tables

### `dim_hospital`

- **Grain:** One row per hospital (H01-H10)
- **Primary key:** `hospital_id`
- **Foreign keys:** none

| Column | Dtype | Key | Description |
|---|---|---|---|
| `hospital_id` | `string` | PK | H01..H10 |
| `hospital_name` | `string` | - | Facility name |
| `city` | `string` | - | City / district |
| `profile` | `string` | - | Operating profile |
| `hospital_type` | `string` | - | Facility type |
| `beds` | `int64` | - | Licensed bed capacity |
| `status` | `string` | - | Active / Inactive |
| `latitude` | `float64` | - | Synthetic latitude |
| `longitude` | `float64` | - | Synthetic longitude |

### `dim_specialty`

- **Grain:** One row per medical specialty
- **Primary key:** `specialty_id`
- **Foreign keys:** none

| Column | Dtype | Key | Description |
|---|---|---|---|
| `specialty_id` | `string` | PK | S01.. |
| `specialty_name` | `string` | - | Specialty name |

### `dim_department`

- **Grain:** One row per department within a hospital
- **Primary key:** `department_id`
- **Foreign keys:** `hospital_id` -> `dim_hospital`, `specialty_id` -> `dim_specialty`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `department_id` | `string` | PK | D001.. |
| `hospital_id` | `string` | FK (dim_hospital) | Parent hospital |
| `department_name` | `string` | - | Department name |
| `specialty_id` | `string` | FK (dim_specialty) | Primary specialty |

### `dim_doctor`

- **Grain:** One row per clinician
- **Primary key:** `doctor_id`
- **Foreign keys:** `hospital_id` -> `dim_hospital`, `department_id` -> `dim_department`, `specialty_id` -> `dim_specialty`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `doctor_id` | `string` | PK | DOC0001.. |
| `hospital_id` | `string` | FK (dim_hospital) | Parent hospital |
| `department_id` | `string` | FK (dim_department) | Parent department |
| `doctor_name` | `string` | - | Synthetic clinician name |
| `specialty_id` | `string` | FK (dim_specialty) | Specialty |
| `role` | `string` | - | Consultant / Specialist / Resident |

### `dim_staff`

- **Grain:** One row per staff member
- **Primary key:** `staff_id`
- **Foreign keys:** `hospital_id` -> `dim_hospital`, `department_id` -> `dim_department`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `staff_id` | `string` | PK | STF00001.. |
| `hospital_id` | `string` | FK (dim_hospital) | Parent hospital |
| `department_id` | `string` | FK (dim_department) | Parent department |
| `staff_name` | `string` | - | Synthetic staff name |
| `role` | `string` | - | Nurse / Technician / Admin / ... |
| `employment_type` | `string` | - | Full-time / Part-time / Contract |
| `status` | `string` | - | Active / On leave |
| `hourly_rate` | `float64` | - | Synthetic hourly rate |

### `dim_payer`

- **Grain:** One row per insurance payer / self-pay category
- **Primary key:** `payer_id`
- **Foreign keys:** none

| Column | Dtype | Key | Description |
|---|---|---|---|
| `payer_id` | `string` | PK | P01.. |
| `payer_name` | `string` | - | Payer name |
| `payer_type` | `string` | - | Insurance / Self-pay / Government |

### `dim_diagnosis`

- **Grain:** One row per diagnosis code
- **Primary key:** `diagnosis_code`
- **Foreign keys:** none

| Column | Dtype | Key | Description |
|---|---|---|---|
| `diagnosis_code` | `string` | PK | ICD-like code |
| `diagnosis_name` | `string` | - | Diagnosis label |
| `category` | `string` | - | Diagnosis category |

### `dim_procedure`

- **Grain:** One row per procedure code
- **Primary key:** `procedure_code`
- **Foreign keys:** `specialty_id` -> `dim_specialty`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `procedure_code` | `string` | PK | CPT-like code |
| `procedure_name` | `string` | - | Procedure label |
| `specialty_id` | `string` | FK (dim_specialty) | Owning specialty |
| `category` | `string` | - | Procedure category |

### `dim_medication`

- **Grain:** One row per medication code
- **Primary key:** `medication_code`
- **Foreign keys:** none

| Column | Dtype | Key | Description |
|---|---|---|---|
| `medication_code` | `string` | PK | MED0001.. |
| `medication_name` | `string` | - | Medicine name |
| `category` | `string` | - | Medication category |
| `unit_cost` | `float64` | - | Synthetic unit cost |

### `dim_lab_test`

- **Grain:** One row per laboratory test code
- **Primary key:** `test_code`
- **Foreign keys:** none

| Column | Dtype | Key | Description |
|---|---|---|---|
| `test_code` | `string` | PK | LAB0001.. |
| `test_name` | `string` | - | Test name |
| `category` | `string` | - | Test category |
| `sla_minutes` | `int64` | - | Turnaround SLA in minutes |

### `dim_service`

- **Grain:** One row per billable service code
- **Primary key:** `service_code`
- **Foreign keys:** none

| Column | Dtype | Key | Description |
|---|---|---|---|
| `service_code` | `string` | PK | SVC0001.. |
| `service_name` | `string` | - | Service label |
| `category` | `string` | - | Consultation / Procedures / Diagnostics / Pharmacy / Inpatient services |
| `unit_price` | `float64` | - | Synthetic unit price |

### `dim_supplier`

- **Grain:** One row per supplier
- **Primary key:** `supplier_id`
- **Foreign keys:** none

| Column | Dtype | Key | Description |
|---|---|---|---|
| `supplier_id` | `string` | PK | SUP0001.. |
| `supplier_name` | `string` | - | Supplier name |
| `lead_days` | `int64` | - | Typical lead time |
| `reliability_score` | `float64` | - | 0..1 on-time reliability |

### `dim_inventory_item`

- **Grain:** One row per inventory SKU
- **Primary key:** `item_id`
- **Foreign keys:** `supplier_id` -> `dim_supplier`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `item_id` | `string` | PK | ITEM00001.. |
| `item_name` | `string` | - | Item name |
| `category` | `string` | - | Clinical / Surgical / Pharmacy / Consumables |
| `unit_cost` | `float64` | - | Unit cost |
| `reorder_level` | `int64` | - | Reorder threshold |
| `supplier_id` | `string` | FK (dim_supplier) | Preferred supplier |

### `dim_bed`

- **Grain:** One row per physical bed
- **Primary key:** `bed_id`
- **Foreign keys:** `hospital_id` -> `dim_hospital`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `bed_id` | `string` | PK | BED-H01-0001.. |
| `hospital_id` | `string` | FK (dim_hospital) | Parent hospital |
| `ward` | `string` | - | Ward / unit |
| `bed_type` | `string` | - | General / ICU / Pediatric / Maternity / Observation |

### `dim_date`

- **Grain:** One row per calendar day in the 24-month window
- **Primary key:** `date_key`
- **Foreign keys:** none

| Column | Dtype | Key | Description |
|---|---|---|---|
| `date_key` | `int64` | PK | YYYYMMDD |
| `full_date` | `date` | - | Calendar date |
| `year` | `int64` | - | Year |
| `quarter` | `int64` | - | Quarter |
| `month` | `int64` | - | Month number |
| `month_name` | `string` | - | Month name |
| `day` | `int64` | - | Day of month |
| `weekday` | `int64` | - | Monday=0 |
| `weekday_name` | `string` | - | Weekday name |
| `is_weekend` | `bool` | - | Sat/Sun flag |

### `dim_time`

- **Grain:** One row per minute-of-day bucket (HHMM)
- **Primary key:** `time_key`
- **Foreign keys:** none

| Column | Dtype | Key | Description |
|---|---|---|---|
| `time_key` | `int64` | PK | HHMM |
| `hour` | `int64` | - | Hour 0-23 |
| `minute` | `int64` | - | Minute 0-59 |
| `hour_bucket` | `string` | - | Morning / Afternoon / Evening / Night |

## Transactional / fact tables

### `patients`

- **Grain:** One row per patient
- **Primary key:** `patient_id`
- **Foreign keys:** none

| Column | Dtype | Key | Description |
|---|---|---|---|
| `patient_id` | `string` | PK | PAT000001.. |
| `first_name` | `string` | - | Synthetic first name |
| `last_name` | `string` | - | Synthetic last name |
| `birth_date` | `date` | - | Date of birth |
| `gender` | `string` | - | Male / Female / Other |
| `city` | `string` | - | City |
| `state` | `string` | - | State / region |
| `registration_date` | `date` | - | Registration date |
| `blood_type` | `string` | - | ABO group |
| `patient_type` | `string` | - | New / Returning |

### `appointments`

- **Grain:** One row per appointment
- **Primary key:** `appointment_id`
- **Foreign keys:** `patient_id` -> `patients`, `hospital_id` -> `dim_hospital`, `department_id` -> `dim_department`, `doctor_id` -> `dim_doctor`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `appointment_id` | `string` | PK | APT0000001.. |
| `patient_id` | `string` | FK (patients) | FK patients |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `department_id` | `string` | FK (dim_department) | FK dim_department |
| `doctor_id` | `string` | FK (dim_doctor) | FK dim_doctor |
| `booking_date` | `date` | - | Booking date |
| `appointment_date` | `date` | - | Scheduled date |
| `appointment_type` | `string` | - | New / Follow-up / Routine / Urgent |
| `status` | `string` | - | Completed / Cancelled / No-show / Scheduled |
| `checkin_datetime` | `datetime64[ns]` | - | Check-in timestamp (nullable) |
| `waiting_minutes` | `float64` | - | Check-in waiting time |
| `cancellation_reason` | `string` | - | Reason or None |
| `booking_channel` | `string` | - | Online / Phone / Walk-in / Portal |
| `lead_days` | `int64` | - | Booking-to-appointment days |
| `rescheduled_flag` | `bool` | - | Was rescheduled |

### `encounters`

- **Grain:** One row per encounter
- **Primary key:** `encounter_id`
- **Foreign keys:** `patient_id` -> `patients`, `appointment_id` -> `appointments`, `hospital_id` -> `dim_hospital`, `department_id` -> `dim_department`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `encounter_id` | `string` | PK | ENC0000001.. |
| `patient_id` | `string` | FK (patients) | FK patients |
| `appointment_id` | `string` | FK (appointments) | FK appointments (nullable) |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `department_id` | `string` | FK (dim_department) | FK dim_department |
| `encounter_type` | `string` | - | Outpatient / Emergency / Inpatient |
| `arrival_datetime` | `datetime64[ns]` | - | Arrival / start time |
| `triage_category` | `string` | - | Critical/Urgent/Standard/Non-urgent |
| `triage_datetime` | `datetime64[ns]` | - | Triage timestamp |
| `provider_datetime` | `datetime64[ns]` | - | Seen-by-provider timestamp |
| `disposition_datetime` | `datetime64[ns]` | - | Disposition timestamp |
| `waiting_minutes` | `float64` | - | Arrival to provider |
| `treatment_minutes` | `float64` | - | Provider to disposition |
| `disposition` | `string` | - | Discharge / Admit / Transfer / LWBS |
| `arrival_mode` | `string` | - | Walk-in / Ambulance / Referral |
| `critical_flag` | `bool` | - | Critical patient |

### `admissions`

- **Grain:** One row per admission
- **Primary key:** `admission_id`
- **Foreign keys:** `encounter_id` -> `encounters`, `patient_id` -> `patients`, `hospital_id` -> `dim_hospital`, `department_id` -> `dim_department`, `bed_id` -> `dim_bed`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `admission_id` | `string` | PK | ADM000001.. |
| `encounter_id` | `string` | FK (encounters) | FK encounters |
| `patient_id` | `string` | FK (patients) | FK patients |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `department_id` | `string` | FK (dim_department) | FK dim_department |
| `ward` | `string` | - | Ward / unit |
| `bed_id` | `string` | FK (dim_bed) | FK dim_bed |
| `admission_datetime` | `datetime64[ns]` | - | Admission timestamp |
| `discharge_datetime` | `datetime64[ns]` | - | Discharge timestamp (nullable) |
| `admission_type` | `string` | - | Elective / Emergency / Transfer |
| `discharge_status` | `string` | - | Recovered / Referred / Deceased / Against advice |
| `los_days` | `float64` | - | Length of stay in days |
| `readmission_flag` | `bool` | - | Readmission within 30 days |
| `boarding_hours` | `float64` | - | Boarding time before bed |

### `transfers`

- **Grain:** One row per transfer
- **Primary key:** `transfer_id`
- **Foreign keys:** `admission_id` -> `admissions`, `patient_id` -> `patients`, `hospital_id` -> `dim_hospital`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `transfer_id` | `string` | PK | TRF000001.. |
| `admission_id` | `string` | FK (admissions) | FK admissions |
| `patient_id` | `string` | FK (patients) | FK patients |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `from_ward` | `string` | - | Source ward |
| `to_ward` | `string` | - | Destination ward |
| `transfer_datetime` | `datetime64[ns]` | - | Transfer timestamp |
| `reason` | `string` | - | Clinical / Capacity / Specialist |

### `bed_snapshots`

- **Grain:** One row per bed per snapshot date/time
- **Primary key:** `snapshot_id`
- **Foreign keys:** `hospital_id` -> `dim_hospital`, `bed_id` -> `dim_bed`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `snapshot_id` | `string` | PK | SNP0000001.. |
| `snapshot_datetime` | `datetime64[ns]` | - | Snapshot timestamp |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `ward` | `string` | - | Ward |
| `bed_id` | `string` | FK (dim_bed) | FK dim_bed |
| `bed_type` | `string` | - | Bed type |
| `status` | `string` | - | Occupied / Available / Blocked |
| `occupied_flag` | `bool` | - | 1 when Occupied |
| `blocked_flag` | `bool` | - | 1 when Blocked |

### `procedures`

- **Grain:** One row per procedure event
- **Primary key:** `procedure_id`
- **Foreign keys:** `patient_id` -> `patients`, `encounter_id` -> `encounters`, `hospital_id` -> `dim_hospital`, `department_id` -> `dim_department`, `surgeon_id` -> `dim_doctor`, `procedure_code` -> `dim_procedure`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `procedure_id` | `string` | PK | PRC0000001.. |
| `patient_id` | `string` | FK (patients) | FK patients |
| `encounter_id` | `string` | FK (encounters) | FK encounters |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `department_id` | `string` | FK (dim_department) | FK dim_department |
| `or_room` | `string` | - | Operating room |
| `surgeon_id` | `string` | FK (dim_doctor) | FK dim_doctor |
| `procedure_code` | `string` | FK (dim_procedure) | FK dim_procedure |
| `scheduled_start` | `datetime64[ns]` | - | Scheduled start |
| `actual_start` | `datetime64[ns]` | - | Actual start (nullable) |
| `actual_end` | `datetime64[ns]` | - | Actual end (nullable) |
| `duration_minutes` | `float64` | - | Procedure duration |
| `delay_minutes` | `float64` | - | Start delay |
| `status` | `string` | - | Completed / Cancelled / Delayed |
| `cancellation_reason` | `string` | - | Reason or None |
| `elective_emergency` | `string` | - | Elective / Emergency |
| `revenue` | `float64` | - | Procedure revenue |

### `lab_orders`

- **Grain:** One row per lab order
- **Primary key:** `lab_order_id`
- **Foreign keys:** `patient_id` -> `patients`, `encounter_id` -> `encounters`, `hospital_id` -> `dim_hospital`, `ordering_department` -> `dim_department`, `test_code` -> `dim_lab_test`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `lab_order_id` | `string` | PK | LBO0000001.. |
| `patient_id` | `string` | FK (patients) | FK patients |
| `encounter_id` | `string` | FK (encounters) | FK encounters |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `ordering_department` | `string` | FK (dim_department) | Ordering department |
| `test_code` | `string` | FK (dim_lab_test) | FK dim_lab_test |
| `priority` | `string` | - | Routine / Urgent / STAT |
| `ordered_at` | `datetime64[ns]` | - | Order timestamp |
| `collection_at` | `datetime64[ns]` | - | Collection timestamp |
| `status` | `string` | - | Completed / Pending / Cancelled |

### `lab_results`

- **Grain:** One row per test result
- **Primary key:** `result_id`
- **Foreign keys:** `lab_order_id` -> `lab_orders`, `patient_id` -> `patients`, `test_code` -> `dim_lab_test`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `result_id` | `string` | PK | LBR0000001.. |
| `lab_order_id` | `string` | FK (lab_orders) | FK lab_orders |
| `patient_id` | `string` | FK (patients) | FK patients |
| `test_code` | `string` | FK (dim_lab_test) | Test performed |
| `result_at` | `datetime64[ns]` | - | Result timestamp (nullable) |
| `result_value` | `float64` | - | Synthetic numeric result |
| `result_flag` | `string` | - | Normal / High / Low |
| `is_critical` | `bool` | - | Critical result flag |
| `tat_minutes` | `float64` | - | Turnaround time |
| `status` | `string` | - | Final / Pending |

### `prescriptions`

- **Grain:** One row per prescription
- **Primary key:** `prescription_id`
- **Foreign keys:** `patient_id` -> `patients`, `encounter_id` -> `encounters`, `hospital_id` -> `dim_hospital`, `medication_code` -> `dim_medication`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `prescription_id` | `string` | PK | RX0000001.. |
| `patient_id` | `string` | FK (patients) | FK patients |
| `encounter_id` | `string` | FK (encounters) | FK encounters |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `medication_code` | `string` | FK (dim_medication) | FK dim_medication |
| `quantity` | `int64` | - | Quantity prescribed |
| `prescribed_date` | `date` | - | Prescription date |
| `status` | `string` | - | Dispensed / Pending / Cancelled |
| `amount` | `float64` | - | Prescription value |

### `dispensing`

- **Grain:** One row per dispensing transaction
- **Primary key:** `dispensing_id`
- **Foreign keys:** `prescription_id` -> `prescriptions`, `hospital_id` -> `dim_hospital`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `dispensing_id` | `string` | PK | DSP0000001.. |
| `prescription_id` | `string` | FK (prescriptions) | FK prescriptions |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `pharmacy_id` | `string` | - | Pharmacy identifier |
| `dispensed_date` | `date` | - | Dispensing date |
| `quantity_dispensed` | `int64` | - | Quantity dispensed |
| `status` | `string` | - | Completed / Partial / Pending |

### `invoices`

- **Grain:** One row per invoice
- **Primary key:** `invoice_id`
- **Foreign keys:** `encounter_id` -> `encounters`, `patient_id` -> `patients`, `hospital_id` -> `dim_hospital`, `payer_id` -> `dim_payer`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `invoice_id` | `string` | PK | INV0000001.. |
| `encounter_id` | `string` | FK (encounters) | FK encounters |
| `patient_id` | `string` | FK (patients) | FK patients |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `payer_id` | `string` | FK (dim_payer) | FK dim_payer |
| `invoice_date` | `date` | - | Invoice date |
| `gross_amount` | `float64` | - | Gross charged |
| `discount_amount` | `float64` | - | Discount applied |
| `net_amount` | `float64` | - | Net after discount |
| `paid_amount` | `float64` | - | Amount collected so far |
| `balance_amount` | `float64` | - | Outstanding balance |
| `invoice_status` | `string` | - | Paid / Partial / Pending / Overdue |
| `payment_status` | `string` | - | Settled / Partial / Unpaid |

### `invoice_lines`

- **Grain:** One row per invoice line
- **Primary key:** `line_id`
- **Foreign keys:** `invoice_id` -> `invoices`, `service_code` -> `dim_service`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `line_id` | `string` | PK | IL00000001.. |
| `invoice_id` | `string` | FK (invoices) | FK invoices |
| `service_code` | `string` | FK (dim_service) | FK dim_service |
| `service_category` | `string` | - | Service category |
| `description` | `string` | - | Line description |
| `quantity` | `int64` | - | Quantity |
| `unit_price` | `float64` | - | Unit price |
| `line_amount` | `float64` | - | Line total |

### `payments`

- **Grain:** One row per payment transaction
- **Primary key:** `payment_id`
- **Foreign keys:** `invoice_id` -> `invoices`, `patient_id` -> `patients`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `payment_id` | `string` | PK | PAY0000001.. |
| `invoice_id` | `string` | FK (invoices) | FK invoices |
| `patient_id` | `string` | FK (patients) | FK patients |
| `payment_date` | `date` | - | Payment date |
| `amount` | `float64` | - | Payment amount (refunds negative) |
| `method` | `string` | - | Cash / Card / Insurance / Transfer |
| `payment_type` | `string` | - | Payment / Refund |
| `status` | `string` | - | Cleared / Pending / Failed |

### `claims`

- **Grain:** One row per insurance claim (claim header)
- **Primary key:** `claim_id`
- **Foreign keys:** `invoice_id` -> `invoices`, `patient_id` -> `patients`, `hospital_id` -> `dim_hospital`, `payer_id` -> `dim_payer`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `claim_id` | `string` | PK | CLM0000001.. |
| `invoice_id` | `string` | FK (invoices) | FK invoices |
| `patient_id` | `string` | FK (patients) | FK patients |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `payer_id` | `string` | FK (dim_payer) | FK dim_payer |
| `claim_date` | `date` | - | Claim submission date |
| `claim_amount` | `float64` | - | Claimed amount |
| `approved_amount` | `float64` | - | Approved amount |
| `paid_amount` | `float64` | - | Paid amount |
| `status` | `string` | - | Approved / Denied / Pending / Under review / Appealed |
| `denial_reason` | `string` | - | Reason or None |
| `processing_days` | `float64` | - | Days to adjudication |
| `claim_type` | `string` | - | Inpatient / Outpatient / Emergency |

### `claim_lines`

- **Grain:** One row per claim line
- **Primary key:** `claim_line_id`
- **Foreign keys:** `claim_id` -> `claims`, `service_code` -> `dim_service`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `claim_line_id` | `string` | PK | CXL0000001.. |
| `claim_id` | `string` | FK (claims) | FK claims |
| `service_code` | `string` | FK (dim_service) | Service code |
| `line_amount` | `float64` | - | Line amount |
| `status` | `string` | - | Approved / Denied / Pending |

### `claim_events`

- **Grain:** One row per claim status event
- **Primary key:** `event_id`
- **Foreign keys:** `claim_id` -> `claims`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `event_id` | `string` | PK | CVE0000001.. |
| `claim_id` | `string` | FK (claims) | FK claims |
| `event_date` | `date` | - | Event date |
| `event_type` | `string` | - | Submitted / Under review / Approved / Denied / Paid / Appealed |
| `status` | `string` | - | Resulting status |

### `shifts`

- **Grain:** One row per staff shift
- **Primary key:** `shift_id`
- **Foreign keys:** `staff_id` -> `dim_staff`, `hospital_id` -> `dim_hospital`, `department_id` -> `dim_department`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `shift_id` | `string` | PK | SFT0000001.. |
| `staff_id` | `string` | FK (dim_staff) | FK dim_staff |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `department_id` | `string` | FK (dim_department) | FK dim_department |
| `shift_date` | `date` | - | Shift date |
| `shift_type` | `string` | - | Morning / Evening / Night |
| `scheduled_hours` | `float64` | - | Scheduled hours |
| `actual_hours` | `float64` | - | Actual hours |
| `overtime_hours` | `float64` | - | Overtime hours |

### `attendance`

- **Grain:** One row per attendance event
- **Primary key:** `attendance_id`
- **Foreign keys:** `shift_id` -> `shifts`, `staff_id` -> `dim_staff`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `attendance_id` | `string` | PK | ATT0000001.. |
| `shift_id` | `string` | FK (shifts) | FK shifts |
| `staff_id` | `string` | FK (dim_staff) | FK dim_staff |
| `attendance_date` | `date` | - | Date |
| `status` | `string` | - | Present / Absent / Late / Leave |
| `hours_worked` | `float64` | - | Hours worked |

### `inventory_movements`

- **Grain:** One row per stock movement
- **Primary key:** `movement_id`
- **Foreign keys:** `hospital_id` -> `dim_hospital`, `item_id` -> `dim_inventory_item`, `supplier_id` -> `dim_supplier`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `movement_id` | `string` | PK | INVM0000001.. |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `item_id` | `string` | FK (dim_inventory_item) | FK dim_inventory_item |
| `supplier_id` | `string` | FK (dim_supplier) | FK dim_supplier |
| `movement_date` | `date` | - | Movement date |
| `movement_type` | `string` | - | Receipt/Issue/Transfer/Adjustment/Return/Waste/Expiry |
| `quantity` | `int64` | - | Quantity moved (signed) |
| `unit_cost` | `float64` | - | Unit cost |
| `expiry_date` | `date` | - | Expiry date for received stock |

### `purchase_orders`

- **Grain:** One row per purchase order
- **Primary key:** `po_id`
- **Foreign keys:** `hospital_id` -> `dim_hospital`, `supplier_id` -> `dim_supplier`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `po_id` | `string` | PK | PO0000001.. |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `supplier_id` | `string` | FK (dim_supplier) | FK dim_supplier |
| `order_date` | `date` | - | Order date |
| `expected_date` | `date` | - | Expected delivery |
| `received_date` | `date` | - | Actual delivery (nullable) |
| `status` | `string` | - | Pending / Received / Delayed / Cancelled |
| `total_amount` | `float64` | - | Order value |

### `feedback`

- **Grain:** One row per patient feedback submission
- **Primary key:** `feedback_id`
- **Foreign keys:** `patient_id` -> `patients`, `hospital_id` -> `dim_hospital`, `department_id` -> `dim_department`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `feedback_id` | `string` | PK | FBK0000001.. |
| `patient_id` | `string` | FK (patients) | FK patients |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `department_id` | `string` | FK (dim_department) | FK dim_department |
| `visit_date` | `date` | - | Visit date |
| `rating` | `int64` | - | 1..5 |
| `category` | `string` | - | Care / Facilities / Staff / Waiting / Billing / Other |
| `sentiment_label` | `string` | - | Synthetic: Positive / Neutral / Negative |
| `complaint_flag` | `bool` | - | Is a complaint |
| `complaint_text` | `string` | - | Synthetic complaint text or None |
| `resolution_status` | `string` | - | Resolved / Open / In progress / N/A |
| `resolution_days` | `float64` | - | Days to resolve |
| `feedback_type` | `string` | - | Survey / Complaint / Suggestion |
| `nps_score` | `int64` | - | 0..10 synthetic NPS |

### `incidents`

- **Grain:** One row per quality / safety incident
- **Primary key:** `incident_id`
- **Foreign keys:** `hospital_id` -> `dim_hospital`, `department_id` -> `dim_department`

| Column | Dtype | Key | Description |
|---|---|---|---|
| `incident_id` | `string` | PK | INC0000001.. |
| `hospital_id` | `string` | FK (dim_hospital) | FK dim_hospital |
| `department_id` | `string` | FK (dim_department) | FK dim_department |
| `incident_date` | `date` | - | Incident date |
| `category` | `string` | - | Fall / Medication / Infection / Safety / Other |
| `severity` | `string` | - | Low / Medium / High / Critical |
| `status` | `string` | - | Open / Investigating / Resolved / Closed |
| `investigation_complete_flag` | `bool` | - | Investigation complete |
| `investigation_days` | `float64` | - | Days to complete investigation |
| `resolution_date` | `date` | - | Resolution date (nullable) |

## Gold / analytical tables

Gold tables are separate, aggregated models fully specified in `CONTRACT.md`
section 3 (`gold_network_daily`, `gold_hospital_monthly`, `gold_department_monthly`,
`gold_patient_access`, `gold_bed_utilization`, `gold_financial_performance`,
`gold_claim_performance`, `gold_lab_performance`, `gold_workforce`,
`gold_inventory`, `gold_patient_experience`, `gold_quality_safety`).
Their grains and measures are documented in [erd.md](erd.md) and
[kpi_glossary.md](kpi_glossary.md).
