"""KPI specifications used by every /kpis endpoint.

Every spec is SQL against gold/silver tables in DuckDB. Values, previous
periods, changes and sparklines are computed centrally by `build_kpis`.

IDs are the canonical blueprint names. Short legacy IDs are retained through
`aliases` so no existing API consumer breaks. All keyword arguments are
explicit: the old positional calls accidentally placed unit constants in the
`date_col` slot, which silently disabled date filtering and sparklines.
"""
from __future__ import annotations

from api.services.metrics import KpiSpec

H = "gold_hospital_monthly"
PA = "gold_patient_access"
BU = "gold_bed_utilization"
FP = "gold_financial_performance"
CP = "gold_claim_performance"
LP = "gold_lab_performance"
WF = "gold_workforce"
IV = "gold_inventory"
PE = "gold_patient_experience"
QS = "gold_quality_safety"

COUNT = "count"
CURRENCY = "currency"
PERCENT = "percent"
MINUTES = "minutes"
HOURS = "hours"
DAYS = "days"
SCORE = "score"
RATIO = "ratio"

_OR_DAY = "CAST(or_room AS VARCHAR) || '-' || CAST(CAST(scheduled_start AS DATE) AS VARCHAR)"


def _pct(num: str, den: str) -> str:
    return f"{num} * 100.0 / NULLIF({den}, 0)"


def _wavg(expr: str, weight: str) -> str:
    return f"SUM(({expr}) * ({weight})) / NULLIF(SUM({weight}), 0)"


def _wavg_nonnull(expr: str, weight: str) -> str:
    """Weighted mean whose denominator excludes rows with a NULL measurement.

    A NULL investigation duration is an unmeasured incident, not a zero-day
    incident. Counting its weight in the denominator understates the mean.
    """
    return (
        f"SUM(({expr}) * ({weight})) FILTER (WHERE {expr} IS NOT NULL) / "
        f"NULLIF(SUM({weight}) FILTER (WHERE {expr} IS NOT NULL), 0)"
    )


NETWORK: list[KpiSpec] = [
    KpiSpec("total_patients", "Total Patients", "silver_encounters",
            "COUNT(DISTINCT patient_id)", date_col="arrival_datetime", unit=COUNT,
            description="Distinct patients with an encounter in the period."),
    KpiSpec("total_encounters", "Total Encounters", H, "SUM(encounters)", unit=COUNT,
            aliases=("patient_volume",),
            description="All outpatient, emergency and inpatient encounters."),
    KpiSpec("total_admissions", "Total Admissions", H, "SUM(admissions)", unit=COUNT,
            description="Inpatient admissions in the period."),
    KpiSpec("total_revenue", "Total Revenue", H, "SUM(gross_revenue)", unit=CURRENCY,
            description="Gross charged revenue before discounts. `revenue` is the separate net-revenue KPI."),
    KpiSpec("net_collections", "Net Collections", H, "SUM(collections)", unit=CURRENCY,
            description="Cash collected against invoices."),
    KpiSpec("average_occupancy", "Average Occupancy", H,
            _pct("SUM(occupied_bed_days)", "SUM(available_bed_days)"), unit=PERCENT,
            description="Occupied bed days divided by available (non-blocked) bed days."),
    KpiSpec("average_los", "Average Length of Stay", H,
            "SUM(avg_los_days * discharges) / NULLIF(SUM(discharges), 0)", unit=DAYS,
            higher_is_better=False, description="Discharge-weighted average length of stay."),
    KpiSpec("patient_satisfaction", "Patient Satisfaction", PE,
            _wavg("satisfaction_pct", "feedback_count"), unit=PERCENT,
            description="Rating converted to a 0-100 scale (AVG(rating)/5*100). `average_satisfaction` is the 1-5 score."),
    KpiSpec("no_show_rate", "No-Show Rate", H,
            _pct("SUM(no_show_appointments)", "SUM(completed_appointments + no_show_appointments)"),
            unit=PERCENT, higher_is_better=False,
            description="No-shows divided by completed plus no-show appointments; cancellations excluded."),
    KpiSpec("claim_denial_rate", "Claim Denial Rate", CP,
            _pct("SUM(denied)", "SUM(approved + denied)"), unit=PERCENT,
            higher_is_better=False, description="Denied claims divided by adjudicated claims."),
    KpiSpec("hospitals_selected", "Hospitals Selected", "dim_hospital",
            "COUNT(DISTINCT hospital_id)", date_col="", unit=COUNT,
            description="Number of hospitals in the active selection (1-10); dimension snapshot, no date filter."),
    KpiSpec("total_beds", "Total Beds", "dim_hospital", "SUM(beds)", date_col="",
            unit=COUNT, description="Staffed bed capacity across the selected hospitals; dimension snapshot, no date filter."),
]

