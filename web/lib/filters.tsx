'use client';

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useApiQuery } from './api';
import { DEFAULT_FILTERS, NO_FILTERS, type FilterKey, type FilterState, type SelectOption, type TableRow } from './types';

interface FilterContextValue {
  filters: FilterState;
  setFilter: (key: FilterKey, value: string | string[]) => void;
  setHospitals: (ids: string[]) => void;
  reset: () => void;
  compare: boolean;
  toggleCompare: () => void;
  hospitals: SelectOption[];
  departments: SelectOption[];
  specialties: SelectOption[];
  optionsLoading: boolean;
  drawerOpen: boolean;
  setDrawerOpen: (open: boolean) => void;
}

const FilterContext = createContext<FilterContextValue | null>(null);

function firstString(...values: unknown[]): string {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value;
    if (typeof value === 'number') return String(value);
  }
  return '';
}

function normaliseOptions(data: unknown, kind: 'hospital' | 'department' | 'payer'): SelectOption[] {
  let rows: TableRow[] = [];
  if (Array.isArray(data)) rows = data as TableRow[];
  else if (data && typeof data === 'object') {
    const object = data as Record<string, unknown>;
    const arrays = Object.values(object).filter(Array.isArray) as TableRow[][];
    rows = arrays[0] || [];
  }

  const seen = new Set<string>();
  return rows
    .map((row): SelectOption | null => {
      if (!row || typeof row !== 'object') return null;
      const value =
        kind === 'hospital'
          ? firstString(row.hospital_id, row.hospitalId, row.id, row.code, row.value)
          : kind === 'department'
            ? firstString(row.department_id, row.departmentId, row.id, row.code, row.value)
            : firstString(row.payer_id, row.payerId, row.id, row.code, row.value);
      const label =
        kind === 'hospital'
          ? firstString(row.hospital_name, row.hospitalName, row.name, row.label, row.value, value)
          : kind === 'department'
            ? firstString(row.department_name, row.departmentName, row.name, row.label, row.value, value)
            : firstString(row.payer_name, row.payerName, row.name, row.label, row.value, value);
      if (!value) return null;
      return {
        value,
        label: label || value,
        specialtyId: firstString(row.specialty_id, row.specialtyId),
        specialtyName: firstString(row.specialty_name, row.specialtyName),
      } satisfies SelectOption;
    })
    .filter((option): option is SelectOption => {
      if (!option || seen.has(option.value)) return false;
      seen.add(option.value);
      return true;
    });
}

export function FilterProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const filters = useMemo<FilterState>(
    () => ({
      date_from: searchParams.get('date_from') ?? DEFAULT_FILTERS.date_from,
      date_to: searchParams.get('date_to') ?? DEFAULT_FILTERS.date_to,
      hospital_ids: searchParams.getAll('hospital_id'),
      department_id: searchParams.get('department_id') ?? '',
      specialty_id: searchParams.get('specialty_id') ?? '',
      payer_id: searchParams.get('payer_id') ?? '',
      encounter_type: searchParams.get('encounter_type') ?? '',
      patient_type: searchParams.get('patient_type') ?? '',
    }),
    [searchParams],
  );

  const compare = searchParams.get('compare') === '1';

  const commit = useCallback(
    (mutate: (params: URLSearchParams) => void) => {
      const params = new URLSearchParams(searchParams.toString());
      mutate(params);
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const setFilter = useCallback(
    (key: FilterKey, value: string | string[]) => {
      commit((params) => {
        if (Array.isArray(value)) {
          params.delete(key);
          value.filter(Boolean).forEach((item) => params.append(key, item));
          if (key === 'hospital_ids') {
            params.delete('department_id');
            params.delete('specialty_id');
          }
        } else if (value) {
          params.set(key, value);
        } else {
          params.delete(key);
          if (key === 'department_id') params.delete('specialty_id');
        }
      });
    },
    [commit],
  );

  const setHospitals = useCallback((ids: string[]) => setFilter('hospital_ids', ids), [setFilter]);

  const reset = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    Object.keys(DEFAULT_FILTERS).forEach((key) => params.delete(key));
    params.delete('compare');
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }, [pathname, router, searchParams]);

  const toggleCompare = useCallback(() => {
    commit((params) => {
      if (params.get('compare') === '1') params.delete('compare');
      else params.set('compare', '1');
    });
  }, [commit]);

  const hospitalQuery = useApiQuery<unknown>('filter-hospitals', '/hospitals', NO_FILTERS, { page_size: 500 });
  const hospitalOptions = useMemo(() => normaliseOptions(hospitalQuery.data?.data, 'hospital'), [hospitalQuery.data]);

  const departmentEndpoint = filters.hospital_ids[0]
    ? `/hospitals/${encodeURIComponent(filters.hospital_ids[0])}/departments`
    : undefined;
  const departmentQuery = useApiQuery<unknown>(
    'filter-departments',
    departmentEndpoint,
    NO_FILTERS,
    { page_size: 500 },
    Boolean(departmentEndpoint),
  );
  const departmentOptions = useMemo(() => normaliseOptions(departmentQuery.data?.data, 'department'), [departmentQuery.data]);

  const specialtyOptions = useMemo(() => {
    const map = new Map<string, SelectOption>();
    departmentOptions.forEach((department) => {
      if (department.specialtyId) {
        map.set(department.specialtyId, {
          value: department.specialtyId,
          label: department.specialtyName || department.specialtyId,
        });
      }
    });
    return Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label));
  }, [departmentOptions]);

  const value = useMemo<FilterContextValue>(
    () => ({
      filters,
      setFilter,
      setHospitals,
      reset,
      compare,
      toggleCompare,
      hospitals: hospitalOptions,
      departments: departmentOptions,
      specialties: specialtyOptions,
      optionsLoading: hospitalQuery.isLoading || departmentQuery.isLoading,
      drawerOpen,
      setDrawerOpen,
    }),
    [
      filters,
      setFilter,
      setHospitals,
      reset,
      compare,
      toggleCompare,
      hospitalOptions,
      departmentOptions,
      specialtyOptions,
      hospitalQuery.isLoading,
      departmentQuery.isLoading,
      drawerOpen,
    ],
  );

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}

export function useFilters(): FilterContextValue {
  const context = useContext(FilterContext);
  if (!context) throw new Error('useFilters must be used inside FilterProvider');
  return context;
}
