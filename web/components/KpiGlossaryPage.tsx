'use client';

import { useMemo, useState } from 'react';
import { BookOpen, Search } from 'lucide-react';
import { useApiQuery } from '@/lib/api';
import { NO_FILTERS, type TableRow } from '@/lib/types';
import { displayValue } from '@/lib/utils';
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

const PREFERRED_ORDER = [
  'definition',
  'business_definition',
  'formula',
  'numerator',
  'denominator',
  'unit',
  'grain',
  'date_field',
  'exclusions',
  'source',
  'dimensions',
  'target',
  'caveat',
  'validation',
  'aliases',
  'expected_range',
  'null_handling',
];

// Phase 2 adds machine-readable contract fields to the glossary JSON. Keep
// those in search, but do not change the card design by printing raw metadata.
const HIDDEN_CONTRACT_FIELDS = new Set([
  'contract_version', 'display_name', 'formula_sql', 'date_column', 'source_columns',
  'aggregation_method', 'filter_behavior', 'units', 'decimal_precision', 'additivity',
  'business_interpretation', 'consumer_status', 'audit_findings', 'last_reviewed',
  'alias_of', 'same_definition_as', 'api_endpoints', 'frontend_consumers',
]);

const SNAPSHOT_KPIS = new Set(['hospitals_selected', 'total_beds', 'active_employees']);

export function KpiGlossaryPage() {
  const [search, setSearch] = useState('');
  const query = useApiQuery<unknown>('glossary-page', '/kpis/glossary', NO_FILTERS);
  const rows = useMemo(() => glossaryRows(query.data?.data), [query.data]);
  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return rows;
    return rows.filter((row) => JSON.stringify(row).toLowerCase().includes(term));
  }, [rows, search]);

  return (
    <div className="space-y-6">
      <PageHeading title="KPI Glossary" description="Every metric displayed in HOSPITAL 360 is defined by the API, not by the frontend." badge={<Badge tone="info">Source of truth</Badge>} />

      <Card className="p-5">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search KPI definitions…"
            className="h-9 w-full rounded-md border border-line pl-9 pr-3 text-xs outline-none focus:border-teal focus:ring-2 focus:ring-teal/15"
          />
        </div>
      </Card>

      {query.isLoading && <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_item, index) => <Skeleton key={index} className="h-48 w-full" />)}</div>}
      {query.isError && <Card><ErrorState message={query.error?.message || 'Glossary unavailable'} onRetry={() => query.refetch()} /></Card>}
      {!query.isLoading && !query.isError && filtered.length === 0 && <Card><EmptyState message="No KPI definitions found" hint="The glossary endpoint returned no matching definitions." /></Card>}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((row, index) => {
          const kpiId = displayValue(row.kpi_id ?? row.id ?? '');
          const title = displayValue(row.kpi_name ?? row.name ?? kpiId ?? `KPI ${index + 1}`);
          const dateUnavailable = row.date_filter_available === false || SNAPSHOT_KPIS.has(kpiId);
          const fields = PREFERRED_ORDER.filter((key) => row[key] !== undefined && row[key] !== null && row[key] !== '')
            .map((key) => [key, row[key]] as [string, unknown]);
          Object.entries(row).forEach(([key, value]) => {
            if (
              !PREFERRED_ORDER.includes(key)
              && !HIDDEN_CONTRACT_FIELDS.has(key)
              && !['kpi_name', 'name', 'kpi_id', 'id'].includes(key)
              && value !== null && value !== undefined && value !== ''
            ) {
              fields.push([key, value]);
            }
          });
          return (
            <Card key={`${title}-${index}`} className="flex flex-col">
              <CardHeader
                title={title}
                subtitle={kpiId}
                action={dateUnavailable ? <Badge tone="warning">No date filter</Badge> : <BookOpen className="h-4 w-4 text-teal" />}
              />
              <div className="flex-1 space-y-2 p-4">
                {fields.length === 0 && <p className="text-xs text-slate-400">No definition fields returned by the API.</p>}
                {fields.map(([key, value]) => (
                  <div key={key}>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{key.replace(/_/g, ' ')}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-ink">{displayValue(value)}</p>
                  </div>
                ))}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
