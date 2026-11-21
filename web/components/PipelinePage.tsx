'use client';

import { useMemo, useState } from 'react';
import { GitBranch, History, Layers3, X } from 'lucide-react';
import { useApiQuery } from '@/lib/api';
import { useFilters } from '@/lib/filters';
import { usePageFilters } from '@/lib/page-filters';
import { type KpiMap, type TableRow } from '@/lib/types';
import { displayValue } from '@/lib/utils';
import EChart from './EChart';
import { DataTable } from './DataTable';
import { useDrilldown } from './DrilldownDrawer';
import { KpiCard } from './KpiCard';
import { Badge, Card, CardHeader, EmptyState, ErrorState, PageHeading, Skeleton } from './ui';

const PIPELINE_KPI_IDS = [
  'latest_run', 'total_source_records', 'bronze_records', 'silver_records', 'gold_records',
  'valid_records', 'quarantined_records', 'processing_duration', 'failed_stages', 'last_successful_run',
];

const PIPELINE_STAGES = ['Generate', 'Bronze', 'Schema validation', 'Silver', 'Quality tests', 'Gold', 'DuckDB', 'API refresh'];

function rowsFrom(data: unknown): TableRow[] {
  if (Array.isArray(data)) return data as TableRow[];
  if (data && typeof data === 'object') {
    const array = Object.values(data as Record<string, unknown>).find(Array.isArray);
    if (array) return array as TableRow[];
  }
  return [];
}

function stageStatus(selected: TableRow | null, stage: string): 'success' | 'failed' | 'pending' | 'unknown' {
  if (!selected) return 'unknown';
  const status = String(selected.status ?? '').toLowerCase();
  const error = String(selected.error_message ?? '').toLowerCase();
  if (status === 'success' || status === 'succeeded') return 'success';
  if (status === 'failed' || status === 'error') {
    // Best-effort mapping from error text; default to failed at validation/quality when unknown.
    if (error.includes(stage.toLowerCase())) return 'failed';
    const order = PIPELINE_STAGES.indexOf(stage);
    const failAt = PIPELINE_STAGES.findIndex((s) => error.includes(s.toLowerCase()));
    if (failAt >= 0) return order < failAt ? 'success' : order === failAt ? 'failed' : 'pending';
    return stage === 'Quality tests' ? 'failed' : PIPELINE_STAGES.indexOf(stage) < PIPELINE_STAGES.indexOf('Quality tests') ? 'success' : 'pending';
  }
  return 'unknown';
}

