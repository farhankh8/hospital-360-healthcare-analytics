// Shared TypeScript contracts for the HOSPITAL 360 frontend.
// Values are never fabricated here: these types only describe API responses.

export interface ResponseMetadata {
  date_from?: string;
  date_to?: string;
  hospital_ids?: string[];
  generated_at?: string;
  filters_applied?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface Pagination {
  page: number;
  page_size: number;
  total_records: number;
  total_pages: number;
}

export interface ApiEnvelope<T> {
  data: T;
  metadata?: ResponseMetadata;
  pagination?: Pagination;
  message?: string;
}

export interface KpiValue {
  value: number | string | null;
  previous?: number | string | null;
  change_pct?: number | null;
  sparkline?: number[] | null;
  unit?: string;
  label?: string;
  definition?: string;
  target?: number | null;
  lower_is_better?: boolean;
  date_filter_available?: boolean;
  date_filter_note?: string;
  [key: string]: unknown;
}

export type KpiMap = Record<string, KpiValue>;

export interface FilterState {
  date_from: string;
  date_to: string;
  hospital_ids: string[];
  department_id: string;
  specialty_id: string;
  payer_id: string;
  encounter_type: string;
  patient_type: string;
}

export type FilterKey = keyof FilterState;

export const NO_FILTERS: FilterState = {
  date_from: '',
  date_to: '',
  hospital_ids: [],
  department_id: '',
  specialty_id: '',
  payer_id: '',
  encounter_type: '',
  patient_type: '',
};

export const DEFAULT_FILTERS: FilterState = {
  date_from: '2025-01-01',
  date_to: '2026-12-31',
  hospital_ids: [],
  department_id: '',
  specialty_id: '',
  payer_id: '',
  encounter_type: '',
  patient_type: '',
};

export type NavGroup = 'Overview' | 'Operations' | 'Business' | 'Performance' | 'Data & Intelligence';

export const NAV_GROUPS: NavGroup[] = [
  'Overview',
  'Operations',
  'Business',
  'Performance',
  'Data & Intelligence',
];

export type ChartType =
  | 'line'
  | 'area'
  | 'bar'
  | 'stacked-bar'
  | 'horizontal-bar'
  | 'pie'
  | 'donut'
  | 'radar'
  | 'heatmap';

export interface ChartConfig {
  title: string;
  endpoint: string;
  type: ChartType;
  /** Key holding the series array when the endpoint returns an object instead of an array. */
  dataKey: string;
  description?: string;
  xKey?: string;
  yKey?: string;
  valueKey?: string;
  seriesKeys?: string[];
  height?: number;
  span?: 1 | 2;
  unfilteredBenchmark?: boolean;
  drilldownEndpoint?: string;
}

export type ColumnType = 'text' | 'number' | 'currency' | 'percent' | 'date' | 'badge';

export interface TableColumn {
  key: string;
  title: string;
  type?: ColumnType;
  sortable?: boolean;
  hidden?: boolean;
}

export type TableRow = Record<string, unknown>;

export interface PageFilterDef {
  /** API query parameter name, also used as the shareable URL key. */
  name: string;
  label: string;
  /** Key in /filters/options when the options are data-driven. */
  optionsKey?: string;
  kind?: 'select' | 'text';
  placeholder?: string;
}

export interface PageTab {
  id: string;
  label: string;
  /** Chart titles to show in this tab. If omitted, all charts are shown. */
  chartTitles?: string[];
  showTable?: boolean;
  showKpis?: boolean;
}

export interface PageConfig {
  slug: string;
  path: string;
  title: string;
  description: string;
  navGroup: NavGroup;
  kpiEndpoint?: string;
  kpiIds: string[];
  charts: ChartConfig[];
  tableEndpoint?: string;
  tableColumns: TableColumn[];
  filters: FilterKey[];
  pageFilters?: PageFilterDef[];
  profileEndpoint?: string;
  special?: boolean;
  tabs?: PageTab[];
}

export interface SelectOption {
  value: string;
  label: string;
  specialtyId?: string;
  specialtyName?: string;
}
