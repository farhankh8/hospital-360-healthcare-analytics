import type { ChartConfig, ChartType, ColumnType, FilterKey, NavGroup, PageConfig, TableColumn } from './types';

export type PageSlug =
  | 'overview'
  | 'hospitals'
  | 'hospitalsProfile'
  | 'appointments'
  | 'emergency'
  | 'inpatient'
  | 'procedures'
  | 'diagnostics'
  | 'pharmacy'
  | 'finance'
  | 'claims'
  | 'workforce'
  | 'inventory'
  | 'experience'
  | 'quality'
  | 'explorer'
  | 'patientJourney'
  | 'dataQuality'
  | 'pipeline'
  | 'kpiGlossary'
  | 'methodology';

const chart = (
  title: string,
  endpoint: string,
  type: ChartType,
  dataKey: string,
  extra: Partial<ChartConfig> = {},
): ChartConfig => ({ title, endpoint, type, dataKey, ...extra });

const col = (key: string, title: string, type?: ColumnType): TableColumn => ({ key, title, type, sortable: true });

const ALL: FilterKey[] = [
  'date_from',
  'date_to',
  'hospital_ids',
  'department_id',
  'specialty_id',
  'payer_id',
  'encounter_type',
  'patient_type',
];
const CORE: FilterKey[] = ['date_from', 'date_to', 'hospital_ids', 'department_id', 'specialty_id'];
const DATE_ONLY: FilterKey[] = ['date_from', 'date_to'];

const hospitalColumns: TableColumn[] = [
  col('hospital_id', 'Hospital ID'),
  col('hospital_name', 'Hospital'),
  col('patients', 'Patients', 'number'),
  col('encounters', 'Encounters', 'number'),
  col('revenue', 'Revenue', 'currency'),
  col('occupancy_rate', 'Occupancy', 'percent'),
  col('avg_satisfaction', 'Satisfaction', 'number'),
  col('no_show_rate', 'No-show rate', 'percent'),
];

const appointmentColumns: TableColumn[] = [
  col('appointment_id', 'Appointment ID'),
  col('patient_id', 'Patient ID'),
  col('hospital_id', 'Hospital'),
  col('department_name', 'Department'),
  col('doctor_name', 'Doctor'),
  col('scheduled_date', 'Scheduled', 'date'),
  col('appointment_type', 'Type'),
  col('status', 'Status', 'badge'),
  col('waiting_minutes', 'Wait (min)', 'number'),
  col('no_show_flag', 'No-show'),
];

const encounterColumns: TableColumn[] = [
  col('encounter_id', 'Encounter ID'),
  col('patient_id', 'Patient ID'),
  col('hospital_id', 'Hospital'),
  col('department_name', 'Department'),
  col('encounter_date', 'Date', 'date'),
  col('encounter_type', 'Type'),
  col('status', 'Status', 'badge'),
];

const claimColumns: TableColumn[] = [
  col('claim_id', 'Claim ID'),
  col('invoice_id', 'Invoice ID'),
  col('hospital_id', 'Hospital'),
  col('payer_name', 'Payer'),
  col('claim_date', 'Claim date', 'date'),
  col('claimed_amount', 'Claimed', 'currency'),
  col('approved_amount', 'Approved', 'currency'),
  col('paid_amount', 'Paid', 'currency'),
  col('status', 'Status', 'badge'),
  col('denial_reason', 'Denial reason'),
];

const invoiceColumns: TableColumn[] = [
  col('invoice_id', 'Invoice ID'),
  col('encounter_id', 'Encounter ID'),
  col('patient_id', 'Patient ID'),
  col('hospital_id', 'Hospital'),
  col('invoice_date', 'Invoice date', 'date'),
  col('gross_amount', 'Gross', 'currency'),
  col('net_amount', 'Net', 'currency'),
  col('paid_amount', 'Paid', 'currency'),
  col('balance', 'Balance', 'currency'),
  col('status', 'Status', 'badge'),
];

