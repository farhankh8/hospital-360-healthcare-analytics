'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import { Check, ChevronDown, Download, GitCompareArrows, RotateCcw, SlidersHorizontal, X } from 'lucide-react';
import { useFilters } from '@/lib/filters';
import { usePageFilters } from '@/lib/page-filters';
import { getPageConfigByPath } from '@/lib/page-configs';
import type { FilterKey } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Badge, DateRangePicker, IconButton, Select } from './ui';

const ENCOUNTER_TYPES = [
  { value: 'Outpatient', label: 'Outpatient' },
  { value: 'Inpatient', label: 'Inpatient' },
  { value: 'Emergency', label: 'Emergency' },
];
const PATIENT_TYPES = [
  { value: 'New', label: 'New' },
  { value: 'Returning', label: 'Returning' },
];
const STATIC_PAGE_OPTIONS: Record<string, Array<{ value: string; label: string }>> = {
  elective_emergency: [
    { value: 'Elective', label: 'Elective' },
    { value: 'Emergency', label: 'Emergency' },
  ],
  rating: [
    { value: '1', label: '1 star' }, { value: '2', label: '2 stars' },
    { value: '3', label: '3 stars' }, { value: '4', label: '4 stars' },
    { value: '5', label: '5 stars' },
  ],
  run_status: [
    { value: 'success', label: 'Success' }, { value: 'failed', label: 'Failed' },
  ],
};

