import type { KpiValue } from './types';
import { titleize, toNumber } from './utils';

/**
 * Metrics where a lower value is favourable. Colour polarity is inverted for
 * these so that green always means "good" and red always means "bad".
 */
export const LOWER_IS_BETTER = new Set([
  'no_show_rate',
  'claim_denial_rate',
  'denial_rate',
  'average_los',
  'avg_los_days',
  'avg_wait_minutes',
  'average_wait_minutes',
  'average_waiting_time',
  'average_wait_for_appointment',
  'average_checkin_waiting_time',
  'avg_triage_minutes',
  'average_triage_time',
  'avg_treatment_minutes',
  'average_treatment_time',
  'avg_tat_minutes',
  'average_turnaround_time',
  'median_tat_minutes',
  'median_turnaround_time',
  'procedure_turnaround_time',
  'avg_processing_days',
  'average_processing_time',
  'avg_investigation_days',
  'avg_investigation_time',
  'average_investigation_time',
  'complaint_resolution_days',
  'complaint_resolution_time',
  'average_discharge_time',
  'average_boarding_time',
  'absence_rate',
  'readmission_rate',
  'incident_rate',
  'cancellation_rate',
  'reschedule_rate',
  'rescheduling_rate',
  'expired_value',
  'expired_inventory_value',
  'expired_medication_value',
  'waste',
  'inventory_waste',
  'pharmacy_waste',
  'stockouts',
  'stockout_items',
  'low_stock',
  'low_stock_items',
  'blocked_beds',
  'outstanding_balance',
  'outstanding_receivables',
  'outstanding_claim_value',
  'refunds',
  'refund_amount',
  'writeoffs',
  'writeoff_amount',
  'duplicate_records',
  'invalid_records',
  'missing_values',
  'quarantined_records',
  'failed_checks',
  'invalid_dates',
  'referential_integrity_violations',
]);

export function isLowerBetter(id: string, kpi?: KpiValue): boolean {
  if (typeof kpi?.lower_is_better === 'boolean') return kpi.lower_is_better;
  const normalised = id.toLowerCase();
  for (const key of LOWER_IS_BETTER) {
    if (normalised === key || normalised.includes(key)) return true;
  }
  return false;
}

export function kpiLabel(id: string, kpi?: KpiValue): string {
  return kpi?.label || titleize(id);
}

export function formatValue(value: unknown, unit?: string): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'string') return value;
  const numeric = toNumber(value);
  if (numeric === null) return String(value);
  const kind = (unit || '').toLowerCase();
  if (kind === 'currency' || kind === 'money' || kind === '$') return formatCurrency(numeric);
  if (kind === 'percent' || kind === '%' || kind === 'rate') return `${numeric.toFixed(1)}%`;
  if (kind === 'count' || kind === 'integer') return Math.round(numeric).toLocaleString('en-US');
  if (kind === 'minutes') return `${numeric.toFixed(1)} min`;
  if (kind === 'hours') return `${numeric.toFixed(1)} h`;
  if (kind === 'seconds') return `${numeric.toFixed(1)} s`;
  if (kind === 'days') return `${numeric.toFixed(1)} d`;
  if (kind === 'ratio' || kind === 'score') return numeric.toFixed(2);
  if (Number.isInteger(numeric)) return numeric.toLocaleString('en-US');
  if (Math.abs(numeric) >= 1000) return compactNumber(numeric);
  return numeric.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

export function formatCurrency(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

export function compactNumber(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(0);
}

export function formatChange(change?: number | null): string {
  const numeric = toNumber(change);
  if (numeric === null) return '—';
  const sign = numeric > 0 ? '+' : numeric < 0 ? '−' : '';
  return `${sign}${Math.abs(numeric).toFixed(1)}%`;
}

export type Tone = 'positive' | 'negative' | 'neutral';

export function changeTone(change?: number | null, lowerIsBetter = false): Tone {
  const numeric = toNumber(change);
  if (numeric === null || Math.abs(numeric) < 0.05) return 'neutral';
  const favourable = lowerIsBetter ? numeric < 0 : numeric > 0;
  return favourable ? 'positive' : 'negative';
}

const CURRENCY_HINTS = [
  'revenue',
  'collection',
  'collected',
  'amount',
  'balance',
  'cost',
  'value',
  'billed',
  'claim',
  'refund',
  'writeoff',
  'invoice',
  'paid',
  'procurement',
];
const SCORE_HINTS = ['avg_rating', 'average_satisfaction', 'satisfaction_score', 'nps'];
const PERCENT_HINTS = ['rate', 'pct', 'percent', 'coverage', 'satisfaction_pct', 'satisfaction_percentage', 'sla', 'completion', 'on_time'];
const DATE_HINTS = ['date', '_at', 'month', 'time', 'start', 'end'];

export function inferColumnType(key: string, sample?: unknown): 'number' | 'currency' | 'percent' | 'date' | 'text' {
  const lowered = key.toLowerCase();
  if (DATE_HINTS.some((hint) => lowered.includes(hint))) return 'date';
  if (SCORE_HINTS.some((hint) => lowered.includes(hint))) return 'number';
  if (PERCENT_HINTS.some((hint) => lowered.includes(hint))) return 'percent';
  if (CURRENCY_HINTS.some((hint) => lowered.includes(hint))) return 'currency';
  if (typeof sample === 'number') return 'number';
  if (typeof sample === 'string' && sample.trim() !== '' && !Number.isNaN(Number(sample))) return 'number';
  return 'text';
}

export function formatCell(value: unknown, type?: string): string {
  if (value === null || value === undefined || value === '') return '—';
  if (type === 'currency') {
    const numeric = toNumber(value);
    return numeric === null ? String(value) : formatCurrency(numeric);
  }
  if (type === 'percent') {
    const numeric = toNumber(value);
    return numeric === null ? String(value) : `${numeric.toFixed(1)}%`;
  }
  if (type === 'number') {
    const numeric = toNumber(value);
    return numeric === null ? String(value) : numeric.toLocaleString('en-US', { maximumFractionDigits: 2 });
  }
  if (type === 'date' && typeof value === 'string') return value.slice(0, 10);
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function statusTone(value: unknown): 'positive' | 'negative' | 'warning' | 'neutral' {
  const text = String(value ?? '').toLowerCase();
  if (/complete|approved|paid|resolved|success|active|available|completed/.test(text)) return 'positive';
  if (/cancel|denied|reject|fail|critical|error|no-show|noshow|expired/.test(text)) return 'negative';
  if (/pending|progress|waiting|low|review|open/.test(text)) return 'warning';
  return 'neutral';
}