export const pages: Record<PageSlug, PageConfig> = {
  overview: {
    slug: 'overview',
    path: '/overview',
    title: 'Network Overview',
    description: 'Executive view of patients, capacity, finance, access and quality across the network.',
    navGroup: 'Overview',
    kpiEndpoint: '/overview/kpis',
    kpiIds: [
      'total_patients',
      'total_encounters',
      'total_admissions',
      'total_revenue',
      'net_collections',
      'average_occupancy',
      'average_los',
      'patient_satisfaction',
      'no_show_rate',
      'claim_denial_rate',
    ],
    charts: [
      chart('Patient volume trend', '/overview/trends', 'line', 'trends', { xKey: 'month', span: 2, description: 'Patients, encounters and admissions by month' }),
      chart('Revenue, collections and balances', '/overview/trends', 'line', 'revenue', {
        xKey: 'month',
        seriesKeys: ['revenue', 'collections', 'outstanding_balance'],
        span: 2,
      }),
      chart('Hospital performance ranking', '/overview/hospital-ranking', 'horizontal-bar', 'ranking', {
        xKey: 'hospital_name',
        span: 1,
        description: 'Compare hospitals on the selected metric',
      }),
      chart('Hospital KPI heatmap', '/overview/heatmap', 'heatmap', 'heatmap', { span: 1 }),
      chart('Patient distribution', '/overview/distribution', 'bar', 'distribution', { span: 1 }),
      chart('Operational performance', '/overview/operational', 'radar', 'operational', {
        span: 1,
        description: 'Normalised access, capacity, finance, experience and workforce indices',
      }),
    ],
    tableEndpoint: '/hospitals',
    tableColumns: hospitalColumns,
    filters: ALL,
  },

  hospitals: {
    slug: 'hospitals',
    path: '/hospitals',
    title: 'Hospital Comparison',
    description: 'Compare every hospital in the network on volume, capacity, finance and outcomes.',
    navGroup: 'Overview',
    kpiEndpoint: '/overview/kpis',
    kpiIds: ['total_patients', 'total_encounters', 'total_revenue', 'average_occupancy', 'patient_satisfaction', 'claim_denial_rate'],
    charts: [
      chart('Revenue ranking', '/overview/hospital-ranking', 'horizontal-bar', 'revenue', { xKey: 'hospital_name', span: 1 }),
      chart('Patient volume ranking', '/overview/hospital-ranking', 'bar', 'patients', { xKey: 'hospital_name', span: 1 }),
      chart('Occupancy comparison', '/overview/heatmap', 'bar', 'occupancy_rate', { xKey: 'hospital_name', span: 1 }),
      chart('Satisfaction comparison', '/overview/hospital-ranking', 'bar', 'avg_satisfaction', { xKey: 'hospital_name', span: 1 }),
      chart('Monthly hospital trends', '/overview/trends', 'line', 'trends', { xKey: 'month', span: 2 }),
      chart('KPI heatmap', '/overview/heatmap', 'heatmap', 'heatmap', { span: 2 }),
    ],
    tableEndpoint: '/hospitals',
    tableColumns: hospitalColumns,
    filters: ALL,
  },

  hospitalsProfile: {
    slug: 'hospitalsProfile',
    path: '/hospitals/[id]',
    title: 'Hospital Profile',
    description: 'Operational, financial and experience detail for a single hospital.',
    navGroup: 'Overview',
    kpiEndpoint: '/hospitals/{id}/kpis',
    kpiIds: [
      'total_patients',
      'total_encounters',
      'total_admissions',
      'total_revenue',
      'average_occupancy',
      'average_los',
      'patient_satisfaction',
      'no_show_rate',
    ],
    charts: [
      chart('Monthly patient volume', '/hospitals/{id}/trends', 'line', 'trends', { xKey: 'month', span: 2 }),
      chart('Department performance', '/hospitals/{id}/departments', 'horizontal-bar', 'departments', { xKey: 'department_name', span: 1 }),
      chart('Revenue trend', '/hospitals/{id}/trends', 'area', 'revenue', { xKey: 'month', span: 1 }),
    ],
    tableEndpoint: '/hospitals/{id}/departments',
    tableColumns: [
      col('department_id', 'Department ID'),
      col('department_name', 'Department'),
      col('specialty_name', 'Specialty'),
      col('patients', 'Patients', 'number'),
      col('encounters', 'Encounters', 'number'),
      col('revenue', 'Revenue', 'currency'),
      col('occupancy_rate', 'Occupancy', 'percent'),
      col('avg_satisfaction', 'Satisfaction', 'number'),
    ],
    profileEndpoint: '/hospitals/{id}/profile',
    filters: CORE,
  },

  appointments: {
    slug: 'appointments',
    path: '/appointments',
    title: 'Appointments & Access',
    description: 'Scheduling efficiency, attendance, waiting times and patient access.',
    navGroup: 'Operations',
    kpiEndpoint: '/appointments/kpis',
    kpiIds: [
      'scheduled_appointments',
      'completed_appointments',
      'cancelled_appointments',
      'no_show_appointments',
      'no_show_rate',
      'avg_wait_minutes',
      'same_day_pct',
      'reschedule_rate',
    ],
    charts: [
      chart('Appointment volume', '/appointments/trends', 'line', 'trends', { xKey: 'month', span: 2 }),
      chart('No-show rate trend', '/appointments/no-shows', 'line', 'no_shows', { xKey: 'month', span: 1 }),
      chart('Waiting times', '/appointments/wait-times', 'bar', 'wait_times', { xKey: 'department_name', span: 1 }),
      chart('Appointment time heatmap', '/appointments/heatmap', 'heatmap', 'heatmap', { span: 1 }),
      chart('No-shows by department', '/appointments/departments', 'horizontal-bar', 'departments', { xKey: 'department_name', span: 1 }),
    ],
    tableEndpoint: '/appointments/records',
    tableColumns: appointmentColumns,
    filters: ALL,
  },

  emergency: {
    slug: 'emergency',
    path: '/emergency',
    title: 'Emergency & Patient Flow',
    description: 'Arrivals, throughput, waiting times and disposition across emergency departments.',
    navGroup: 'Operations',
    kpiEndpoint: '/emergency/kpis',
    kpiIds: [
      'emergency_visits',
      'avg_triage_minutes',
      'avg_wait_minutes',
      'avg_treatment_minutes',
      'patients_admitted',
      'patients_discharged',
      'patients_transferred',
      'left_without_being_seen',
      'critical_patient_volume',
    ],
    charts: [
      chart('Emergency visits trend', '/emergency/trend', 'line', 'trend', { xKey: 'month', span: 2 }),
      chart('Hourly arrivals', '/emergency/arrivals', 'bar', 'arrivals', { xKey: 'hour', span: 1 }),
      chart('Patient flow', '/emergency/flow', 'stacked-bar', 'flow', { xKey: 'stage', span: 1 }),
    ],
    tableEndpoint: '/emergency/records',
    tableColumns: [
      col('encounter_id', 'Encounter ID'),
      col('patient_id', 'Patient ID'),
      col('hospital_id', 'Hospital'),
      col('arrival_time', 'Arrival', 'date'),
      col('triage_category', 'Triage'),
      col('waiting_minutes', 'Wait (min)', 'number'),
      col('disposition', 'Disposition'),
    ],
    filters: ALL,
  },

  inpatient: {
    slug: 'inpatient',
    path: '/inpatient',
    title: 'Inpatient & Beds',
    description: 'Bed capacity, occupancy, length of stay, readmissions and admission flow.',
    navGroup: 'Operations',
    kpiEndpoint: '/inpatient/kpis',
    kpiIds: [
      'total_beds',
      'available_beds',
      'occupied_beds',
      'blocked_beds',
      'average_occupancy',
      'average_los',
      'bed_turnover',
      'admissions',
      'discharges',
      'readmission_rate',
      'avg_boarding_hours',
    ],
    charts: [
      chart('Occupancy trend', '/inpatient/occupancy', 'line', 'occupancy', { xKey: 'month', span: 2 }),
      chart('Length of stay', '/inpatient/los', 'bar', 'los', { xKey: 'specialty_name', span: 1 }),
      chart('Bed status', '/inpatient/bed-status', 'stacked-bar', 'bed_status', { xKey: 'ward', span: 1 }),
      chart('Admissions vs discharges', '/inpatient/admissions', 'line', 'admissions', { xKey: 'month', span: 2 }),
    ],
    tableEndpoint: '/inpatient/records',
    tableColumns: [
      col('admission_id', 'Admission ID'),
      col('patient_id', 'Patient ID'),
      col('hospital_id', 'Hospital'),
      col('ward', 'Ward'),
      col('bed_id', 'Bed'),
      col('admission_date', 'Admitted', 'date'),
      col('discharge_date', 'Discharged', 'date'),
      col('los_days', 'LOS (days)', 'number'),
      col('status', 'Status', 'badge'),
    ],
    filters: ALL,
  },

  procedures: {
    slug: 'procedures',
    path: '/procedures',
    title: 'Surgery & Procedures',
    description: 'Procedure volume, operating room utilisation, delays and cancellations.',
    navGroup: 'Operations',
    kpiEndpoint: '/procedures/kpis',
    kpiIds: [
      'scheduled_procedures',
      'completed_procedures',
      'cancelled_procedures',
      'cancellation_rate',
      'avg_procedure_duration',
      'or_utilization',
      'first_case_on_time_rate',
      'avg_turnaround_minutes',
      'delayed_procedures',
      'procedure_revenue',
    ],
    charts: [
      chart('Procedure volume', '/procedures/volume', 'line', 'volume', { xKey: 'month', span: 2 }),
      chart('OR utilisation', '/procedures/utilization', 'bar', 'utilization', { xKey: 'hospital_id', span: 2 }),
    ],
    tableEndpoint: '/procedures/records',
    tableColumns: [
      col('procedure_id', 'Procedure ID'),
      col('patient_id', 'Patient ID'),
      col('hospital_id', 'Hospital'),
      col('operating_room', 'OR'),
      col('surgeon_name', 'Surgeon'),
      col('procedure_name', 'Procedure'),
      col('scheduled_start', 'Scheduled', 'date'),
      col('duration_minutes', 'Duration', 'number'),
      col('status', 'Status', 'badge'),
    ],
    filters: ALL,
  },

  diagnostics: {
    slug: 'diagnostics',
    path: '/diagnostics',
    title: 'Diagnostics & Laboratory',
    description: 'Lab order volume, turnaround time, SLA compliance and critical results.',
    navGroup: 'Operations',
    kpiEndpoint: '/diagnostics/kpis',
    kpiIds: [
      'total_lab_orders',
      'completed_tests',
      'pending_tests',
      'cancelled_tests',
      'avg_tat_minutes',
      'median_tat_minutes',
      'sla_rate',
      'delayed_results',
      'critical_results',
      'lab_revenue',
    ],
    charts: [
      chart('Turnaround time', '/diagnostics/tat', 'line', 'tat', { xKey: 'month', span: 2 }),
      chart('Test volume', '/diagnostics/volume', 'bar', 'volume', { xKey: 'test_name', span: 2 }),
    ],
    tableEndpoint: '/diagnostics/records',
    tableColumns: [
      col('lab_order_id', 'Lab order ID'),
      col('patient_id', 'Patient ID'),
      col('hospital_id', 'Hospital'),
      col('test_name', 'Test'),
      col('priority', 'Priority'),
      col('ordered_at', 'Ordered', 'date'),
      col('resulted_at', 'Resulted', 'date'),
      col('tat_minutes', 'TAT (min)', 'number'),
      col('status', 'Status', 'badge'),
    ],
    filters: ALL,
  },

  pharmacy: {
    slug: 'pharmacy',
    path: '/pharmacy',
    title: 'Pharmacy',
    description: 'Prescription volume, dispensing performance, medication revenue and stock risk.',
    navGroup: 'Business',
    kpiEndpoint: '/pharmacy/kpis',
    kpiIds: [
      'prescriptions',
      'items_prescribed',
      'items_dispensed',
      'pending_prescriptions',
      'dispensing_completion_rate',
      'medication_revenue',
      'avg_prescription_value',
      'stockout_medications',
      'expired_medication_value',
      'pharmacy_waste',
    ],
    charts: [chart('Pharmacy trend', '/pharmacy/trend', 'line', 'trend', { xKey: 'month', span: 2 })],
    tableEndpoint: '/pharmacy/records',
    tableColumns: [
      col('prescription_id', 'Prescription ID'),
      col('patient_id', 'Patient ID'),
      col('hospital_id', 'Hospital'),
      col('medication_name', 'Medication'),
      col('quantity', 'Quantity', 'number'),
      col('prescribed_date', 'Prescribed', 'date'),
      col('dispensed_date', 'Dispensed', 'date'),
      col('amount', 'Amount', 'currency'),
      col('status', 'Status', 'badge'),
    ],
    filters: ALL,
  },

  finance: {
    slug: 'finance',
    path: '/finance',
    title: 'Finance & Revenue',
    description: 'Gross and net revenue, collections, receivables and revenue leakage.',
    navGroup: 'Business',
    kpiEndpoint: '/finance/kpis',
    kpiIds: [
      'gross_revenue',
      'net_revenue',
      'total_billed',
      'total_collected',
      'outstanding_balance',
      'collection_rate',
      'revenue_per_encounter',
      'avg_invoice_value',
      'refunds',
      'writeoffs',
      'revenue_growth_pct',
    ],
    charts: [
      chart('Revenue trend', '/finance/revenue-trend', 'line', 'revenue_trend', { xKey: 'month', span: 2 }),
      chart('Collections', '/finance/collections', 'bar', 'collections', { xKey: 'month', span: 1 }),
      chart('Receivables ageing', '/finance/receivables', 'bar', 'receivables', { xKey: 'aging_bucket', span: 1 }),
      chart('Revenue by department', '/finance/revenue-by', 'horizontal-bar', 'revenue_by', { xKey: 'department_name', span: 2 }),
    ],
    tableEndpoint: '/finance/invoices',
    tableColumns: invoiceColumns,
    filters: ALL,
  },

  claims: {
    slug: 'claims',
    path: '/claims',
    title: 'Insurance & Claims',
    description: 'Claim submission, adjudication, denials, payer mix and appeals.',
    navGroup: 'Business',
    kpiEndpoint: '/claims/kpis',
    kpiIds: [
      'claims_submitted',
      'claims_approved',
      'claims_denied',
      'claim_denial_rate',
      'pending_claims',
      'claimed_amount',
      'approved_amount',
      'paid_amount',
      'avg_processing_days',
      'appeal_success_rate',
      'outstanding_claim_value',
    ],
    charts: [
      chart('Denial rate trend', '/claims/denials', 'line', 'denials', { xKey: 'month', span: 2 }),
      chart('Claims by payer', '/claims/payers', 'horizontal-bar', 'payers', { xKey: 'payer_name', span: 1 }),
      chart('Claims ageing', '/claims/aging', 'bar', 'aging', { xKey: 'aging_bucket', span: 1 }),
    ],
    tableEndpoint: '/claims/records',
    tableColumns: claimColumns,
    filters: ALL,
  },

  workforce: {
    slug: 'workforce',
    path: '/workforce',
    title: 'Workforce',
    description: 'Staffing levels, shift coverage, overtime, absence and workforce cost.',
    navGroup: 'Business',
    kpiEndpoint: '/workforce/kpis',
    kpiIds: [
      'headcount',
      'scheduled_hours',
      'worked_hours',
      'overtime_hours',
      'absence_rate',
      'coverage_pct',
      'workforce_cost',
    ],
    charts: [
      chart('Coverage', '/workforce/coverage', 'line', 'coverage', { xKey: 'month', span: 2 }),
      chart('Overtime', '/workforce/overtime', 'bar', 'overtime', { xKey: 'department_name', span: 1 }),
      chart('Attendance', '/workforce/attendance', 'bar', 'attendance', { xKey: 'month', span: 1 }),
    ],
    tableEndpoint: '/workforce/records',
    tableColumns: [
      col('staff_id', 'Staff ID'),
      col('hospital_id', 'Hospital'),
      col('department_name', 'Department'),
      col('role', 'Role'),
      col('shift', 'Shift'),
      col('scheduled_hours', 'Scheduled', 'number'),
      col('worked_hours', 'Worked', 'number'),
      col('overtime_hours', 'Overtime', 'number'),
      col('attendance_status', 'Attendance', 'badge'),
    ],
    filters: ALL,
  },

  inventory: {
    slug: 'inventory',
    path: '/inventory',
    title: 'Inventory & Procurement',
    description: 'Stock availability, stockouts, expiry, waste and supplier performance.',
    navGroup: 'Business',
    kpiEndpoint: '/inventory/kpis',
    kpiIds: [
      'inventory_value',
      'low_stock',
      'stockouts',
      'expired_value',
      'inventory_turnover',
      'purchase_orders',
      'procurement_value',
      'supplier_on_time_rate',
      'waste',
    ],
    charts: [
      chart('Stockouts', '/inventory/stockouts', 'line', 'stockouts', { xKey: 'month', span: 2 }),
      chart('Expiry', '/inventory/expiry', 'bar', 'expiry', { xKey: 'category', span: 1 }),
      chart('Inventory movements', '/inventory/movements', 'stacked-bar', 'movements', { xKey: 'month', span: 1 }),
    ],
    tableEndpoint: '/inventory/records',
    tableColumns: [
      col('item_id', 'Item ID'),
      col('item_name', 'Item'),
      col('hospital_id', 'Hospital'),
      col('category', 'Category'),
      col('supplier_name', 'Supplier'),
      col('quantity_available', 'On hand', 'number'),
      col('reorder_level', 'Reorder level', 'number'),
      col('unit_cost', 'Unit cost', 'currency'),
      col('expiry_date', 'Expiry', 'date'),
      col('stock_status', 'Status', 'badge'),
    ],
    filters: ALL,
  },

  experience: {
    slug: 'experience',
    path: '/experience',
    title: 'Patient Experience',
    description: 'Satisfaction, feedback volume, promoters, complaints and resolution.',
    navGroup: 'Performance',
    kpiEndpoint: '/experience/kpis',
    kpiIds: [
      'feedback_count',
      'avg_satisfaction',
      'satisfaction_pct',
      'nps',
      'promoters',
      'detractors',
      'complaints',
      'complaint_resolution_days',
    ],
    charts: [
      chart('Satisfaction trend', '/experience/trend', 'line', 'trend', { xKey: 'month', span: 2 }),
      chart('Satisfaction by hospital', '/experience/by-hospital', 'horizontal-bar', 'by_hospital', { xKey: 'hospital_name', span: 2 }),
    ],
    tableEndpoint: '/experience/records',
    tableColumns: [
      col('feedback_id', 'Feedback ID'),
      col('patient_id', 'Patient ID'),
      col('hospital_id', 'Hospital'),
      col('department_name', 'Department'),
      col('visit_date', 'Visit', 'date'),
      col('avg_rating', 'Rating', 'number'),
      col('category', 'Category'),
      col('sentiment_label', 'Sentiment (synthetic)'),
      col('complaint', 'Complaint'),
      col('resolution_status', 'Status', 'badge'),
    ],
    filters: ALL,
  },

  quality: {
    slug: 'quality',
    path: '/quality',
    title: 'Quality & Safety',
    description: 'Incidents, severity, investigation completion and readmission indicators.',
    navGroup: 'Performance',
    kpiEndpoint: '/quality/kpis',
    kpiIds: [
      'incidents',
      'incident_rate',
      'falls',
      'medication_incidents',
      'infection_incidents',
      'critical_incidents',
      'investigation_completion_rate',
      'avg_investigation_days',
      'readmission_rate',
    ],
    charts: [
      chart('Incident trend', '/quality/trend', 'line', 'trend', { xKey: 'month', span: 2 }),
      chart('Incidents by category', '/quality/incidents', 'bar', 'incidents', { xKey: 'category', span: 2 }),
    ],
    tableEndpoint: '/quality/records',
    tableColumns: [
      col('incident_id', 'Incident ID'),
      col('hospital_id', 'Hospital'),
      col('department_name', 'Department'),
      col('incident_date', 'Incident date', 'date'),
      col('category', 'Category'),
      col('severity', 'Severity', 'badge'),
      col('status', 'Status', 'badge'),
      col('investigation_complete', 'Investigated'),
      col('resolution_date', 'Resolved', 'date'),
    ],
    filters: ALL,
  },

  explorer: {
    slug: 'explorer',
    path: '/explorer',
    title: 'Data Explorer',
    description: 'Inspect validated record-level datasets, schemas and source lineage.',
    navGroup: 'Data & Intelligence',
    kpiIds: [],
    charts: [],
    filters: DATE_ONLY,
    special: true,
    tableColumns: [],
  },

  patientJourney: {
    slug: 'patientJourney',
    path: '/patient-journey',
    title: 'Patient Journey',
    description: 'Follow one synthetic patient across appointments, encounters, billing and feedback.',
    navGroup: 'Data & Intelligence',
    kpiIds: [],
    charts: [],
    filters: DATE_ONLY,
    special: true,
    tableColumns: [],
  },

  dataQuality: {
    slug: 'dataQuality',
    path: '/data-quality',
    title: 'Data Quality',
    description: 'Validation rules, failures, severity and dataset-level quality scoring.',
    navGroup: 'Data & Intelligence',
    kpiIds: [],
    charts: [],
    filters: DATE_ONLY,
    special: true,
    tableColumns: [],
  },

  pipeline: {
    slug: 'pipeline',
    path: '/pipeline',
    title: 'Data Pipeline',
    description: 'Pipeline run history, manifests and end-to-end data lineage.',
    navGroup: 'Data & Intelligence',
    kpiIds: [],
    charts: [],
    filters: DATE_ONLY,
    special: true,
    tableColumns: [],
  },

  kpiGlossary: {
    slug: 'kpiGlossary',
    path: '/kpi-glossary',
    title: 'KPI Glossary',
    description: 'Definitions, formulas, grains, exclusions and caveats for every KPI.',
    navGroup: 'Data & Intelligence',
    kpiIds: [],
    charts: [],
    filters: [],
    special: true,
    tableColumns: [],
  },

  methodology: {
    slug: 'methodology',
    path: '/methodology',
    title: 'Methodology',
    description: 'Synthetic data methodology, analytical model, limitations and disclaimer.',
    navGroup: 'Data & Intelligence',
    kpiIds: [],
    charts: [],
    filters: [],
    special: true,
    tableColumns: [],
  },
};