HOSPITAL: list[KpiSpec] = [
    KpiSpec("patients", "Patients", "silver_encounters", "COUNT(DISTINCT patient_id)",
            date_col="arrival_datetime", unit=COUNT),
    KpiSpec("encounters", "Encounters", H, "SUM(encounters)", unit=COUNT),
    KpiSpec("admissions", "Admissions", H, "SUM(admissions)", unit=COUNT),
    KpiSpec("total_revenue", "Total Revenue", H, "SUM(gross_revenue)", unit=CURRENCY,
            description="Gross charged revenue before discounts; the net measure is `revenue`."),
    KpiSpec("occupancy", "Occupancy", H,
            _pct("SUM(occupied_bed_days)", "SUM(available_bed_days)"), unit=PERCENT),
    KpiSpec("average_los", "Average LOS", H,
            "SUM(avg_los_days * discharges) / NULLIF(SUM(discharges), 0)", unit=DAYS,
            aliases=("los",), higher_is_better=False),
    KpiSpec("patient_satisfaction", "Patient Satisfaction", PE,
            _wavg("satisfaction_pct", "feedback_count"), unit=PERCENT),
    KpiSpec("staff_count", "Staff Count", WF, "SUM(headcount)", unit=COUNT),
]

APPOINTMENTS: list[KpiSpec] = [
    KpiSpec("scheduled_appointments", "Scheduled Appointments", PA, "SUM(scheduled)", unit=COUNT),
    KpiSpec("completed_appointments", "Completed Appointments", PA, "SUM(completed)", unit=COUNT),
    KpiSpec("cancelled_appointments", "Cancelled Appointments", PA, "SUM(cancelled)",
            unit=COUNT, higher_is_better=False),
    KpiSpec("no_show_appointments", "No-Show Appointments", PA, "SUM(no_shows)",
            unit=COUNT, higher_is_better=False),
    KpiSpec("no_show_rate", "No-Show Rate", PA,
            _pct("SUM(no_shows)", "SUM(completed + no_shows)"), unit=PERCENT,
            higher_is_better=False),
    KpiSpec("avg_wait_appointment", "Average Wait for Appointment", PA,
            _wavg("avg_lead_days", "scheduled"), unit=DAYS, higher_is_better=False,
            aliases=("average_wait_for_appointment",)),
    KpiSpec("avg_checkin_wait", "Average Check-in Waiting Time", PA,
            _wavg("avg_wait_minutes", "scheduled"), unit=MINUTES, higher_is_better=False,
            aliases=("average_checkin_waiting_time",)),
    KpiSpec("appointment_utilization", "Appointment Utilization", PA,
            _pct("SUM(completed)", "SUM(scheduled)"), unit=PERCENT),
    KpiSpec("same_day_pct", "Same-Day Appointments", PA,
            _wavg("same_day_pct", "scheduled"), unit=PERCENT,
            aliases=("same_day_appointment_pct",)),
    KpiSpec("rescheduling_rate", "Rescheduling Rate", PA,
            _wavg("reschedule_rate", "scheduled"), unit=PERCENT, higher_is_better=False),
]