function HospitalMultiSelect() {
  const { hospitals, filters, setHospitals, optionsLoading } = useFilters();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selected = filters.hospital_ids;
  const label = selected.length === 0 ? 'All hospitals' : selected.length === 1 ? hospitals.find((h) => h.value === selected[0])?.label || selected[0] : `${selected.length} hospitals`;

  const toggle = (value: string) => {
    setHospitals(selected.includes(value) ? selected.filter((id) => id !== value) : [...selected, value]);
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex h-9 min-w-[150px] items-center justify-between gap-2 rounded-md border border-line bg-white px-2.5 text-xs text-ink transition hover:border-teal"
        aria-label={`Hospital filter: ${label}`}
        data-testid="filter-hospital"
        aria-expanded={open}
      >
        <span className="truncate">{label}</span>
        <ChevronDown className="h-3.5 w-3.5 shrink-0 text-slate-600" />
      </button>
      {open && (
        <div role="listbox" aria-label="Hospitals" className="absolute left-0 top-10 z-40 max-h-64 w-64 overflow-auto rounded-lg border border-line bg-white p-2 shadow-lg">
          {optionsLoading && <p className="px-2 py-3 text-xs text-slate-600">Loading hospitals…</p>}
          {!optionsLoading && hospitals.length === 0 && <p className="px-2 py-3 text-xs text-slate-600">No hospitals returned by the API.</p>}
          {hospitals.map((hospital) => (
            <button
              key={hospital.value}
              type="button"
              role="option"
              aria-selected={selected.includes(hospital.value)}
              onClick={() => toggle(hospital.value)}
              className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs text-ink hover:bg-canvas"
            >
              <span className={cn('flex h-4 w-4 items-center justify-center rounded border', selected.includes(hospital.value) ? 'border-teal bg-teal text-white' : 'border-slate-300')}>
                {selected.includes(hospital.value) && <Check className="h-3 w-3" />}
              </span>
              <span className="truncate">{hospital.label}</span>
            </button>
          ))}
          {selected.length > 0 && (
            <button type="button" onClick={() => setHospitals([])} className="mt-1 w-full border-t border-line px-2 pt-2 text-left text-xs font-medium text-teal">
              Clear selection
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export function FilterBar({ inDrawer = false }: { inDrawer?: boolean }) {
  const pathname = usePathname();
  const { filters, setFilter, reset, compare, toggleCompare, departments, specialties, setDrawerOpen } = useFilters();
  const { params: pageParams, setPageParam, options: pageOptions, optionsLoading: pageOptionsLoading } = usePageFilters();
  const config = getPageConfigByPath(pathname);
  const enabled = new Set(config?.filters ?? []);

  const show = (key: FilterKey) => enabled.size === 0 || enabled.has(key);
  const exportData = () => window.dispatchEvent(new CustomEvent('hospital360:export'));

  return (
    <div className={cn('flex flex-wrap items-end gap-3', inDrawer && 'flex-col items-stretch')}>
      {show('date_from') && (
        <div className="min-w-[240px] flex-1">
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-600">Date range</label>
          <DateRangePicker
            from={filters.date_from}
            to={filters.date_to}
            onFromChange={(value) => setFilter('date_from', value)}
            onToChange={(value) => setFilter('date_to', value)}
          />
        </div>
      )}
      {show('hospital_ids') && (
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-600">Hospital</label>
          <HospitalMultiSelect />
        </div>
      )}
      {show('department_id') && (
        <div className="w-44">
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-600">Department</label>
          <Select
            value={filters.department_id}
            onChange={(event) => setFilter('department_id', event.target.value)}
            options={departments}
            placeholder="All departments"
          />
        </div>
      )}
      {show('specialty_id') && (
        <div className="w-40">
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-600">Specialty</label>
          <Select
            value={filters.specialty_id}
            onChange={(event) => setFilter('specialty_id', event.target.value)}
            options={specialties}
            placeholder="All specialties"
            disabled={!specialties.length}
          />
        </div>
      )}
      {show('payer_id') && (
        <div className="w-36">
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-600">Payer ID</label>
          <input
            value={filters.payer_id}
            onChange={(event) => setFilter('payer_id', event.target.value.trim())}
            placeholder="e.g. PAY01"
            className="h-9 w-full rounded-md border border-line bg-white px-2.5 text-xs outline-none focus:border-teal focus:ring-2 focus:ring-teal/15"
          />
        </div>
      )}
      {show('encounter_type') && (
        <div className="w-36">
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-600">Encounter</label>
          <Select value={filters.encounter_type} onChange={(event) => setFilter('encounter_type', event.target.value)} options={ENCOUNTER_TYPES} placeholder="All types" />
        </div>
      )}
      {show('patient_type') && (
        <div className="w-32">
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-600">Patient</label>
          <Select value={filters.patient_type} onChange={(event) => setFilter('patient_type', event.target.value)} options={PATIENT_TYPES} placeholder="All patients" />
        </div>
      )}

      <div className="flex items-center gap-2 pb-0.5">
        <button
          type="button"
          onClick={reset}
          className="inline-flex h-9 items-center gap-1.5 rounded-md border border-line bg-white px-2.5 text-xs font-medium text-slate-600 transition hover:border-teal hover:text-teal"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Reset
        </button>
        <button
          type="button"
          onClick={exportData}
          className="inline-flex h-9 items-center gap-1.5 rounded-md bg-navy px-2.5 text-xs font-medium text-white transition hover:bg-navy-light"
        >
          <Download className="h-3.5 w-3.5" />
          Export
        </button>
        <button
          type="button"
          onClick={toggleCompare}
          className={cn(
            'inline-flex h-9 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium transition',
            compare ? 'border-teal bg-teal-light text-teal-dark' : 'border-line bg-white text-slate-600 hover:border-teal',
          )}
        >
          <GitCompareArrows className="h-3.5 w-3.5" />
          Compare
        </button>
        {inDrawer && (
          <IconButton onClick={() => setDrawerOpen(false)} aria-label="Close filters">
            <X className="h-4 w-4" />
          </IconButton>
        )}
      </div>
      {compare && !inDrawer && <Badge tone="info">Comparing with previous period</Badge>}
      {!inDrawer && (
        <button type="button" onClick={() => setDrawerOpen(true)} className="ml-auto flex items-center gap-1.5 text-xs text-slate-600 lg:hidden">
          <SlidersHorizontal className="h-4 w-4" />
          Filters
        </button>
      )}
    </div>
  );
}
