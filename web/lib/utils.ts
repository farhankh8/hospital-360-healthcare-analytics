import clsx, { type ClassValue } from 'clsx';
import type { FilterState } from './types';

export function cn(...classes: ClassValue[]): string {
  return clsx(classes);
}

/** Build a route that preserves the currently active, shareable filters. */
export function routeWithFilters(path: string, filters: FilterState, extra?: Record<string, string>): string {
  const params = new URLSearchParams();
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);
  filters.hospital_ids.forEach((id) => id && params.append('hospital_id', id));
  if (filters.department_id) params.set('department_id', filters.department_id);
  if (filters.specialty_id) params.set('specialty_id', filters.specialty_id);
  if (filters.payer_id) params.set('payer_id', filters.payer_id);
  if (filters.encounter_type) params.set('encounter_type', filters.encounter_type);
  if (filters.patient_type) params.set('patient_type', filters.patient_type);
  extra &&
    Object.entries(extra).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export function titleize(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
    .trim();
}

export function toNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

/** Render an API column value without ever inventing a number. */
export function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function downloadCsv(filename: string, rows: Array<Record<string, unknown>>): void {
  if (!rows.length) return;
  const headers = Array.from(
    rows.reduce((set, row) => {
      Object.keys(row).forEach((key) => set.add(key));
      return set;
    }, new Set<string>()),
  );
  const escape = (value: unknown): string => {
    const text = value === null || value === undefined ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value);
    return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const csv = [headers.map(escape).join(','), ...rows.map((row) => headers.map((key) => escape(row[key])).join(','))].join('\r\n');
  const blob = new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
