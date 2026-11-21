'use client';

import { useMemo } from 'react';
import { ShieldCheck } from 'lucide-react';
import { useApiQuery } from '@/lib/api';
import { useFilters } from '@/lib/filters';
import { usePageFilters } from '@/lib/page-filters';
import { type ChartConfig, type FilterState, type KpiMap } from '@/lib/types';
import { ChartContainer } from './ChartContainer';
import { DataTable } from './DataTable';
import { KpiCard } from './KpiCard';
import { Badge, Card, EmptyState, ErrorState, PageHeading, Skeleton } from './ui';

const DQ_CHARTS: ChartConfig[] = [
  { title: 'Completeness by dataset', endpoint: '/charts/dq/completeness', type: 'horizontal-bar', dataKey: 'completeness', xKey: 'label', valueKey: 'completeness', span: 1 },
  { title: 'Uniqueness violations', endpoint: '/charts/dq/uniqueness', type: 'bar', dataKey: 'violations', xKey: 'label', valueKey: 'violations', span: 1 },
  { title: 'Validity rule failures', endpoint: '/charts/dq/validity', type: 'bar', dataKey: 'failures', xKey: 'label', valueKey: 'failures', span: 1 },
  { title: 'Consistency checks', endpoint: '/charts/dq/consistency', type: 'bar', dataKey: 'pass_rate', xKey: 'label', valueKey: 'pass_rate', span: 1 },
  { title: 'Missing values by rule', endpoint: '/charts/dq/missing-by-column', type: 'horizontal-bar', dataKey: 'missing', xKey: 'label', valueKey: 'missing', span: 1 },
  { title: 'Duplicate detection', endpoint: '/charts/dq/duplicates', type: 'bar', dataKey: 'duplicates', xKey: 'label', valueKey: 'duplicates', span: 1 },
  { title: 'Rule pass rate', endpoint: '/charts/dq/rule-pass-rate', type: 'bar', dataKey: 'pass_rate', xKey: 'label', valueKey: 'pass_rate', span: 1 },
  { title: 'Validation trend over time', endpoint: '/charts/dq/validation-trend', type: 'line', dataKey: 'validation', xKey: 'period', span: 1 },
  { title: 'Quarantine trend', endpoint: '/charts/dq/quarantine-trend', type: 'line', dataKey: 'quarantine', xKey: 'period', span: 2 },
  { title: 'Quarantine by rule', endpoint: '/charts/dq/quarantine-by-rule', type: 'bar', dataKey: 'quarantined', xKey: 'label', valueKey: 'quarantined', span: 1 },
  { title: 'Quarantine by dataset', endpoint: '/charts/dq/quarantine-by-dataset', type: 'horizontal-bar', dataKey: 'quarantined', xKey: 'label', valueKey: 'quarantined', span: 1 },
  { title: 'Injected vs detected DQ issues', endpoint: '/charts/dq/injected-vs-detected', type: 'bar', dataKey: 'comparison', xKey: 'label', seriesKeys: ['injected', 'detected'], span: 2 },
];

const DQ_KPI_IDS = [
  'total_records_processed', 'valid_records', 'invalid_records', 'data_quality_score',
  'duplicate_records', 'missing_values', 'referential_integrity_violations',
  'invalid_dates', 'failed_checks', 'quarantined_records',
];

function DqChart({ config, filters, params }: { config: ChartConfig; filters: FilterState; params: Record<string, string> }) {
  const query = useApiQuery<unknown>(`dq-chart-${config.endpoint}`, config.endpoint, filters, params);
  const drillable = { ...config, drilldownEndpoint: config.drilldownEndpoint ?? '/data-quality/failures' };
  return (
    <div className={config.span === 2 ? 'xl:col-span-2' : undefined}>
      <ChartContainer config={drillable} data={query.data?.data} loading={query.isLoading} error={query.error} onRetry={() => query.refetch()} />
    </div>
  );
}