EMERGENCY: list[KpiSpec] = [
    KpiSpec("emergency_visits", "Emergency Visits", "silver_encounters",
            "COUNT(*) FILTER (WHERE encounter_type = 'Emergency')",
            date_col="arrival_datetime", unit=COUNT),
    KpiSpec("avg_triage_time", "Average Triage Time", "silver_encounters",
            "AVG(date_diff('minute', arrival_datetime, triage_datetime)) "
            "FILTER (WHERE encounter_type = 'Emergency')",
            date_col="arrival_datetime", unit=MINUTES, higher_is_better=False,
            aliases=("average_triage_time",)),
    KpiSpec("avg_waiting_time", "Average Waiting Time", "silver_encounters",
            "AVG(waiting_minutes) FILTER (WHERE encounter_type = 'Emergency')",
            date_col="arrival_datetime", unit=MINUTES, higher_is_better=False,
            aliases=("average_waiting_time",)),
    KpiSpec("avg_treatment_time", "Average Treatment Time", "silver_encounters",
            "AVG(treatment_minutes) FILTER (WHERE encounter_type = 'Emergency')",
            date_col="arrival_datetime", unit=MINUTES,
            aliases=("average_treatment_time",)),
    KpiSpec("patients_admitted", "Patients Admitted", "silver_encounters",
            "COUNT(*) FILTER (WHERE disposition = 'Admit')",
            date_col="arrival_datetime", unit=COUNT),
    KpiSpec("patients_discharged", "Patients Discharged", "silver_encounters",
            "COUNT(*) FILTER (WHERE disposition = 'Discharge')",
            date_col="arrival_datetime", unit=COUNT),
    KpiSpec("patients_transferred", "Patients Transferred", "silver_encounters",
            "COUNT(*) FILTER (WHERE disposition = 'Transfer')",
            date_col="arrival_datetime", unit=COUNT),
    KpiSpec("left_without_seen", "Left Without Being Seen", "silver_encounters",
            "COUNT(*) FILTER (WHERE disposition = 'LWBS')",
            date_col="arrival_datetime", unit=COUNT, higher_is_better=False,
            aliases=("left_without_being_seen",)),
    KpiSpec("emergency_throughput", "Emergency Throughput", "silver_encounters",
            "COUNT(*) FILTER (WHERE encounter_type = 'Emergency') * 1.0 / "
            "NULLIF(date_diff('day', CAST($date_from AS DATE), CAST($date_to AS DATE)) + 1, 0)",
            date_col="arrival_datetime", unit=COUNT,
            description="Emergency visits per calendar day in the selected period."),
    KpiSpec("critical_patient_volume", "Critical Patient Volume", "silver_encounters",
            "COUNT(*) FILTER (WHERE critical_flag)",
            date_col="arrival_datetime", unit=COUNT),
]

INPATIENT: list[KpiSpec] = [
    KpiSpec("total_beds", "Total Beds", "dim_hospital", "SUM(beds)", date_col="", unit=COUNT),
    KpiSpec("available_beds", "Available Beds", BU,
            "SUM(available_bed_days) / NULLIF(COUNT(DISTINCT month || ward), 0)", unit=COUNT),
    KpiSpec("occupied_beds", "Occupied Beds", BU,
            "SUM(occupied_bed_days) / NULLIF(COUNT(DISTINCT month || ward), 0)", unit=COUNT),
    KpiSpec("blocked_beds", "Blocked Beds", BU,
            "SUM(blocked_bed_days) / NULLIF(COUNT(DISTINCT month || ward), 0)", unit=COUNT),
    KpiSpec("occupancy_rate", "Occupancy Rate", BU,
            _pct("SUM(occupied_bed_days)", "SUM(available_bed_days)"), unit=PERCENT),
    KpiSpec("average_los", "Average LOS", BU,
            "SUM(avg_los_days * discharges) / NULLIF(SUM(discharges), 0)", unit=DAYS,
            higher_is_better=False,
            description="Discharge-weighted mean LOS; occupied bed-days are not a valid LOS weight."),
    KpiSpec("bed_turnover", "Bed Turnover", BU,
            _wavg("bed_turnover", "available_bed_days"), unit=RATIO,
            aliases=("bed_turnover_rate",)),
    KpiSpec("average_discharge_time", "Average Discharge Time", "silver_admissions",
            "AVG(date_part('hour', discharge_datetime))", date_col="discharge_datetime",
            unit=HOURS, description="Average hour of day when inpatient discharges occur."),
    KpiSpec("admissions", "Admissions", H, "SUM(admissions)", unit=COUNT),
    KpiSpec("discharges", "Discharges", H, "SUM(discharges)", unit=COUNT),
    KpiSpec("readmission_rate", "Readmission Rate", H,
            _pct("SUM(readmissions)", "SUM(discharges)"), unit=PERCENT,
            higher_is_better=False),
    KpiSpec("boarding_hours", "Average Boarding Time", BU,
            _wavg("avg_boarding_hours", "occupied_bed_days"), unit=DAYS,
            higher_is_better=False, aliases=("average_boarding_time",)),
]

