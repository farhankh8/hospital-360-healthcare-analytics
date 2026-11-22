'use client';

import { useMemo } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Database, GitBranch } from 'lucide-react';
import { useApiQuery } from '@/lib/api';
import { useFilters } from '@/lib/filters';
import { usePageFilters } from '@/lib/page-filters';
import type { SelectOption, TableRow } from '@/lib/types';
import { NO_FILTERS } from '@/lib/types';
import { displayValue } from '@/lib/utils';
import { DataTable } from './DataTable';
import { Badge, Card, CardHeader, EmptyState, ErrorState, PageHeading, Select, Skeleton } from './ui';

function datasetOptions(data: unknown): SelectOption[] {
  const list = Array.isArray(data) ? data : data && typeof data === 'object' ? (Object.values(data as Record<string, unknown>).find(Array.isArray) as unknown[]) || [] : [];
  return list
    .map((item) => {
      if (typeof item === 'string') return { value: item, label: item.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase()) };
      if (item && typeof item === 'object') {
        const row = item as Record<string, unknown>;
        const value = String(row.dataset_name ?? row.name ?? row.id ?? row.table_name ?? row.dataset ?? '');
        if (!value) return null;
        return { value, label: String(row.label ?? row.display_name ?? value.replace(/_/g, ' ')) };
      }
      return null;
    })
    .filter((option): option is SelectOption => Boolean(option));
}

function schemaRows(data: unknown): TableRow[] {
  if (Array.isArray(data)) return data as TableRow[];
  if (data && typeof data === 'object') {
    const object = data as Record<string, unknown>;
    const array = Object.values(object).find(Array.isArray);
    if (array) return array as TableRow[];
    return Object.entries(object).map(([column, definition]) => ({ column_name: column, data_type: typeof definition === 'string' ? definition : JSON.stringify(definition) }));
  }
  return [];
}

const NUMERIC_HINTS = ['INTEGER', 'BIGINT', 'DOUBLE', 'FLOAT', 'DECIMAL', 'HUGEINT', 'REAL'];