export function DataQualityPage() {
  const { filters } = useFilters();
  const { params: pageParams } = usePageFilters();
  const summaryQuery = useApiQuery<{ kpis?: KpiMap }>('dq-summary', '/data-quality/summary', filters, pageParams);
  const kpis = useMemo(() => summaryQuery.data?.data?.kpis, [summaryQuery.data]);

  return (
    <div className="space-y-6">
      <PageHeading title="Data Quality" description="Validation rules, detected failures and dataset-level quality indicators." badge={<Badge tone="info">Engineering</Badge>} />

      <Card className="border-amber-200 bg-amber-50/60 p-4 text-sm text-slate-700">
        <p className="font-medium text-slate-900">Post-quarantine DQ rule score: silver passes all rules after invalid rows are quarantined.</p>
        <p className="mt-1 text-muted">
          The DQ rule checks below run on cleaned silver/gold data. Detections at ingestion are shown in the quarantine charts below, so a 100% post-quarantine score does not mean raw input was perfect.
        </p>
      </Card>

      <section aria-label="Key performance indicators">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">Key indicators</h2>
          <span className="text-[11px] text-muted">Values from /data-quality/summary</span>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {summaryQuery.isLoading && DQ_KPI_IDS.map((id) => <Skeleton key={id} className="h-[148px] w-full" />)}
          {!summaryQuery.isLoading && DQ_KPI_IDS.map((id) => (
            <KpiCard key={id} kpiId={id} item={kpis?.[id]} route="/data-quality" />
          ))}
        </div>
        {summaryQuery.isError && <Card className="mt-3"><ErrorState message={summaryQuery.error?.message || 'Quality summary unavailable'} onRetry={() => summaryQuery.refetch()} /></Card>}
        {!summaryQuery.isLoading && !summaryQuery.isError && (!kpis || Object.keys(kpis).length === 0) && <Card className="mt-3"><EmptyState message="No summary values returned" /></Card>}
      </section>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-2">
        {DQ_CHARTS.map((config) => <DqChart key={config.endpoint} config={config} filters={filters} params={pageParams} />)}
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <DataTable endpoint="/data-quality/datasets" columns={[
          { key: 'dataset', title: 'Dataset', sortable: true },
          { key: 'records', title: 'Records', type: 'number', sortable: true },
          { key: 'valid_records', title: 'Valid', type: 'number', sortable: true },
          { key: 'invalid_records', title: 'Invalid', type: 'number', sortable: true },
          { key: 'quality_score', title: 'Quality score', type: 'number', sortable: true },
          { key: 'status', title: 'Status', type: 'badge', sortable: true },
        ]} filters={filters} params={pageParams} title="Datasets" exportName="dq-datasets" />
        <DataTable endpoint="/data-quality/rules" columns={[
          { key: 'rule_id', title: 'Rule ID', sortable: true },
          { key: 'rule_name', title: 'Rule', sortable: true },
          { key: 'dataset', title: 'Dataset', sortable: true },
          { key: 'severity', title: 'Severity', type: 'badge', sortable: true },
          { key: 'description', title: 'Description', sortable: true },
          { key: 'status', title: 'Status', type: 'badge', sortable: true },
        ]} filters={filters} params={pageParams} title="Validation rules" exportName="dq-rules" primaryExport={false} />
      </div>

      <DataTable endpoint="/data-quality/failures" columns={[
        { key: 'failure_id', title: 'Validation ID', sortable: true },
        { key: 'table_name', title: 'Dataset', sortable: true },
        { key: 'record_id', title: 'Record ID', sortable: true },
        { key: 'rule_id', title: 'Rule', sortable: true },
        { key: 'failure_reason', title: 'Failure reason', sortable: true },
        { key: 'severity', title: 'Severity', type: 'badge', sortable: true },
        { key: 'detected_at', title: 'Detected', type: 'date', sortable: true },
        { key: 'pipeline_run_id', title: 'Pipeline run', sortable: true },
      ]} filters={filters} params={pageParams} title="Validation failures" exportName="dq-failures" primaryExport={false} />

      <p className="flex items-center gap-2 text-[11px] text-muted"><ShieldCheck className="h-3.5 w-3.5" /> Intentional quality issues are documented in the pipeline manifest and never silently discarded.</p>
    </div>
  );
}