PROCEDURES: list[KpiSpec] = [
    KpiSpec("scheduled_procedures", "Scheduled Procedures", "silver_procedures",
            "COUNT(*)", date_col="scheduled_start", unit=COUNT),
    KpiSpec("completed_procedures", "Completed Procedures", "silver_procedures",
            "COUNT(*) FILTER (WHERE status = 'Completed')",
            date_col="scheduled_start", unit=COUNT),
    KpiSpec("cancelled_procedures", "Cancelled Procedures", "silver_procedures",
            "COUNT(*) FILTER (WHERE status = 'Cancelled')",
            date_col="scheduled_start", unit=COUNT, higher_is_better=False),
    KpiSpec("cancellation_rate", "Cancellation Rate", "silver_procedures",
            _pct("COUNT(*) FILTER (WHERE status = 'Cancelled')", "COUNT(*)"),
            date_col="scheduled_start", unit=PERCENT, higher_is_better=False),
    KpiSpec("avg_procedure_duration", "Average Procedure Duration", "silver_procedures",
            "AVG(duration_minutes)", date_col="scheduled_start", unit=MINUTES,
            aliases=("average_procedure_duration",)),
    KpiSpec("or_utilization", "OR Utilization", "silver_procedures",
            f"LEAST(100.0, SUM(duration_minutes) * 100.0 / NULLIF(COUNT(DISTINCT {_OR_DAY}) * 480, 0))",
            date_col="scheduled_start", unit=PERCENT,
            description="Procedure minutes divided by 8 staffed hours per operating-room day."),
    KpiSpec("first_case_on_time_start_rate", "First-Case On-Time Start Rate", "silver_procedures",
            _pct("COUNT(*) FILTER (WHERE date_part('hour', scheduled_start) <= 8 "
                 "AND COALESCE(delay_minutes, 0) = 0 AND actual_start IS NOT NULL)",
                 "COUNT(*) FILTER (WHERE date_part('hour', scheduled_start) <= 8)"),
            date_col="scheduled_start", unit=PERCENT,
            description="Early-slot procedures that started without delay (synthetic first-case proxy)."),
    KpiSpec("procedure_turnaround_time", "Procedure Turnaround Time", "silver_procedures",
            "AVG(date_diff('minute', actual_end, (SELECT MIN(s2.scheduled_start) "
            "FROM silver_procedures s2 WHERE s2.or_room = silver_procedures.or_room "
            "AND CAST(s2.scheduled_start AS DATE) = CAST(silver_procedures.scheduled_start AS DATE) "
            "AND s2.scheduled_start > silver_procedures.actual_end)))",
            date_col="scheduled_start", unit=MINUTES, higher_is_better=False,
            description="Average minutes from a procedure end to the next scheduled case in the same room."),
    KpiSpec("delayed_procedures", "Delayed Procedures", "silver_procedures",
            "COUNT(*) FILTER (WHERE status = 'Delayed' OR delay_minutes > 0)",
            date_col="scheduled_start", unit=COUNT, higher_is_better=False),
    KpiSpec("procedure_revenue", "Procedure Revenue", "silver_procedures",
            "SUM(revenue)", date_col="scheduled_start", unit=CURRENCY),
]

DIAGNOSTICS: list[KpiSpec] = [
    KpiSpec("total_lab_orders", "Total Lab Orders", LP, "SUM(orders)", unit=COUNT),
    KpiSpec("completed_tests", "Completed Tests", LP, "SUM(completed)", unit=COUNT),
    KpiSpec("pending_tests", "Pending Tests", LP, "SUM(pending)", unit=COUNT,
            higher_is_better=False),
    KpiSpec("cancelled_tests", "Cancelled Tests", LP, "SUM(cancelled)", unit=COUNT,
            higher_is_better=False),
    KpiSpec("avg_tat", "Average Turnaround Time", LP,
            _wavg("avg_tat_minutes", "orders"), unit=MINUTES, higher_is_better=False,
            aliases=("average_turnaround_time",)),
    KpiSpec("median_tat", "Median Turnaround Time", LP,
            _wavg("median_tat_minutes", "orders"), unit=MINUTES, higher_is_better=False,
            aliases=("median_turnaround_time",)),
    KpiSpec("sla_compliance", "SLA Compliance Rate", LP,
            _wavg("sla_rate", "orders"), unit=PERCENT,
            aliases=("sla_compliance_rate",)),
    KpiSpec("delayed_results", "Delayed Results", LP, "SUM(delayed)", unit=COUNT,
            higher_is_better=False),
    KpiSpec("critical_results", "Critical Results", LP, "SUM(critical)", unit=COUNT),
    KpiSpec("laboratory_revenue", "Laboratory Revenue", "silver_invoice_lines",
            "SUM(line_amount)",
            join_sql="JOIN silver_invoices i ON i.invoice_id = silver_invoice_lines.invoice_id",
            date_col="invoice_date", source_columns=("invoice_date", "hospital_id"),
            extra_where="silver_invoice_lines.service_category = 'Diagnostics'",
            unit=CURRENCY, description="Invoice-line revenue in the Diagnostics service category."),
]