export function ExplorerPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { filters } = useFilters();
  const { params: pageParams, setPageParam } = usePageFilters();

  const datasetsQuery = useApiQuery<unknown>('explorer-datasets', '/explorer/datasets', NO_FILTERS);
  const datasets = useMemo(() => datasetOptions(datasetsQuery.data?.data), [datasetsQuery.data]);
  const selected = searchParams.get('dataset') || datasets[0]?.value || '';
  const endpoint = selected ? `/explorer/${encodeURIComponent(selected)}/records` : undefined;
  const schemaQuery = useApiQuery<unknown>(`explorer-schema-${selected}`, selected ? `/explorer/${encodeURIComponent(selected)}/schema` : undefined, NO_FILTERS, undefined, Boolean(selected));
  const lineageQuery = useApiQuery<unknown>('pipeline-lineage', '/pipeline/lineage', NO_FILTERS);
  const schema = useMemo(() => schemaRows(schemaQuery.data?.data), [schemaQuery.data]);
  const numericColumns = useMemo(
    () => schema.filter((row) => NUMERIC_HINTS.some((hint) => String(row.column_type ?? row.data_type ?? '').toUpperCase().includes(hint))),
    [schema],
  );
  const lineageRows = useMemo(() => {
    const data = lineageQuery.data?.data;
    const rows = Array.isArray(data) ? data : data && typeof data === 'object' ? Object.values(data as Record<string, unknown>).find(Array.isArray) ?? [] : [];
    return (rows as TableRow[]).filter((row) => !selected || String(row.target_table ?? '').includes(selected));
  }, [lineageQuery.data, selected]);

  const selectDataset = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set('dataset', value);
    else params.delete('dataset');
    params.delete('numeric_column');
    params.delete('numeric_min');
    params.delete('numeric_max');
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  return (
    <div className="space-y-6">
      <PageHeading title="Data Explorer" description="Inspect validated, record-level datasets with schema, numeric range filters and source lineage." badge={<Badge tone="info">Record level</Badge>} />

      <Card className="p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-64">
            <Select label="Dataset" value={selected} onChange={(event) => selectDataset(event.target.value)} options={datasets} placeholder="Select a dataset" disabled={datasetsQuery.isLoading} data-testid="explorer-dataset-select" />
          </div>
          <div className="w-52">
            <Select
              label="Numeric column"
              value={pageParams.numeric_column ?? ''}
              onChange={(event) => setPageParam('numeric_column', event.target.value)}
              options={numericColumns.map((row) => ({ value: String(row.column_name), label: String(row.column_name) }))}
              placeholder="No numeric filter"
              data-testid="explorer-numeric-column"
            />
          </div>
          <div className="w-32">
            <label htmlFor="explorer-numeric-min" className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted">Minimum</label>
            <input id="explorer-numeric-min" aria-label="Minimum" value={pageParams.numeric_min ?? ''} onChange={(event) => setPageParam('numeric_min', event.target.value)} placeholder="Min" data-testid="explorer-numeric-min" className="h-9 w-full rounded-md border border-line bg-surface px-2.5 text-xs outline-none focus:border-teal" />
          </div>
          <div className="w-32">
            <label htmlFor="explorer-numeric-max" className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted">Maximum</label>
            <input id="explorer-numeric-max" aria-label="Maximum" value={pageParams.numeric_max ?? ''} onChange={(event) => setPageParam('numeric_max', event.target.value)} placeholder="Max" data-testid="explorer-numeric-max" className="h-9 w-full rounded-md border border-line bg-surface px-2.5 text-xs outline-none focus:border-teal" />
          </div>
          <p className="pb-2 text-xs text-muted">{datasets.length} datasets · server-side pagination · maximum page size enforced by the API</p>
        </div>
        {datasetsQuery.isError && <p className="mt-3 text-xs text-critical">Datasets could not be loaded: {datasetsQuery.error?.message}</p>}
      </Card>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="xl:col-span-2">
          {selected ? (
            <DataTable endpoint={endpoint} columns={[]} filters={filters} params={pageParams} title={`${selected} records`} exportName={`explorer-${selected}`} initialSearch={searchParams.get('search') || ''} />
          ) : <Card><EmptyState message="Select a dataset" hint="Choose a dataset to load its records." /></Card>}
        </div>
        <div className="space-y-5">
          <Card>
            <CardHeader title="Schema" subtitle={selected || 'No dataset selected'} action={<Database className="h-4 w-4 text-teal" />} />
            {schemaQuery.isLoading ? (
              <div className="space-y-2 p-4">{Array.from({ length: 6 }).map((_item, index) => <Skeleton key={index} className="h-5 w-full" />)}</div>
            ) : schemaQuery.isError ? <ErrorState message="Schema unavailable" /> : schema.length === 0 ? <EmptyState message="No schema returned" /> : (
              <div className="max-h-[420px] overflow-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-canvas text-[10px] uppercase tracking-wide text-muted"><tr><th className="px-4 py-2">Column</th><th className="px-4 py-2">Type</th></tr></thead>
                  <tbody className="divide-y divide-line">
                    {schema.map((row, index) => (
                      <tr key={index} className="cursor-pointer hover:bg-teal-light/30" onClick={() => setPageParam('numeric_column', String(row.column_name))}>
                        <td className="px-4 py-2 font-medium text-ink">{displayValue(row.column_name ?? row.name ?? row.column)}</td>
                        <td className="px-4 py-2 text-muted">{displayValue(row.column_type ?? row.data_type ?? row.type)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
          <Card>
            <CardHeader title="Source lineage" subtitle={selected ? `Sources for ${selected}` : 'From /pipeline/lineage'} action={<GitBranch className="h-4 w-4 text-teal" />} />
            {lineageQuery.isLoading ? <div className="p-4"><Skeleton className="h-24 w-full" /></div> : lineageQuery.isError ? <ErrorState message="Lineage unavailable" /> : (
              <div className="max-h-72 space-y-2 overflow-auto p-4">
                {lineageRows.length === 0 ? <EmptyState message="No lineage rows for this dataset" /> : lineageRows.map((row, index) => (
                  <div key={index} className="rounded border border-line p-2 text-[11px]">
                    <p className="font-medium text-navy">{displayValue(row.target_table)}</p>
                    <p className="mt-0.5 text-muted">{displayValue(row.source_tables)}</p>
                    <p className="mt-0.5 text-muted">{displayValue(row.transformations)}</p>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
