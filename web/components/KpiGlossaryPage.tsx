'use client';

import { useMemo, useState } from 'react';
import { BookOpen, LayoutGrid, List, Search } from 'lucide-react';
import { useApiQuery } from '@/lib/api';
import { NO_FILTERS, type TableRow } from '@/lib/types';
import { displayValue } from '@/lib/utils';
import { useDrilldown } from './DrilldownDrawer';
import { Badge, Card, CardHeader, EmptyState, ErrorState, PageHeading, Skeleton } from './ui';

function glossaryRows(data: unknown): TableRow[] {
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    const array = Object.values(data as Record<string, unknown>).find(Array.isArray);
    if (array) data = array;
  }
  if (Array.isArray(data)) return data as TableRow[];
  if (data && typeof data === 'object') {
    return Object.entries(data as Record<string, unknown>).map(([id, value]) => {
      if (value && typeof value === 'object' && !Array.isArray(value)) return { kpi_id: id, ...(value as TableRow) };
      return { kpi_id: id, definition: typeof value === 'string' ? value : JSON.stringify(value) };
    });
  }
  return [];
}

const DETAIL_FIELDS: Array<[string, string]> = [
  ['name', 'KPI name'],
  ['business_definition', 'Business definition'],
  ['formula', 'Formula'],
  ['numerator', 'Numerator'],
  ['denominator', 'Denominator'],
  ['unit', 'Unit'],
  ['grain', 'Data grain'],
  ['date_field', 'Date logic'],
  ['exclusions', 'Exclusions'],
  ['source_tables', 'Source table'],
  ['dimensions', 'Supported dimensions'],
  ['caveat', 'Caveats'],
  ['validation_test', 'Validation test'],
];

const SNAPSHOT_KPIS = new Set(['hospitals_selected', 'total_beds', 'active_employees']);