PHARMACY: list[KpiSpec] = [
    KpiSpec("prescriptions", "Prescriptions", "silver_prescriptions", "COUNT(*)",
            date_col="prescribed_date", unit=COUNT),
    KpiSpec("items_prescribed", "Items Prescribed", "silver_prescriptions", "SUM(quantity)",
            date_col="prescribed_date", unit=COUNT),
    KpiSpec("items_dispensed", "Items Dispensed", "silver_dispensing", "SUM(quantity_dispensed)",
            date_col="dispensed_date", unit=COUNT),
    KpiSpec("pending_prescriptions", "Pending Prescriptions", "silver_prescriptions",
            "COUNT(*) FILTER (WHERE status = 'Pending')",
            date_col="prescribed_date", unit=COUNT, higher_is_better=False),
    KpiSpec("dispensing_completion", "Dispensing Completion Rate", "silver_prescriptions",
            _pct("COUNT(*) FILTER (WHERE status = 'Dispensed')", "COUNT(*)"),
            date_col="prescribed_date", unit=PERCENT,
            aliases=("dispensing_completion_rate",)),
    KpiSpec("medication_revenue", "Medication Revenue", "silver_prescriptions", "SUM(amount)",
            date_col="prescribed_date", unit=CURRENCY),
    KpiSpec("avg_prescription_value", "Average Prescription Value", "silver_prescriptions",
            "AVG(amount)", date_col="prescribed_date", unit=CURRENCY,
            aliases=("average_prescription_value",)),
    KpiSpec("stockout_medication_count", "Stockout Medication Count", IV,
            "SUM(stockouts) FILTER (WHERE category = 'Pharmacy')", unit=COUNT,
            higher_is_better=False,
            description="Stockout events in the Pharmacy inventory category."),
    KpiSpec("expired_medication_value", "Expired Medication Value", IV,
            "SUM(expired_value) FILTER (WHERE category = 'Pharmacy')", unit=CURRENCY,
            higher_is_better=False, description="Expired stock value in the Pharmacy category."),
    KpiSpec("pharmacy_waste", "Pharmacy Waste", IV,
            "SUM(waste) FILTER (WHERE category = 'Pharmacy')", unit=CURRENCY,
            higher_is_better=False, description="Waste value in the Pharmacy inventory category."),
]

FINANCE: list[KpiSpec] = [
    KpiSpec("gross_revenue", "Gross Revenue", H, "SUM(gross_revenue)", unit=CURRENCY),
    KpiSpec("revenue", "Revenue (Net)", H, "SUM(net_revenue)", unit=CURRENCY,
            description="Canonical net revenue. `total_revenue` is gross and is a different KPI."),
    KpiSpec("net_revenue", "Net Revenue", H, "SUM(net_revenue)", unit=CURRENCY),
    KpiSpec("total_billed", "Total Billed", H, "SUM(gross_revenue)", unit=CURRENCY),
    KpiSpec("total_collected", "Total Collected", H, "SUM(collections)", unit=CURRENCY),
    KpiSpec("outstanding_receivables", "Outstanding Receivables", H,
            "SUM(outstanding_balance)", unit=CURRENCY, higher_is_better=False),
    KpiSpec("collection_rate", "Collection Rate", H,
            _pct("SUM(collections)", "SUM(net_revenue)"), unit=PERCENT),
    KpiSpec("average_revenue_per_encounter", "Average Revenue per Encounter", H,
            "SUM(net_revenue) / NULLIF(SUM(encounters), 0)", unit=CURRENCY),
    KpiSpec("avg_invoice_value", "Average Invoice Value", FP,
            _wavg("avg_invoice_value", "net_revenue"), unit=CURRENCY,
            aliases=("average_invoice_value",)),
    KpiSpec("refund_amount", "Refund Amount", FP, "SUM(refunds)", unit=CURRENCY,
            higher_is_better=False),
    KpiSpec("writeoff_amount", "Write-off Amount", FP, "SUM(writeoffs)", unit=CURRENCY,
            higher_is_better=False),
    KpiSpec("revenue_growth", "Revenue Growth", FP, "AVG(revenue_growth_pct)", unit=PERCENT),
    KpiSpec("revenue_per_hospital", "Revenue per Hospital", H,
            "SUM(net_revenue) / NULLIF(COUNT(DISTINCT hospital_id), 0)", unit=CURRENCY),
]

