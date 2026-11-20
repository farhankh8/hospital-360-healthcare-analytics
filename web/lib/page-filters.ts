'use client';

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { usePathname, useRouter, useSearchParams, type ReadonlyURLSearchParams } from 'next/navigation';
import { useApiQuery } from './api';
import { NO_FILTERS, type SelectOption, type TableRow } from './types';

/** Page-scoped filters that are sent verbatim to the API and stored in the URL. */
export const PAGE_FILTER_PARAMS = [
  'doctor_id', 'appointment_type', 'status', 'age_group', 'booking_channel',
  'triage_category', 'disposition', 'arrival_mode', 'ward', 'bed_type',
  'admission_type', 'discharge_type', 'or_room', 'procedure_code',
  'elective_emergency', 'test_code', 'priority', 'result_status',
  'medication_code', 'service_category', 'invoice_status', 'payment_status',
  'claim_type', 'denial_reason', 'role', 'shift_type', 'employment_type',
  'category', 'item_id', 'supplier_id', 'movement_type', 'feedback_type',
  'rating', 'sentiment', 'severity', 'resolution_status',
  'dataset', 'rule_category', 'layer', 'stage', 'run_status',
] as const;

export type PageFilterParam = (typeof PAGE_FILTER_PARAMS)[number];

export interface PageFilterContextValue {
  /** Global-filter-compatible params for useApiQuery's `params` argument. */
  params: Record<string, string>;
  setPageParam: (name: string, value: string) => void;
  options: Record<string, SelectOption[]>;
  optionsLoading: boolean;
}

export function usePageFilters(): PageFilterContextValue {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const paramsRef = useRef<URLSearchParams | ReadonlyURLSearchParams>(searchParams);

  useEffect(() => {
    paramsRef.current = searchParams;
  }, [searchParams]);

  const params = useMemo<Record<string, string>>(() => {
    const result: Record<string, string> = {};
    PAGE_FILTER_PARAMS.forEach((name) => {
      const value = searchParams.get(name);
      if (value) result[name] = value;
    });
    return result;
  }, [searchParams]);

  const setPageParam = useCallback((name: string, value: string) => {
    const next = new URLSearchParams(paramsRef.current.toString());
    if (value) next.set(name, value);
    else next.delete(name);
    paramsRef.current = next;
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }, [pathname, router]);

  const optionsQuery = useApiQuery<unknown>('filter-page-options', '/filters/options', NO_FILTERS);

  const options = useMemo<Record<string, SelectOption[]>>(() => {
    const data = optionsQuery.data?.data;
    if (!data || typeof data !== 'object' || Array.isArray(data)) return {};
    const result: Record<string, SelectOption[]> = {};
    Object.entries(data as Record<string, unknown>).forEach(([key, rows]) => {
      if (!Array.isArray(rows)) return;
      result[key] = (rows as TableRow[])
        .map((row) => ({
          value: String(row.value ?? ''),
          label: String(row.label ?? row.value ?? ''),
          specialtyId: row.specialtyId ? String(row.specialtyId) : undefined,
        }))
        .filter((option) => option.value);
    });
    return result;
  }, [optionsQuery.data]);

  return { params, setPageParam, options, optionsLoading: optionsQuery.isLoading };
}
