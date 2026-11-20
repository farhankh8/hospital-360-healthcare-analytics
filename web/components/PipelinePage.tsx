'use client';

import { useMemo, useState } from 'react';
import { GitBranch, History, Layers3, X } from 'lucide-react';
import { useApiQuery } from '@/lib/api';
import { useFilters } from '@/lib/filters';
import { usePageFilters } from '@/lib/page-filters';
import { type KpiMap, type TableRow } from '@/lib/types';
import { displayValue } from '@/lib/utils';
import { DataTable } from './DataTable';
import { KpiCard } from './KpiCard';
import { Badge, Card, CardHeader, EmptyState, ErrorState, PageHeading, Skeleton } from './ui';

const PIPELINE_KPI_IDS = [
  'latest_run', 'total_source_records', 'bronze_records', 'silver_records', 'gold_records',
  'valid_records', 'quarantined_records', 'processing_duration', 'failed_stages', 'last_successful_run',
];

function rowsFrom(data: unknown): TableRow[] {
  if (Array.isArray(data)) return data as TableRow[];
  if (data && typeof data === 'object') {
    const array = Object.values(data as Record<string, unknown>).find(Array.isArray);
    if (array) return array as TableRow[];
  }
  return [];
}

const COMPARE_KEYS = ['source_records', 'valid_records', 'quarantined_records', 'duration_seconds', 'tables_created'];