CLAIMS: list[KpiSpec] = [
    KpiSpec("claims_submitted", "Claims Submitted", CP, "SUM(claims)", unit=COUNT),
    KpiSpec("claims_approved", "Claims Approved", CP, "SUM(approved)", unit=COUNT),
    KpiSpec("claims_denied", "Claims Denied", CP, "SUM(denied)", unit=COUNT,
            higher_is_better=False),
    KpiSpec("denial_rate", "Denial Rate", CP,
            _pct("SUM(denied)", "SUM(approved + denied)"), unit=PERCENT,
            higher_is_better=False, aliases=("claim_denial_rate",)),
    KpiSpec("pending_claims", "Pending Claims", CP,
            "GREATEST(SUM(claims) - SUM(approved) - SUM(denied), 0)", unit=COUNT,
            higher_is_better=False),
    KpiSpec("total_claimed_amount", "Total Claimed Amount", CP, "SUM(claimed_amount)", unit=CURRENCY),
    KpiSpec("approved_amount", "Approved Amount", CP, "SUM(approved_amount)", unit=CURRENCY),
    KpiSpec("denied_amount", "Denied Amount", "silver_claims",
            "SUM(claim_amount) FILTER (WHERE status = 'Denied')",
            date_col="claim_date", unit=CURRENCY, higher_is_better=False),
    KpiSpec("paid_amount", "Paid Amount", CP, "SUM(paid_amount)", unit=CURRENCY),
    KpiSpec("avg_processing_time", "Average Processing Time", CP,
            _wavg("avg_processing_days", "claims"), unit=DAYS, higher_is_better=False,
            aliases=("average_processing_time",)),
    KpiSpec("appeal_success_rate", "Appeal Success Rate", CP,
            _wavg("appeal_success_rate", "appeals"), unit=PERCENT),
    KpiSpec("outstanding_claim_value", "Outstanding Claim Value", CP,
            "GREATEST(SUM(claimed_amount) - SUM(paid_amount), 0)", unit=CURRENCY,
            higher_is_better=False),
]

WORKFORCE: list[KpiSpec] = [
    KpiSpec("total_employees", "Total Employees", WF, "SUM(headcount)", unit=COUNT),
    KpiSpec("active_employees", "Active Employees", "silver_dim_staff",
            "COUNT(DISTINCT staff_id) FILTER (WHERE status = 'Active')",
            date_col="", unit=COUNT,
            description="Staff records marked Active in the synthetic staff dimension."),
    KpiSpec("scheduled_hours", "Scheduled Hours", WF, "SUM(scheduled_hours)", unit=HOURS),
    KpiSpec("worked_hours", "Worked Hours", WF, "SUM(worked_hours)", unit=HOURS),
    KpiSpec("overtime_hours", "Overtime Hours", WF, "SUM(overtime_hours)", unit=HOURS,
            higher_is_better=False),
    KpiSpec("absence_rate", "Absence Rate", WF,
            _wavg("absence_rate", "headcount"), unit=PERCENT, higher_is_better=False),
    KpiSpec("shift_coverage", "Shift Coverage", WF,
            _wavg("coverage_pct", "headcount"), unit=PERCENT),
    KpiSpec("staffing_shortage", "Staffing Shortage", WF,
            "SUM(CASE WHEN coverage_pct < 100 THEN 1 ELSE 0 END)", unit=COUNT,
            higher_is_better=False,
            description="Hospital-department-months with shift coverage below 100%."),
    KpiSpec("nurse_to_patient_ratio", "Nurse-to-Patient Ratio", WF,
            "SUM(gold_workforce.headcount) * 0.6 / NULLIF(SUM(h.encounters), 0)",
            join_sql="JOIN gold_hospital_monthly h ON h.hospital_id = gold_workforce.hospital_id "
                     "AND h.month = gold_workforce.month",
            date_col="month", date_col_sql="gold_workforce.month", unit=RATIO, higher_is_better=False,
            description="Estimated nursing headcount (60% of staff) per encounter in the period."),
    KpiSpec("physician_utilization", "Physician Utilization", PA,
            _pct("SUM(completed)", "SUM(scheduled)"), unit=PERCENT,
            description="Completed appointments as a share of scheduled appointments."),
    KpiSpec("workforce_cost", "Workforce Cost", WF, "SUM(workforce_cost)", unit=CURRENCY),
    KpiSpec("open_staffing_gaps", "Open Staffing Gaps", WF,
            "SUM(GREATEST(100 - coverage_pct, 0) / 100.0)", unit=COUNT,
            higher_is_better=False,
            description="Under-covered department-months expressed as 8-hour-equivalent gaps."),
]

