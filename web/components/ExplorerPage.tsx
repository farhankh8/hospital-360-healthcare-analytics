'use client';

import { useMemo } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Database, GitBranch } from 'lucide-react';
import { useApiQuery } from '@/lib/api';
import { useFilters } from '@/lib/filters';
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

export function ExplorerPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { filters } = useFilters();

  const datasetsQuery = useApiQuery<unknown>('explorer-datasets', '/explorer/datasets', NO_FILTERS);
  const datasets = useMemo(() => datasetOptions(datasetsQuery.data?.data), [datasetsQuery.data]);
  const selected = searchParams.get('dataset') || datasets[0]?.value || '';
  const endpoint = selected ? `/explorer/${encodeURIComponent(selected)}/records` : undefined;
  const schemaQuery = useApiQuery<unknown>(`explorer-schema-${selected}`, selected ? `/explorer/${encodeURIComponent(selected)}/schema` : undefined, NO_FILTERS, undefined, Boolean(selected));
  const lineageQuery = useApiQuery<unknown>('pipeline-lineage', '/pipeline/lineage', NO_FILTERS);
  const schema = useMemo(() => schemaRows(schemaQuery.data?.data), [schemaQuery.data]);

  const selectDataset = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set('dataset', value);
    else params.delete('dataset');
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  return (
    <div className="space-y-6">
      <PageHeading title="Data Explorer" description="Inspect validated, record-level datasets with schema and source lineage from the API." badge={<Badge tone="info">Record level</Badge>} />

      <Card className="p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-64">
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-400">Dataset</label>
            <Select value={selected} onChange={(event) => selectDataset(event.target.value)} options={datasets} placeholder="Select a dataset" disabled={datasetsQuery.isLoading} />
          </div>
          <p className="pb-2 text-xs text-slate-500">{datasets.length} datasets available · server-side pagination · maximum page size enforced by the API</p>
        </div>
        {datasetsQuery.isError && <p className="mt-3 text-xs text-critical">Datasets could not be loaded: {datasetsQuery.error?.message}</p>}
      </Card>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="xl:col-span-2">
          {selected ? (
            <DataTable endpoint={endpoint} columns={[]} filters={filters} title={`${selected} records`} exportName={`explorer-${selected}`} initialSearch={searchParams.get('search') || ''} />
          ) : (
            <Card><EmptyState message="Select a dataset" hint="Choose a dataset to load its records." /></Card>
          )}
        </div>
        <div className="space-y-5">
          <Card>
            <CardHeader title="Schema" subtitle={selected || 'No dataset selected'} action={<Database className="h-4 w-4 text-teal" />} />
            {schemaQuery.isLoading ? (
              <div className="space-y-2 p-4">{Array.from({ length: 6 }).map((_item, index) => <Skeleton key={index} className="h-5 w-full" />)}</div>
            ) : schemaQuery.isError ? (
              <ErrorState message="Schema unavailable" />
            ) : schema.length === 0 ? (
              <EmptyState message="No schema returned" />
            ) : (
              <div className="max-h-[420px] overflow-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-canvas text-[10px] uppercase tracking-wide text-slate-400">
                    <tr><th className="px-4 py-2">Column</th><th className="px-4 py-2">Type</th></tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {schema.map((row, index) => (
                      <tr key={index}>
                        <td className="px-4 py-2 font-medium text-ink">{displayValue(row.column_name ?? row.name ?? row.column)}</td>
                        <td className="px-4 py-2 text-slate-500">{displayValue(row.data_type ?? row.type ?? row.dtype)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card>
            <CardHeader title="Source lineage" subtitle="From /pipeline/lineage" action={<GitBranch className="h-4 w-4 text-teal" />} />
            {lineageQuery.isLoading ? (
              <div className="p-4"><Skeleton className="h-24 w-full" /></div>
            ) : lineageQuery.isError ? (
              <ErrorState message="Lineage unavailable" />
            ) : (
              <details className="p-4">
                <summary className="cursor-pointer text-xs font-medium text-teal">View lineage definition</summary>
                <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded bg-canvas p-3 text-[10px] leading-relaxed text-slate-600">
                  {JSON.stringify(lineageQuery.data?.data ?? {}, null, 2)}
                </pre>
              </details>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