export function KpiGlossaryPage() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [view, setView] = useState<'table' | 'cards'>('table');
  const { openDrilldown } = useDrilldown();
  const query = useApiQuery<unknown>('glossary-page', '/kpis/glossary', NO_FILTERS);
  const rows = useMemo(() => glossaryRows(query.data?.data), [query.data]);

  const categories = useMemo(() => ['all', ...Array.from(new Set(rows.map((r) => String(r.category || 'Other')))).sort()], [rows]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return rows.filter((row) => {
      if (category !== 'all' && String(row.category || 'Other') !== category) return false;
      if (!term) return true;
      return JSON.stringify(row).toLowerCase().includes(term);
    });
  }, [rows, search, category]);

  const openDetail = (row: TableRow) => {
    const detail: Record<string, unknown> = {};
    DETAIL_FIELDS.forEach(([key, label]) => {
      const v = row[key];
      if (v !== undefined && v !== null && v !== '') detail[label] = v;
    });
    // include id/category for context
    detail['KPI ID'] = row.id ?? row.kpi_id;
    detail['Category'] = row.category;
    openDrilldown(detail as TableRow, String(row.name || row.kpi_name || row.id || 'KPI detail'));
  };

  return (
    <div className="space-y-6" data-testid="kpi-glossary-page">
      <PageHeading
        title="KPI Glossary"
        description="Every metric displayed in HOSPITAL 360 is defined by the API, not by the frontend."
        badge={<Badge tone="info">Source of truth</Badge>}
      />

      <Card className="p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-1 flex-col gap-3 sm:flex-row">
            <div className="relative max-w-sm flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search KPI definitions..."
                data-testid="glossary-search"
                className="h-9 w-full rounded-md border border-line pl-9 pr-3 text-xs outline-none focus:border-teal focus:ring-2 focus:ring-teal/15"
              />
            </div>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              data-testid="glossary-category"
              className="h-9 rounded-md border border-line px-3 text-xs text-slate-700 outline-none focus:border-teal"
            >
              {categories.map((c) => <option key={c} value={c}>{c === 'all' ? 'All categories' : c}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <a href="/methodology" className="text-xs font-medium text-teal hover:underline">Methodology</a>
            <div className="flex rounded-md border border-line">
              <button type="button" onClick={() => setView('table')} className={`px-2 py-1.5 ${view === 'table' ? 'bg-teal-light/40 text-teal-dark' : 'text-slate-500'}`} aria-label="Table view"><List className="h-4 w-4" /></button>
              <button type="button" onClick={() => setView('cards')} className={`px-2 py-1.5 ${view === 'cards' ? 'bg-teal-light/40 text-teal-dark' : 'text-slate-500'}`} aria-label="Card view"><LayoutGrid className="h-4 w-4" /></button>
            </div>
          </div>
        </div>
        <p className="mt-3 text-[11px] text-slate-400">{filtered.length} of {rows.length} KPIs. Click a row/card for full definition.</p>
      </Card>

      {query.isLoading && <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_item, index) => <Skeleton key={index} className="h-48 w-full" />)}</div>}
      {query.isError && <Card><ErrorState message={query.error?.message || 'Glossary unavailable'} onRetry={() => query.refetch()} /></Card>}
      {!query.isLoading && !query.isError && filtered.length === 0 && <Card><EmptyState message="No KPI definitions found" hint="Try adjusting search or category filter." /></Card>}

      {!query.isLoading && !query.isError && filtered.length > 0 && view === 'table' && (
        <Card>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs" data-testid="glossary-table">
              <thead className="border-b border-line bg-surface-alt text-left text-slate-500">
                <tr>
                  <th className="px-4 py-3">KPI</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Definition</th>
                  <th className="px-4 py-3">Unit</th>
                  <th className="px-4 py-3">Date logic</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row, index) => {
                  const kpiId = String(row.id ?? row.kpi_id ?? '');
                  const title = String(row.name ?? row.kpi_name ?? kpiId);
                  const dateUnavailable = row.date_filter_available === false || SNAPSHOT_KPIS.has(kpiId);
                  return (
                    <tr key={`${kpiId}-${index}`} className="cursor-pointer border-b border-line/60 hover:bg-teal-light/10" onClick={() => openDetail(row)} data-testid="glossary-row">
                      <td className="px-4 py-3 font-medium text-navy">{title}<div className="text-[10px] text-slate-400">{kpiId}</div></td>
                      <td className="px-4 py-3"><Badge tone="neutral">{String(row.category || 'Other')}</Badge></td>
                      <td className="px-4 py-3 text-slate-600">{String(row.business_definition || row.definition || '').slice(0, 120)}</td>
                      <td className="px-4 py-3">{displayValue(row.unit)}</td>
                      <td className="px-4 py-3">{dateUnavailable ? <Badge tone="warning">No date filter</Badge> : <span className="text-slate-500">{String(row.date_field || '').slice(0, 40)}</span>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {!query.isLoading && !query.isError && filtered.length > 0 && view === 'cards' && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((row, index) => {
            const kpiId = String(row.id ?? row.kpi_id ?? '');
            const title = String(row.name ?? row.kpi_name ?? kpiId ?? `KPI ${index + 1}`);
            const dateUnavailable = row.date_filter_available === false || SNAPSHOT_KPIS.has(kpiId);
            return (
              <button key={`${kpiId}-${index}`} type="button" onClick={() => openDetail(row)} className="text-left" data-testid="glossary-card">
                <Card className="flex h-full flex-col hover:border-teal/40">
                  <CardHeader title={title} subtitle={kpiId} action={dateUnavailable ? <Badge tone="warning">No date filter</Badge> : <BookOpen className="h-4 w-4 text-teal" />} />
                  <div className="flex-1 space-y-2 p-4">
                    <p className="text-xs leading-relaxed text-ink">{String(row.business_definition || row.definition || '')}</p>
                    <div className="flex flex-wrap gap-2">
                      <Badge tone="neutral">{String(row.category || 'Other')}</Badge>
                      <Badge tone="info">{displayValue(row.unit)}</Badge>
                    </div>
                  </div>
                </Card>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