/** Where a KPI card should navigate when clicked (filters are preserved by the card). */
const KPI_ROUTE_RULES: Array<[RegExp, string]> = [
  [/no_show|appointment|access|wait|reschedule|same_day/i, '/appointments'],
  [/denial|claim|payer|appeal/i, '/claims'],
  [/occupancy|los|bed|admission|discharge|readmission|boarding/i, '/inpatient'],
  [/satisfaction|experience|feedback|nps|complaint/i, '/experience'],
  [/incident|fall|infection|medication_incident|quality|safety/i, '/quality'],
  [/lab|tat|test|sla/i, '/diagnostics'],
  [/prescription|dispens|medication|pharmacy/i, '/pharmacy'],
  [/stock|inventory|expir|supplier|procurement/i, '/inventory'],
  [/overtime|workforce|absence|coverage|staff/i, '/workforce'],
  [/revenue|collection|invoice|billing|receivable|refund|writeoff/i, '/finance'],
  [/emergency|triage|patient_flow/i, '/emergency'],
  [/procedure|or_utilization|surgery/i, '/procedures'],
];

export function kpiRoute(id: string, fallback: string): string {
  const match = KPI_ROUTE_RULES.find(([pattern]) => pattern.test(id));
  return match ? match[1] : fallback;
}

/** Find a config for a pathname, including the dynamic hospital profile route. */
export function getPageConfigByPath(pathname: string): PageConfig | undefined {
  const direct = Object.values(pages).find((page) => page.path === pathname);
  if (direct) return direct;
  if (/^\/hospitals\/[^/]+$/.test(pathname)) return pages.hospitalsProfile;
  return undefined;
}

export function buildHospitalProfileConfig(id: string): PageConfig {
  const base = pages.hospitalsProfile;
  const replace = (endpoint: string) => endpoint.replace('{id}', id);
  return {
    ...base,
    title: `Hospital Profile · ${id}`,
    kpiEndpoint: base.kpiEndpoint ? replace(base.kpiEndpoint) : undefined,
    profileEndpoint: base.profileEndpoint ? replace(base.profileEndpoint) : undefined,
    tableEndpoint: base.tableEndpoint ? replace(base.tableEndpoint) : undefined,
    charts: base.charts.map((item) => ({ ...item, endpoint: replace(item.endpoint) })),
  };
}