INVENTORY: list[KpiSpec] = [
    KpiSpec("inventory_value", "Inventory Value", IV, "SUM(inventory_value)", unit=CURRENCY),
    KpiSpec("total_skus", "Total SKUs", "silver_inventory_movements",
            "COUNT(DISTINCT item_id)", date_col="movement_date", unit=COUNT),
    KpiSpec("stock_available", "Stock Available", "silver_inventory_movements",
            "SUM(quantity) FILTER (WHERE movement_type = 'Receipt') - "
            "SUM(quantity) FILTER (WHERE movement_type IN ('Issue', 'Waste', 'Expiry'))",
            date_col="movement_date", unit=COUNT),
    KpiSpec("stockouts", "Stockout Items", IV, "SUM(stockouts)", unit=COUNT,
            higher_is_better=False, aliases=("stockout_items",)),
    KpiSpec("low_stock", "Low-Stock Items", IV, "SUM(low_stock)", unit=COUNT,
            higher_is_better=False, aliases=("low_stock_items",)),
    KpiSpec("expiring_items", "Expiring Items", "silver_inventory_movements",
            "COUNT(DISTINCT item_id) FILTER (WHERE CAST(expiry_date AS DATE) <= "
            "CAST($date_to AS DATE) + INTERVAL '90' DAY)",
            date_col="movement_date", unit=COUNT, higher_is_better=False,
            description="Distinct items expiring within 90 days of the selected date range."),
    KpiSpec("expired_inventory_value", "Expired Inventory Value", IV, "SUM(expired_value)",
            unit=CURRENCY, higher_is_better=False),
    KpiSpec("inventory_turnover", "Inventory Turnover", IV,
            _wavg("turnover", "inventory_value"), unit=RATIO),
    KpiSpec("purchase_orders", "Purchase Orders", IV, "SUM(purchase_orders)", unit=COUNT),
    KpiSpec("procurement_value", "Procurement Value", IV, "SUM(procurement_value)", unit=CURRENCY),
    KpiSpec("supplier_delivery", "Supplier Delivery Performance", IV,
            _wavg("supplier_on_time_rate", "inventory_value"), unit=PERCENT,
            aliases=("supplier_delivery_performance",)),
    KpiSpec("inventory_waste", "Inventory Waste", IV, "SUM(waste)", unit=CURRENCY,
            higher_is_better=False),
]