export function PipelinePage() {
  const { filters } = useFilters();
  const { params: pageParams } = usePageFilters();
  const { openDrilldown } = useDrilldown();
  const [selected, setSelected] = useState<TableRow | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [lineageSearch, setLineageSearch] = useState('');

  const summaryQuery = useApiQuery<KpiMap>('pipeline-summary', '/pipeline/summary', filters, pageParams);
  const runsQuery = useApiQuery<unknown>('pipeline-runs', '/pipeline/runs', filters, { ...pageParams, page: 1, page_size: 100 });
  const lineageQuery = useApiQuery<unknown>('pipeline-lineage', '/pipeline/lineage', filters, pageParams);
  const manifestQuery = useApiQuery<unknown>('pipeline-manifest', '/pipeline/manifest', filters, pageParams);
  const selectedId = String(selected?.run_id ?? selected?.id ?? '');
  const runDetailQuery = useApiQuery<Record<string, unknown>>(`pipeline-run-${selectedId}`, selectedId ? `/pipeline/runs/${encodeURIComponent(selectedId)}` : undefined, filters, undefined, Boolean(selectedId));
  const compareA = compareIds[0] ?? '';
  const compareB = compareIds[1] ?? '';
  const compareQuery = useApiQuery<Record<string, unknown>>(
    `pipeline-compare-${compareA}-${compareB}`,
    compareA && compareB ? `/pipeline/runs/compare?run_a=${encodeURIComponent(compareA)}&run_b=${encodeURIComponent(compareB)}` : undefined,
    filters,
    undefined,
    Boolean(compareA && compareB),
  );

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
  const selectedDetail = (runDetailQuery.data?.data as TableRow | undefined) ?? selected;

  const toggleCompare = (run: TableRow) => {
    const id = String(run.run_id ?? run.id ?? '');
    if (!id) return;
    setCompareIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id].slice(-2));
  };

  const compareData = (compareQuery.data?.data as Record<string, unknown> | undefined) ?? null;
  const compareTables = useMemo(
    () => (Array.isArray(compareData?.tables) ? (compareData?.tables as Array<Record<string, unknown>>) : []),
    [compareData],
  );
  const compareChartOption = useMemo(() => {
    const top = compareTables.slice(0, 12);
    return {
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 40, right: 20, top: 35, bottom: 60 },
      xAxis: { type: 'category', data: top.map((t) => String(t.table)), axisLabel: { rotate: 30, fontSize: 10 } },
      yAxis: { type: 'value' },
      series: [
        { name: 'Valid delta', type: 'bar', data: top.map((t) => Number((t.delta as Record<string, unknown>)?.valid ?? 0)), itemStyle: { color: '#0f766e' } },
        { name: 'Quarantined delta', type: 'bar', data: top.map((t) => Number((t.delta as Record<string, unknown>)?.quarantined ?? 0)), itemStyle: { color: '#b45309' } },
      ],
    };
  }, [compareTables]);

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
          { key: 'quarantined_records', title: 'Invalid/Quarantined', type: 'number', sortable: true },
          { key: 'tables_created', title: 'Tables created', type: 'number', sortable: true },
          { key: 'error_message', title: 'Error message', sortable: true },
        ]}
      />

      {selectedDetail && (
        <Card className="p-5">
          <div className="mb-3 flex items-start justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold text-navy">Run detail: {displayValue(selectedDetail.run_id ?? selectedDetail.id)}</h3>
              <p className="text-xs text-slate-500">Stage status, metadata, and error detail for the selected run.</p>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => toggleCompare(selectedDetail)} className="rounded-md border border-line px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:border-teal hover:text-teal">
                {compareIds.includes(String(selectedDetail.run_id ?? selectedDetail.id)) ? 'Remove from compare' : 'Add to compare'}
              </button>
              <button type="button" onClick={() => setSelected(null)} aria-label="Close run detail"><X className="h-4 w-4 text-slate-400" /></button>
            </div>
          </div>

          <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-8">
            {PIPELINE_STAGES.map((stage) => {
              const st = stageStatus(selectedDetail, stage);
              const tone = st === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : st === 'failed' ? 'bg-rose-50 border-rose-200 text-rose-700' : st === 'pending' ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-slate-50 border-slate-200 text-slate-600';
              return <div key={stage} className={`rounded-md border px-2 py-2 text-center text-[11px] font-medium ${tone}`}>{stage}<div className="text-[10px] font-normal uppercase">{st}</div></div>;
            })}
          </div>

          {Boolean(selectedDetail.error_message) ? (
            <button type="button" onClick={() => openDrilldown({ ...selectedDetail, endpoint: '/pipeline/runs' }, `Error: ${String(selectedDetail.run_id ?? '')}`)} className="mb-3 w-full rounded-md border border-rose-200 bg-rose-50 p-3 text-left text-xs text-rose-700 hover:bg-rose-100">
              Error: {displayValue(selectedDetail.error_message)} <span className="ml-2 underline">Open error detail</span>
            </button>
          ) : (
            <div className="mb-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">No errors for this run.</div>
          )}

          <dl className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
            {Object.entries(selectedDetail).filter(([k]) => k !== 'stages').map(([key, value]) => (
              <div key={key} className="min-w-0 border-b border-line pb-2">
                <dt className="truncate text-[10px] uppercase tracking-wide text-slate-400">{key.replace(/_/g, ' ')}</dt>
                <dd className="mt-0.5 truncate text-xs font-medium text-ink">{typeof value === 'object' ? JSON.stringify(value) : displayValue(value)}</dd>
              </div>
            ))}
          </dl>
        </Card>
      )}

      <Card className="p-5">
        <CardHeader title="Compare runs" subtitle="Select two runs in Run detail to compare record counts, duration and DQ score." action={<History className="h-4 w-4 text-teal" />} />
        {compareIds.length < 2 ? (
          <EmptyState message="Pick two runs using 'Add to compare' in run detail." />
        ) : compareQuery.isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : compareQuery.isError ? (
          <ErrorState message="Compare request failed" />
        ) : compareData ? (
          <div className="space-y-4">
            <div className="overflow-auto">
              <table className="w-full text-xs">
                <thead><tr className="border-b border-line text-left text-[10px] uppercase tracking-wide text-slate-400"><th className="py-2">Metric</th><th className="py-2">{String((compareData.run_a as Record<string, unknown>)?.run_id ?? compareA)}</th><th className="py-2">{String((compareData.run_b as Record<string, unknown>)?.run_id ?? compareB)}</th><th className="py-2">Delta (B-A)</th></tr></thead>
                <tbody>
                  {Object.entries((compareData.deltas as Record<string, unknown>) ?? {}).map(([key, value]) => {
                    const num = typeof value === 'number' ? value : null;
                    const unfavorable = (key.includes('quarantine') || key.includes('duration')) ? (num ?? 0) > 0 : (key.includes('dq_score') || key.includes('valid') || key.includes('source')) ? (num ?? 0) < 0 : false;
                    return <tr key={key} className="border-b border-line/60"><td className="py-2 capitalize">{key.replace(/_/g, ' ')}</td><td className="py-2">{displayValue((compareData.run_a as Record<string, unknown>)?.[key])}</td><td className="py-2">{displayValue((compareData.run_b as Record<string, unknown>)?.[key])}</td><td className={`py-2 font-medium ${unfavorable ? 'text-rose-600' : 'text-emerald-600'}`}>{displayValue(value)}</td></tr>;
                  })}
                </tbody>
              </table>
            </div>
            <div className="h-72"><EChart option={compareChartOption as never} height={280} /></div>
            <div className="max-h-64 overflow-auto">
              <table className="w-full text-xs">
                <thead><tr className="border-b border-line text-left text-[10px] uppercase tracking-wide text-slate-400"><th className="py-2">Table</th><th className="py-2">Valid A</th><th className="py-2">Valid B</th><th className="py-2">Delta</th><th className="py-2">Quar. delta</th></tr></thead>
                <tbody>{compareTables.slice(0, 50).map((t) => { const d = (t.delta as Record<string, unknown>) ?? {}; return <tr key={String(t.table)} className="border-b border-line/60"><td className="py-2">{String(t.table)}</td><td className="py-2">{displayValue((t.run_a as Record<string, unknown>)?.valid)}</td><td className="py-2">{displayValue((t.run_b as Record<string, unknown>)?.valid)}</td><td className="py-2">{displayValue(d.valid)}</td><td className="py-2">{displayValue(d.quarantined)}</td></tr>; })}</tbody>
              </table>
            </div>
          </div>
        ) : <EmptyState message="No compare data" />}
      </Card>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Card>
          <CardHeader title="Pipeline lineage" subtitle="From /pipeline/lineage" action={<GitBranch className="h-4 w-4 text-teal" />} />
          <div className="p-4">
            <input value={lineageSearch} onChange={(event) => setLineageSearch(event.target.value)} placeholder="Filter by target table" data-testid="pipeline-lineage-search" className="mb-3 h-9 w-full rounded-md border border-line bg-white px-2.5 text-xs outline-none focus:border-teal" />
            <div className="max-h-80 overflow-auto">
              {visibleLineage.length === 0 ? <EmptyState message="No lineage rows match" /> : visibleLineage.map((row) => (
                <button key={String(row.target_table)} type="button" onClick={() => openDrilldown({ ...row, endpoint: `/pipeline/lineage/${encodeURIComponent(String(row.target_table))}` }, `Lineage: ${String(row.target_table)}`)} className="mb-1 block w-full rounded border border-line px-2 py-2 text-left text-xs hover:border-teal hover:bg-teal-light/30">
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
          {manifestQuery.isLoading ? <div className="p-4"><Skeleton className="h-32 w-full" /></div>
            : manifestQuery.isError ? <ErrorState message="Manifest unavailable" />
            : manifestQuery.data?.data && Object.keys(manifestQuery.data.data as object).length ? (
              <dl className="grid grid-cols-2 gap-3 p-4">
                {Object.entries(manifestQuery.data.data as Record<string, unknown>).slice(0, 24).map(([key, value]) => (
                  <div key={key} className="min-w-0 border-b border-line pb-2">
                    <dt className="truncate text-[10px] uppercase tracking-wide text-slate-400">{key.replace(/_/g, ' ')}</dt>
                    <dd className="mt-0.5 truncate text-xs font-medium text-ink">{typeof value === 'object' ? JSON.stringify(value) : displayValue(value)}</dd>
                  </div>
                ))}
              </dl>
            ) : <EmptyState message="No manifest returned" />}
        </Card>
      </div>
    </div>
  );
}
