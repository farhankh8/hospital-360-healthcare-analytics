'use client';

import { useMemo } from 'react';
import { GitBranch, History, Layers3 } from 'lucide-react';
import { useApiQuery } from '@/lib/api';
import { NO_FILTERS, type TableRow } from '@/lib/types';
import { displayValue } from '@/lib/utils';
import { DataTable } from './DataTable';
import { Badge, Card, CardHeader, EmptyState, ErrorState, PageHeading, Skeleton } from './ui';

function rowsFrom(data: unknown): TableRow[] {
  if (Array.isArray(data)) return data as TableRow[];
  if (data && typeof data === 'object') {
    const array = Object.values(data as Record<string, unknown>).find(Array.isArray);
    if (array) return array as TableRow[];
  }
  return [];
}

export function PipelinePage() {
  const runsQuery = useApiQuery<unknown>('pipeline-runs', '/pipeline/runs', NO_FILTERS, { page: 1, page_size: 100 });
  const lineageQuery = useApiQuery<unknown>('pipeline-lineage', '/pipeline/lineage', NO_FILTERS);
  const manifestQuery = useApiQuery<unknown>('pipeline-manifest', '/pipeline/manifest', NO_FILTERS);
  const runs = useMemo(() => rowsFrom(runsQuery.data?.data), [runsQuery.data]);

  const stats = useMemo(() => {
    const statusOf = (row: TableRow) => String(row.status ?? row.run_status ?? '').toLowerCase();
    const success = runs.filter((row) => /success|complete|ok/.test(statusOf(row))).length;
    const failed = runs.filter((row) => /fail|error/.test(statusOf(row))).length;
    const latest = [...runs].sort((a, b) => String(b.start_time ?? b.created_at ?? b.run_id ?? '').localeCompare(String(a.start_time ?? a.created_at ?? a.run_id ?? '')))[0];
    return {
      total: runs.length,
      success,
      failed,
      latest: latest ? displayValue(latest.run_id ?? latest.id) : '—',
      latestStatus: latest ? displayValue(latest.status ?? latest.run_status) : '—',
    };
  }, [runs]);

  return (
    <div className="space-y-6">
      <PageHeading title="Data Pipeline" description="Run history, manifests and lineage for the synthetic data pipeline." badge={<Badge tone="info">Engineering</Badge>} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {[
          ['Total runs', stats.total],
          ['Successful', stats.success],
          ['Failed', stats.failed],
          ['Latest run', stats.latest],
          ['Latest status', stats.latestStatus],
        ].map(([label, value]) => (
          <Card key={String(label)} className="p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
            <p className="mt-2 truncate text-xl font-semibold text-navy">{displayValue(value)}</p>
          </Card>
        ))}
        {runsQuery.isLoading && <Skeleton className="col-span-full h-2" />}
        {runsQuery.isError && <Card className="col-span-full"><ErrorState message={runsQuery.error?.message || 'Run history unavailable'} /></Card>}
      </div>

      <DataTable
        endpoint="/pipeline/runs"
        filters={NO_FILTERS}
        title="Run history"
        exportName="pipeline-runs"
        columns={[
          { key: 'run_id', title: 'Run ID', sortable: true },
          { key: 'start_time', title: 'Start', type: 'date', sortable: true },
          { key: 'end_time', title: 'End', type: 'date', sortable: true },
          { key: 'duration_seconds', title: 'Duration (s)', type: 'number', sortable: true },
          { key: 'status', title: 'Status', type: 'badge', sortable: true },
          { key: 'source_records', title: 'Source records', type: 'number', sortable: true },
          { key: 'valid_records', title: 'Valid', type: 'number', sortable: true },
          { key: 'invalid_records', title: 'Invalid', type: 'number', sortable: true },
          { key: 'tables_created', title: 'Tables', type: 'number', sortable: true },
          { key: 'error_message', title: 'Error', sortable: true },
        ]}
      />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Card>
          <CardHeader title="Pipeline lineage" subtitle="From /pipeline/lineage" action={<GitBranch className="h-4 w-4 text-teal" />} />
          {lineageQuery.isLoading ? (
            <div className="p-4"><Skeleton className="h-32 w-full" /></div>
          ) : lineageQuery.isError ? (
            <ErrorState message="Lineage unavailable" />
          ) : (
            <div className="max-h-96 overflow-auto p-4">
              <pre className="whitespace-pre-wrap text-[10px] leading-relaxed text-slate-600">{JSON.stringify(lineageQuery.data?.data ?? {}, null, 2)}</pre>
            </div>
          )}
        </Card>
        <Card>
          <CardHeader title="Latest manifest" subtitle="From /pipeline/manifest" action={<Layers3 className="h-4 w-4 text-teal" />} />
          {manifestQuery.isLoading ? (
            <div className="p-4"><Skeleton className="h-32 w-full" /></div>
          ) : manifestQuery.isError ? (
            <ErrorState message="Manifest unavailable" />
          ) : manifestQuery.data?.data && Object.keys(manifestQuery.data.data as object).length ? (
            <dl className="grid grid-cols-2 gap-3 p-4">
              {Object.entries(manifestQuery.data.data as Record<string, unknown>).slice(0, 24).map(([key, value]) => (
                <div key={key} className="min-w-0 border-b border-line pb-2">
                  <dt className="truncate text-[10px] uppercase tracking-wide text-slate-400">{key.replace(/_/g, ' ')}</dt>
                  <dd className="mt-0.5 truncate text-xs font-medium text-ink">{displayValue(value)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <EmptyState message="No manifest returned" />
          )}
        </Card>
      </div>

      <p className="flex items-center gap-2 text-[11px] text-slate-400"><History className="h-3.5 w-3.5" /> Select a run in the table to inspect its full record.</p>
    </div>
  );
}