export function PipelinePage() {
  const { filters } = useFilters();
  const { params: pageParams } = usePageFilters();
  const [selected, setSelected] = useState<TableRow | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [lineageSearch, setLineageSearch] = useState('');
  const summaryQuery = useApiQuery<KpiMap>('pipeline-summary', '/pipeline/summary', filters, pageParams);
  const runsQuery = useApiQuery<unknown>('pipeline-runs', '/pipeline/runs', filters, { ...pageParams, page: 1, page_size: 100 });
  const lineageQuery = useApiQuery<unknown>('pipeline-lineage', '/pipeline/lineage', filters, pageParams);
  const manifestQuery = useApiQuery<unknown>('pipeline-manifest', '/pipeline/manifest', filters, pageParams);
  const pipelineKpis = useMemo<KpiMap>(() => {
    const payload = summaryQuery.data?.data as unknown;
    if (!payload || typeof payload !== 'object') return {};
    const record = payload as Record<string, unknown>;
    if (record.kpis && typeof record.kpis === 'object') return record.kpis as KpiMap;
    return record as KpiMap;
  }, [summaryQuery.data]);
  const runs = useMemo(() => rowsFrom(runsQuery.data?.data), [runsQuery.data]);
  const lineage = useMemo(() => rowsFrom(lineageQuery.data?.data), [lineageQuery.data]);
  const visibleLineage = useMemo(
    () => lineage.filter((row) => !lineageSearch || String(row.target_table ?? '').toLowerCase().includes(lineageSearch.toLowerCase())),
    [lineage, lineageSearch],
  );
  const compared = useMemo(
    () => runs.filter((run) => compareIds.includes(String(run.run_id ?? run.id ?? ''))).slice(0, 2),
    [runs, compareIds],
  );

  const toggleCompare = (run: TableRow) => {
    const id = String(run.run_id ?? run.id ?? '');
    if (!id) return;
    setCompareIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id].slice(-2));
  };

  return (
    <div className="space-y-6">
      <PageHeading title="Data Pipeline" description="Run history, manifests and lineage for the synthetic data pipeline." badge={<Badge tone="info">Engineering</Badge>} />

      <section aria-label="Key performance indicators">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Key indicators</h2>
          <span className="text-[11px] text-slate-400">Values from /pipeline/summary</span>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {summaryQuery.isLoading && PIPELINE_KPI_IDS.map((id) => <Skeleton key={id} className="h-[148px] w-full" />)}
          {!summaryQuery.isLoading && PIPELINE_KPI_IDS.map((id) => (
            <KpiCard key={id} kpiId={id} item={pipelineKpis[id]} route="/pipeline" />
          ))}
        </div>
      </section>

      <DataTable
        endpoint="/pipeline/runs"
        filters={filters}
        params={pageParams}
        title="Run history"
        exportName="pipeline-runs"
        onRowClick={setSelected}
        columns={[
          { key: 'run_id', title: 'Run ID', sortable: true },
          { key: 'start_time', title: 'Start', type: 'date', sortable: true },
          { key: 'end_time', title: 'End', type: 'date', sortable: true },
          { key: 'duration_seconds', title: 'Duration (s)', type: 'number', sortable: true },
          { key: 'status', title: 'Status', type: 'badge', sortable: true },
          { key: 'source_records', title: 'Source records', type: 'number', sortable: true },
          { key: 'valid_records', title: 'Valid', type: 'number', sortable: true },
          { key: 'quarantined_records', title: 'Quarantined', type: 'number', sortable: true },
          { key: 'tables_created', title: 'Tables', type: 'number', sortable: true },
          { key: 'error_message', title: 'Error', sortable: true },
        ]}
      />

      {selected && (
        <Card className="p-5">
          <div className="mb-3 flex items-start justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold text-navy">Run detail: {displayValue(selected.run_id ?? selected.id)}</h3>
              <p className="text-xs text-slate-500">Every field returned by /pipeline/runs for the selected run.</p>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => toggleCompare(selected)} className="rounded-md border border-line px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:border-teal hover:text-teal">
                {compareIds.includes(String(selected.run_id ?? selected.id)) ? 'Remove from compare' : 'Add to compare'}
              </button>
              <button type="button" onClick={() => setSelected(null)} aria-label="Close run detail"><X className="h-4 w-4 text-slate-400" /></button>
            </div>
          </div>
          {Boolean(selected.error_message) && <div className="mb-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">Error: {displayValue(selected.error_message)}</div>}
          <dl className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
            {Object.entries(selected).map(([key, value]) => (
              <div key={key} className="min-w-0 border-b border-line pb-2">
                <dt className="truncate text-[10px] uppercase tracking-wide text-slate-400">{key.replace(/_/g, ' ')}</dt>
                <dd className="mt-0.5 truncate text-xs font-medium text-ink">{displayValue(value)}</dd>
              </div>
            ))}
          </dl>
        </Card>
      )}

      {compared.length === 2 && (
        <Card className="p-5">
          <CardHeader title="Run comparison" subtitle={`${String(compared[0].run_id)} vs ${String(compared[1].run_id)}`} action={<History className="h-4 w-4 text-teal" />} />
          <table className="mt-3 w-full text-xs">
            <thead><tr className="border-b border-line text-left text-[10px] uppercase tracking-wide text-slate-400"><th className="py-2">Metric</th><th className="py-2">{displayValue(compared[0].run_id)}</th><th className="py-2">{displayValue(compared[1].run_id)}</th><th className="py-2">Delta</th></tr></thead>
            <tbody>
              {COMPARE_KEYS.map((key) => {
                const a = Number(compared[0][key] ?? 0);
                const b = Number(compared[1][key] ?? 0);
                return <tr key={key} className="border-b border-line/60"><td className="py-2 capitalize">{key.replace(/_/g, ' ')}</td><td className="py-2">{displayValue(compared[0][key])}</td><td className="py-2">{displayValue(compared[1][key])}</td><td className="py-2">{(b - a).toLocaleString()}</td></tr>;
              })}
            </tbody>
          </table>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Card>
          <CardHeader title="Pipeline lineage" subtitle="From /pipeline/lineage" action={<GitBranch className="h-4 w-4 text-teal" />} />
          <div className="p-4">
            <input
              value={lineageSearch}
              onChange={(event) => setLineageSearch(event.target.value)}
              placeholder="Filter by target table"
              data-testid="pipeline-lineage-search"
              className="mb-3 h-9 w-full rounded-md border border-line bg-white px-2.5 text-xs outline-none focus:border-teal"
            />
            <div className="max-h-80 overflow-auto">
              {visibleLineage.length === 0 ? <EmptyState message="No lineage rows match" /> : visibleLineage.map((row) => (
                <button key={String(row.target_table)} type="button" onClick={() => setSelected({ run_id: row.target_table, ...row })} className="mb-1 block w-full rounded border border-line px-2 py-2 text-left text-xs hover:border-teal hover:bg-teal-light/30">
                  <span className="font-medium text-navy">{displayValue(row.target_table)}</span>
                  <span className="ml-2 text-slate-400">{displayValue(row.layer)}</span>
                  <span className="mt-0.5 block truncate text-[10px] text-slate-500">{displayValue(row.source_tables)}</span>
                </button>
              ))}
            </div>
          </div>
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
          ) : <EmptyState message="No manifest returned" />}
        </Card>
      </div>
    </div>
  );
}