EXPERIENCE: list[KpiSpec] = [
    KpiSpec("total_feedback", "Total Feedback", PE, "SUM(feedback_count)", unit=COUNT),
    KpiSpec("average_satisfaction", "Average Satisfaction Score", PE,
            _wavg("avg_rating", "feedback_count"), unit=SCORE,
            aliases=("average_satisfaction_score",)),
    KpiSpec("satisfaction_percentage", "Satisfaction Percentage", PE,
            _wavg("satisfaction_pct", "feedback_count"), unit=PERCENT),
    KpiSpec("nps", "Net Promoter Score", PE, _wavg("nps", "feedback_count"), unit=SCORE,
            aliases=("net_promoter_score",)),
    KpiSpec("positive_feedback", "Positive Feedback Percentage", "silver_feedback",
            _pct("COUNT(*) FILTER (WHERE sentiment_label ILIKE '%Positive%')", "COUNT(*)"),
            date_col="visit_date", unit=PERCENT,
            aliases=("positive_feedback_percentage",),
            description="Share of synthetic feedback records labelled Positive."),
    KpiSpec("negative_feedback_percentage", "Negative Feedback Percentage", "silver_feedback",
            _pct("COUNT(*) FILTER (WHERE sentiment_label ILIKE '%Negative%')", "COUNT(*)"),
            date_col="visit_date", unit=PERCENT, higher_is_better=False,
            description="Share of synthetic feedback records labelled Negative."),
    KpiSpec("complaints", "Complaints", PE, "SUM(complaints)", unit=COUNT,
            higher_is_better=False),
    KpiSpec("complaint_resolution_time", "Complaint Resolution Time", PE,
            _wavg("complaint_resolution_days", "complaints"), unit=DAYS, higher_is_better=False),
    KpiSpec("response_rate", "Response Rate", "silver_feedback",
            _pct("COUNT(*) FILTER (WHERE resolution_status IS NOT NULL AND resolution_status <> '')", "COUNT(*)"),
            date_col="visit_date", unit=PERCENT,
            description="Share of feedback records with a recorded resolution status."),
    KpiSpec("experience_trend", "Experience Trend", PE,
            "COALESCE(REGR_SLOPE(avg_rating, date_diff('day', DATE '2025-01-01', CAST(month AS DATE))), 0)",
            unit=SCORE, description="Monthly linear trend of average satisfaction rating."),
]

QUALITY: list[KpiSpec] = [
    KpiSpec("total_incidents", "Total Incidents", QS, "SUM(incidents)", unit=COUNT,
            higher_is_better=False),
    KpiSpec("incident_rate", "Incident Rate", QS,
            _wavg("incident_rate", "incidents"), unit=PERCENT, higher_is_better=False),
    KpiSpec("falls", "Falls Reported", QS, "SUM(falls)", unit=COUNT,
            higher_is_better=False, aliases=("falls_reported",)),
    KpiSpec("medication_incidents", "Medication Incidents", QS,
            "SUM(medication_incidents)", unit=COUNT, higher_is_better=False),
    KpiSpec("infection_incidents", "Infection-Related Incidents", QS,
            "SUM(infection_incidents)", unit=COUNT, higher_is_better=False),
    KpiSpec("incident_severity_distribution", "Incident Severity Distribution", "silver_incidents",
            "COUNT(DISTINCT severity)", date_col="incident_date", unit=COUNT,
            description="Number of distinct severity levels observed in the period."),
    KpiSpec("investigation_completion", "Investigation Completion Rate", QS,
            _wavg("investigation_completion_rate", "incidents"), unit=PERCENT,
            aliases=("investigation_completion_rate",)),
    KpiSpec("average_investigation_time", "Average Investigation Time", QS,
            _wavg_nonnull("avg_investigation_days", "incidents"), unit=DAYS,
            higher_is_better=False, aliases=("avg_investigation_time",),
            description="Incident-weighted mean of completed investigations; incidents with no duration are excluded."),
    KpiSpec("readmission_rate", "Readmission Rate", H,
            _pct("SUM(readmissions)", "SUM(discharges)"), unit=PERCENT,
            higher_is_better=False,
            description="Readmissions per discharge. The incident-weighted variant was not a canonical KPI."),
    KpiSpec("compliance_indicator", "Compliance Indicator", "silver_incidents",
            _pct("COUNT(*) FILTER (WHERE investigation_complete_flag)", "COUNT(*)"),
            date_col="incident_date", unit=PERCENT,
            description="Share of incidents with a completed investigation."),
]

SPECS: dict[str, list[KpiSpec]] = {
    "overview": NETWORK,
    "hospital": HOSPITAL,
    "appointments": APPOINTMENTS,
    "emergency": EMERGENCY,
    "inpatient": INPATIENT,
    "procedures": PROCEDURES,
    "diagnostics": DIAGNOSTICS,
    "pharmacy": PHARMACY,
    "finance": FINANCE,
    "claims": CLAIMS,
    "workforce": WORKFORCE,
    "inventory": INVENTORY,
    "experience": EXPERIENCE,
    "quality": QUALITY,
}
