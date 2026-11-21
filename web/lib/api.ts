'use client';

import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { downloadCsvBlob } from './utils';
import type { ApiEnvelope, FilterState, KpiMap, TableRow } from './types';

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '');

export type QueryParamValue = string | number | boolean | null | undefined | string[];

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function readApiError(response: Response): Promise<ApiError> {
  let message = `Request failed (${response.status})`;
  let code: string | undefined;
  let details: unknown;
  try {
    const body = (await response.json()) as {
      error?: { code?: string; message?: string; details?: unknown };
      detail?: unknown;
      message?: string;
    };
    if (typeof body.error?.message === 'string') message = body.error.message;
    else if (typeof body.detail === 'string') message = body.detail;
    else if (typeof body.message === 'string') message = body.message;
    else if (body.detail) message = JSON.stringify(body.detail);
    code = body.error?.code;
    details = body.error?.details;
  } catch {
    message = response.statusText || message;
  }
  return new ApiError(message, response.status, code, details);
}

/** Turn global filters into the exact query parameters defined by the API contract. */
export function buildQueryString(filters: FilterState, params?: Record<string, QueryParamValue>): string {
  const search = new URLSearchParams();
  if (filters.date_from) search.set('date_from', filters.date_from);
  if (filters.date_to) search.set('date_to', filters.date_to);
  filters.hospital_ids.forEach((id) => {
    if (id) search.append('hospital_id', id);
  });
  if (filters.department_id) search.set('department_id', filters.department_id);
  if (filters.specialty_id) search.set('specialty_id', filters.specialty_id);
  if (filters.payer_id) search.set('payer_id', filters.payer_id);
  if (filters.encounter_type) search.set('encounter_type', filters.encounter_type);
  if (filters.patient_type) search.set('patient_type', filters.patient_type);

  Object.entries(params || {}).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item) => item !== '' && item !== undefined && search.append(key, String(item)));
    } else if (value !== null && value !== undefined && value !== '') {
      search.set(key, String(value));
    }
  });
  return search.toString();
}

export interface ApiGetOptions {
  params?: Record<string, QueryParamValue>;
  signal?: AbortSignal;
}

export async function apiGet<T>(path: string, filters: FilterState, options: ApiGetOptions = {}): Promise<ApiEnvelope<T>> {
  const query = buildQueryString(filters, options.params);
  const response = await fetch(`${API_BASE}${path}${query ? `?${query}` : ''}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: options.signal,
    cache: 'no-store',
  });

  if (!response.ok) {
    throw await readApiError(response);
  }

  return (await response.json()) as ApiEnvelope<T>;
}

/** Request a server-generated CSV export with the global cap enforced by the API. */
export async function apiExportCsv(
  path: string,
  filters: FilterState,
  params: Record<string, QueryParamValue> = {},
  filename = 'export',
): Promise<void> {
  const query = buildQueryString(filters, { ...params, path, filename });
  const response = await fetch(`${API_BASE}/exports/csv?${query}`, {
    method: 'GET',
    headers: { Accept: 'text/csv' },
    cache: 'no-store',
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  const disposition = response.headers.get('content-disposition') || '';
  const suggested = /filename="?([^";]+)"?/i.exec(disposition)?.[1];
  downloadCsvBlob(suggested || `${filename}.csv`, await response.blob());
}

/**
 * Single typed TanStack Query hook used by every data consumer.
 * The filter state is part of the query key and the abort signal is forwarded,
 * so stale requests are cancelled as soon as filters change.
 */
export function useApiQuery<T>(
  queryId: string,
  path: string | undefined,
  filters: FilterState,
  params?: Record<string, QueryParamValue>,
  enabled = true,
): UseQueryResult<ApiEnvelope<T>, ApiError> {
  return useQuery<ApiEnvelope<T>, ApiError>({
    queryKey: [queryId, path, filters, params],
    queryFn: ({ signal }) => apiGet<T>(path as string, filters, { signal, params }),
    enabled: Boolean(path) && enabled,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    retry: 1,
  });
}

export function useKpis(
  path: string | undefined,
  filters: FilterState,
  params?: Record<string, QueryParamValue>,
): UseQueryResult<ApiEnvelope<KpiMap>, ApiError> {
  return useApiQuery<KpiMap>('kpis', path, filters, params);
}

export function useChartData(
  path: string | undefined,
  filters: FilterState,
  params?: Record<string, QueryParamValue>,
): UseQueryResult<ApiEnvelope<unknown>, ApiError> {
  return useApiQuery<unknown>('chart', path, filters, params);
}

export function useTableData(
  path: string | undefined,
  filters: FilterState,
  params: Record<string, QueryParamValue>,
  enabled = true,
): UseQueryResult<ApiEnvelope<TableRow[]>, ApiError> {
  return useApiQuery<TableRow[]>('table', path, filters, params, enabled);
}

/** Replace {id} style placeholders in configured endpoints (e.g. hospital profile routes). */
export function resolveEndpoint(endpoint: string | undefined, values: Record<string, string>): string | undefined {
  if (!endpoint) return undefined;
  return endpoint.replace(/\{(\w+)\}/g, (_match, key: string) => encodeURIComponent(values[key] || ''));
}
