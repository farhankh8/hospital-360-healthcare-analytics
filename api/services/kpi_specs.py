"""KPI specifications used by every /kpis endpoint.

Each spec is pure SQL against gold/silver tables in DuckDB. Values, previous
periods, changes and sparklines are computed centrally by `build_kpis`.
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
DAYS = "days"
SCORE = "score"


def _pct(num: str, den: str) -> str:
    return f"{num} * 100.0 / NULLIF({den}, 0)"


def _wavg(expr: str, weight: str) -> str:
    return f"SUM(({expr}) * ({weight})) / NULLIF(SUM({weight}), 0)"


NETWORK: list[KpiSpec] = [
    KpiSpec("total_patients", "Total Patients", "silver_encounters",
            "COUNT(DISTINCT patient_id)", "arrival_datetime", COUNT, description="Distinct patients with an encounter in the period."),
    KpiSpec("total_encounters", "Total Encounters", H, "SUM(encounters)", description="All outpatient, emergency and inpatient encounters."),
    KpiSpec("total_admissions", "Total Admissions", H, "SUM(admissions)", description="Inpatient admissions in the period."),
    KpiSpec("total_revenue", "Total Revenue", H, "SUM(gross_revenue)", CURRENCY, description="Gross charged revenue before discounts."),
    KpiSpec("net_collections", "Net Collections", H, "SUM(collections)", CURRENCY, description="Cash collected against invoices."),
    KpiSpec("average_occupancy", "Average Occupancy", H,
            _pct("SUM(occupied_bed_days)", "SUM(available_bed_days)"), PERCENT,
            description="Occupied bed days divided by available (non-blocked) bed days."),
    KpiSpec("average_los", "Average Length of Stay", H,
            "SUM(avg_los_days * discharges) / NULLIF(SUM(discharges), 0)", DAYS,
            higher_is_better=False, description="Discharge-weighted average length of stay."),
    KpiSpec("patient_satisfaction", "Patient Satisfaction", PE,
            _wavg("satisfaction_pct", "feedback_count"), PERCENT,
            description="Feedback-weighted satisfaction percentage."),
    KpiSpec("no_show_rate", "No-Show Rate", H,
            _pct("SUM(no_show_appointments)", "SUM(completed_appointments + no_show_appointments)"), PERCENT,
            higher_is_better=False, description="No-shows divided by completed plus no-show appointments; cancellations excluded."),
    KpiSpec("claim_denial_rate", "Claim Denial Rate", CP,
            _pct("SUM(denied)", "SUM(approved + denied)"), PERCENT,
            higher_is_better=False, description="Denied claims divided by adjudicated claims."),
]

HOSPITAL: list[KpiSpec] = [
    KpiSpec("patients", "Patients", "silver_encounters", "COUNT(DISTINCT patient_id)", "arrival_datetime"),
    KpiSpec("encounters", "Encounters", H, "SUM(encounters)"),
    KpiSpec("admissions", "Admissions", H, "SUM(admissions)"),
    KpiSpec("revenue", "Revenue", H, "SUM(gross_revenue)", CURRENCY),
    KpiSpec("occupancy", "Occupancy", H, _pct("SUM(occupied_bed_days)", "SUM(available_bed_days)"), PERCENT),
    KpiSpec("average_los", "Average LOS", H, "SUM(avg_los_days * discharges) / NULLIF(SUM(discharges), 0)", DAYS, higher_is_better=False),
    KpiSpec("patient_satisfaction", "Patient Satisfaction", PE, _wavg("satisfaction_pct", "feedback_count"), PERCENT),
    KpiSpec("staff_count", "Staff Count", WF, "SUM(headcount)", COUNT),
]

APPOINTMENTS: list[KpiSpec] = [
    KpiSpec("scheduled_appointments", "Scheduled Appointments", PA, "SUM(scheduled)"),
    KpiSpec("completed_appointments", "Completed Appointments", PA, "SUM(completed)"),
    KpiSpec("cancelled_appointments", "Cancelled Appointments", PA, "SUM(cancelled)", higher_is_better=False),
    KpiSpec("no_show_appointments", "No-Show Appointments", PA, "SUM(no_shows)", higher_is_better=False),
    KpiSpec("no_show_rate", "No-Show Rate", PA, _pct("SUM(no_shows)", "SUM(completed + no_shows)"), PERCENT, higher_is_better=False),
    KpiSpec("avg_wait_appointment", "Average Wait for Appointment", PA, _wavg("avg_lead_days", "scheduled"), DAYS, higher_is_better=False),
    KpiSpec("avg_checkin_wait", "Average Check-in Waiting Time", PA, _wavg("avg_wait_minutes", "scheduled"), MINUTES, higher_is_better=False),
    KpiSpec("appointment_utilization", "Appointment Utilization", PA, _pct("SUM(completed)", "SUM(scheduled)"), PERCENT),
    KpiSpec("same_day_pct", "Same-Day Appointments", PA, _wavg("same_day_pct", "scheduled"), PERCENT),
    KpiSpec("rescheduling_rate", "Rescheduling Rate", PA, _wavg("reschedule_rate", "scheduled"), PERCENT, higher_is_better=False),
]

EMERGENCY: list[KpiSpec] = [
    KpiSpec("emergency_visits", "Emergency Visits", "silver_encounters",
            "COUNT(*) FILTER (WHERE encounter_type = 'Emergency')", "arrival_datetime"),
    KpiSpec("avg_triage_time", "Average Triage Time", "silver_encounters",
            "AVG(date_diff('minute', arrival_datetime, triage_datetime)) FILTER (WHERE encounter_type = 'Emergency')",
            "arrival_datetime", MINUTES, higher_is_better=False),
    KpiSpec("avg_waiting_time", "Average Waiting Time", "silver_encounters",
            "AVG(waiting_minutes) FILTER (WHERE encounter_type = 'Emergency')", "arrival_datetime", MINUTES, higher_is_better=False),
    KpiSpec("avg_treatment_time", "Average Treatment Time", "silver_encounters",
            "AVG(treatment_minutes) FILTER (WHERE encounter_type = 'Emergency')", "arrival_datetime", MINUTES),
    KpiSpec("patients_admitted", "Patients Admitted", "silver_encounters",
            "COUNT(*) FILTER (WHERE disposition = 'Admit')", "arrival_datetime"),
    KpiSpec("patients_discharged", "Patients Discharged", "silver_encounters",
            "COUNT(*) FILTER (WHERE disposition = 'Discharge')", "arrival_datetime"),
    KpiSpec("patients_transferred", "Patients Transferred", "silver_encounters",
            "COUNT(*) FILTER (WHERE disposition = 'Transfer')", "arrival_datetime"),
    KpiSpec("left_without_seen", "Left Without Being Seen", "silver_encounters",
            "COUNT(*) FILTER (WHERE disposition = 'LWBS')", "arrival_datetime", higher_is_better=False),
    KpiSpec("critical_patient_volume", "Critical Patient Volume", "silver_encounters",
            "COUNT(*) FILTER (WHERE critical_flag)", "arrival_datetime"),
]

INPATIENT: list[KpiSpec] = [
    KpiSpec("total_beds", "Total Beds", BU, "SUM(total_beds)"),
    KpiSpec("available_beds", "Available Beds", BU, "SUM(available_bed_days) / NULLIF(COUNT(DISTINCT month || ward), 0)"),
    KpiSpec("occupied_beds", "Occupied Beds", BU, "SUM(occupied_bed_days) / NULLIF(COUNT(DISTINCT month || ward), 0)"),
    KpiSpec("blocked_beds", "Blocked Beds", BU, "SUM(blocked_bed_days) / NULLIF(COUNT(DISTINCT month || ward), 0)"),
    KpiSpec("occupancy_rate", "Occupancy Rate", BU, _pct("SUM(occupied_bed_days)", "SUM(available_bed_days)"), PERCENT),
    KpiSpec("average_los", "Average LOS", BU, _wavg("avg_los_days", "occupied_bed_days"), DAYS, higher_is_better=False),
    KpiSpec("bed_turnover", "Bed Turnover", BU, _wavg("bed_turnover", "available_bed_days")),
    KpiSpec("admissions", "Admissions", H, "SUM(admissions)"),
    KpiSpec("discharges", "Discharges", H, "SUM(discharges)"),
    KpiSpec("readmission_rate", "Readmission Rate", H, _pct("SUM(readmissions)", "SUM(discharges)"), PERCENT, higher_is_better=False),
    KpiSpec("boarding_hours", "Average Boarding Time", BU, _wavg("avg_boarding_hours", "occupied_bed_days"), DAYS, higher_is_better=False),
]

PROCEDURES: list[KpiSpec] = [
    KpiSpec("scheduled_procedures", "Scheduled Procedures", "silver_procedures", "COUNT(*)"),
    KpiSpec("completed_procedures", "Completed Procedures", "silver_procedures",
            "COUNT(*) FILTER (WHERE status = 'Completed')"),
    KpiSpec("cancelled_procedures", "Cancelled Procedures", "silver_procedures",
            "COUNT(*) FILTER (WHERE status = 'Cancelled')", higher_is_better=False),
    KpiSpec("cancellation_rate", "Cancellation Rate", "silver_procedures",
            _pct("COUNT(*) FILTER (WHERE status = 'Cancelled')", "COUNT(*)"), PERCENT, higher_is_better=False),
    KpiSpec("avg_procedure_duration", "Average Procedure Duration", "silver_procedures",
            "AVG(duration_minutes)", MINUTES),
    KpiSpec("delayed_procedures", "Delayed Procedures", "silver_procedures",
            "COUNT(*) FILTER (WHERE status = 'Delayed' OR delay_minutes > 0)", higher_is_better=False),
    KpiSpec("procedure_revenue", "Procedure Revenue", "silver_procedures", "SUM(revenue)", CURRENCY),
]

DIAGNOSTICS: list[KpiSpec] = [
    KpiSpec("total_lab_orders", "Total Lab Orders", LP, "SUM(orders)"),
    KpiSpec("completed_tests", "Completed Tests", LP, "SUM(completed)"),
    KpiSpec("pending_tests", "Pending Tests", LP, "SUM(pending)", higher_is_better=False),
    KpiSpec("cancelled_tests", "Cancelled Tests", LP, "SUM(cancelled)", higher_is_better=False),
    KpiSpec("avg_tat", "Average Turnaround Time", LP, _wavg("avg_tat_minutes", "orders"), MINUTES, higher_is_better=False),
    KpiSpec("median_tat", "Median Turnaround Time", LP, _wavg("median_tat_minutes", "orders"), MINUTES, higher_is_better=False),
    KpiSpec("sla_compliance", "SLA Compliance Rate", LP, _wavg("sla_rate", "orders"), PERCENT),
    KpiSpec("delayed_results", "Delayed Results", LP, "SUM(delayed)", higher_is_better=False),
    KpiSpec("critical_results", "Critical Results", LP, "SUM(critical)"),
]

PHARMACY: list[KpiSpec] = [
    KpiSpec("prescriptions", "Prescriptions", "silver_prescriptions", "COUNT(*)"),
    KpiSpec("items_prescribed", "Items Prescribed", "silver_prescriptions", "SUM(quantity)"),
    KpiSpec("items_dispensed", "Items Dispensed", "silver_dispensing", "SUM(quantity_dispensed)"),
    KpiSpec("pending_prescriptions", "Pending Prescriptions", "silver_prescriptions",
            "COUNT(*) FILTER (WHERE status = 'Pending')", higher_is_better=False),
    KpiSpec("dispensing_completion", "Dispensing Completion Rate", "silver_prescriptions",
            _pct("COUNT(*) FILTER (WHERE status = 'Dispensed')", "COUNT(*)"), PERCENT),
    KpiSpec("medication_revenue", "Medication Revenue", "silver_prescriptions", "SUM(amount)", CURRENCY),
    KpiSpec("avg_prescription_value", "Average Prescription Value", "silver_prescriptions", "AVG(amount)", CURRENCY),
]

FINANCE: list[KpiSpec] = [
    KpiSpec("gross_revenue", "Gross Revenue", H, "SUM(gross_revenue)", CURRENCY),
    KpiSpec("net_revenue", "Net Revenue", H, "SUM(net_revenue)", CURRENCY),
    KpiSpec("total_billed", "Total Billed", H, "SUM(gross_revenue)", CURRENCY),
    KpiSpec("total_collected", "Total Collected", H, "SUM(collections)", CURRENCY),
    KpiSpec("outstanding_receivables", "Outstanding Receivables", H, "SUM(outstanding_balance)", CURRENCY, higher_is_better=False),
    KpiSpec("collection_rate", "Collection Rate", H, _pct("SUM(collections)", "SUM(net_revenue)"), PERCENT),
    KpiSpec("avg_invoice_value", "Average Invoice Value", FP, _wavg("avg_invoice_value", "net_revenue"), CURRENCY),
    KpiSpec("refund_amount", "Refund Amount", FP, "SUM(refunds)", CURRENCY, higher_is_better=False),
    KpiSpec("writeoff_amount", "Write-off Amount", FP, "SUM(writeoffs)", CURRENCY, higher_is_better=False),
    KpiSpec("revenue_growth", "Revenue Growth", FP, "AVG(revenue_growth_pct)", PERCENT),
]

CLAIMS: list[KpiSpec] = [
    KpiSpec("claims_submitted", "Claims Submitted", CP, "SUM(claims)"),
    KpiSpec("claims_approved", "Claims Approved", CP, "SUM(approved)"),
    KpiSpec("claims_denied", "Claims Denied", CP, "SUM(denied)", higher_is_better=False),
    KpiSpec("denial_rate", "Denial Rate", CP, _pct("SUM(denied)", "SUM(approved + denied)"), PERCENT, higher_is_better=False),
    KpiSpec("pending_claims", "Pending Claims", CP, "GREATEST(SUM(claims) - SUM(approved) - SUM(denied), 0)", higher_is_better=False),
    KpiSpec("total_claimed_amount", "Total Claimed Amount", CP, "SUM(claimed_amount)", CURRENCY),
    KpiSpec("approved_amount", "Approved Amount", CP, "SUM(approved_amount)", CURRENCY),
    KpiSpec("paid_amount", "Paid Amount", CP, "SUM(paid_amount)", CURRENCY),
    KpiSpec("avg_processing_time", "Average Processing Time", CP, _wavg("avg_processing_days", "claims"), DAYS, higher_is_better=False),
    KpiSpec("appeal_success_rate", "Appeal Success Rate", CP, _wavg("appeal_success_rate", "appeals"), PERCENT),
    KpiSpec("outstanding_claim_value", "Outstanding Claim Value", CP, "GREATEST(SUM(claimed_amount) - SUM(paid_amount), 0)", CURRENCY, higher_is_better=False),
]

WORKFORCE: list[KpiSpec] = [
    KpiSpec("total_employees", "Total Employees", WF, "SUM(headcount)"),
    KpiSpec("scheduled_hours", "Scheduled Hours", WF, "SUM(scheduled_hours)"),
    KpiSpec("worked_hours", "Worked Hours", WF, "SUM(worked_hours)"),
    KpiSpec("overtime_hours", "Overtime Hours", WF, "SUM(overtime_hours)", higher_is_better=False),
    KpiSpec("absence_rate", "Absence Rate", WF, _wavg("absence_rate", "headcount"), PERCENT, higher_is_better=False),
    KpiSpec("shift_coverage", "Shift Coverage", WF, _wavg("coverage_pct", "headcount"), PERCENT),
    KpiSpec("workforce_cost", "Workforce Cost", WF, "SUM(workforce_cost)", CURRENCY),
]

INVENTORY: list[KpiSpec] = [
    KpiSpec("inventory_value", "Inventory Value", IV, "SUM(inventory_value)", CURRENCY),
    KpiSpec("stockouts", "Stockout Items", IV, "SUM(stockouts)", higher_is_better=False),
    KpiSpec("low_stock", "Low-Stock Items", IV, "SUM(low_stock)", higher_is_better=False),
    KpiSpec("expired_inventory_value", "Expired Inventory Value", IV, "SUM(expired_value)", CURRENCY, higher_is_better=False),
    KpiSpec("inventory_turnover", "Inventory Turnover", IV, _wavg("turnover", "inventory_value")),
    KpiSpec("purchase_orders", "Purchase Orders", IV, "SUM(purchase_orders)"),
    KpiSpec("procurement_value", "Procurement Value", IV, "SUM(procurement_value)", CURRENCY),
    KpiSpec("supplier_delivery", "Supplier Delivery Performance", IV, _wavg("supplier_on_time_rate", "inventory_value"), PERCENT),
    KpiSpec("inventory_waste", "Inventory Waste", IV, "SUM(waste)", CURRENCY, higher_is_better=False),
]

EXPERIENCE: list[KpiSpec] = [
    KpiSpec("total_feedback", "Total Feedback", PE, "SUM(feedback_count)"),
    KpiSpec("average_satisfaction", "Average Satisfaction", PE, _wavg("avg_rating", "feedback_count"), SCORE),
    KpiSpec("satisfaction_percentage", "Satisfaction Percentage", PE, _wavg("satisfaction_pct", "feedback_count"), PERCENT),
    KpiSpec("nps", "Net Promoter Score", PE, _wavg("nps", "feedback_count"), SCORE),
    KpiSpec("positive_feedback", "Positive Feedback", PE, _pct("SUM(promoters)", "SUM(feedback_count)"), PERCENT),
    KpiSpec("complaints", "Complaints", PE, "SUM(complaints)", higher_is_better=False),
    KpiSpec("complaint_resolution_time", "Complaint Resolution Time", PE, _wavg("complaint_resolution_days", "complaints"), DAYS, higher_is_better=False),
]

QUALITY: list[KpiSpec] = [
    KpiSpec("total_incidents", "Total Incidents", QS, "SUM(incidents)", higher_is_better=False),
    KpiSpec("incident_rate", "Incident Rate", QS, _wavg("incident_rate", "incidents"), PERCENT, higher_is_better=False),
    KpiSpec("falls", "Falls Reported", QS, "SUM(falls)", higher_is_better=False),
    KpiSpec("medication_incidents", "Medication Incidents", QS, "SUM(medication_incidents)", higher_is_better=False),
    KpiSpec("infection_incidents", "Infection-Related Incidents", QS, "SUM(infection_incidents)", higher_is_better=False),
    KpiSpec("critical_incidents", "Critical Incidents", QS, "SUM(critical_incidents)", higher_is_better=False),
    KpiSpec("investigation_completion", "Investigation Completion Rate", QS, _wavg("investigation_completion_rate", "incidents"), PERCENT),
    KpiSpec("avg_investigation_time", "Average Investigation Time", QS, _wavg("avg_investigation_days", "incidents"), DAYS, higher_is_better=False),
    KpiSpec("readmission_rate", "Readmission Rate", QS, _wavg("readmission_rate", "incidents"), PERCENT, higher_is_better=False),
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
