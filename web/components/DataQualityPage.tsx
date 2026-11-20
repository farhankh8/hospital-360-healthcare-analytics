'use client';

import { useMemo } from 'react';
import { ShieldCheck } from 'lucide-react';
import { useApiQuery } from '@/lib/api';
import { useFilters } from '@/lib/filters';
import { NO_FILTERS, type ChartConfig, type TableRow } from '@/lib/types';
import { displayValue } from '@/lib/utils';
import { ChartContainer } from './ChartContainer';
import { DataTable } from './DataTable';
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
];

function DqChart({ config }: { config: ChartConfig }) {
  const query = useApiQuery<unknown>(`dq-chart-${config.endpoint}`, config.endpoint, NO_FILTERS);
  return (
    <div className={config.span === 2 ? 'xl:col-span-2' : undefined}>
      <ChartContainer config={config} data={query.data?.data} loading={query.isLoading} error={query.error} onRetry={() => query.refetch()} />
    </div>
  );
}

function summaryFields(data: unknown): Array<[string, unknown]> {
  if (Array.isArray(data)) {
    const first = data[0];
    return first && typeof first === 'object' ? Object.entries(first as TableRow) : [];
  }
  if (data && typeof data === 'object') return Object.entries(data as Record<string, unknown>);
  return [];
}

export function DataQualityPage() {
  const { filters } = useFilters();
  const summaryQuery = useApiQuery<unknown>('dq-summary', '/data-quality/summary', filters);
  const summary = useMemo(() => summaryFields(summaryQuery.data?.data).filter(([, value]) => value !== null && value !== undefined && typeof value !== 'object').slice(0, 12), [summaryQuery.data]);

  return (
    <div className="space-y-6">
      <PageHeading title="Data Quality" description="Validation rules, detected failures and dataset-level quality indicators." badge={<Badge tone="info">Engineering</Badge>} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {summaryQuery.isLoading && Array.from({ length: 8 }).map((_item, index) => <Skeleton key={index} className="h-20 w-full" />)}
        {summaryQuery.isError && <Card className="col-span-full"><ErrorState message={summaryQuery.error?.message || 'Quality summary unavailable'} onRetry={() => summaryQuery.refetch()} /></Card>}
        {!summaryQuery.isLoading && !summaryQuery.isError && summary.length === 0 && <Card className="col-span-full"><EmptyState message="No summary values returned" /></Card>}
        {summary.map(([key, value]) => (
          <Card key={key} className="p-4">
            <p className="truncate text-[10px] font-semibold uppercase tracking-wide text-slate-400">{key.replace(/_/g, ' ')}</p>
            <p className="mt-2 truncate text-xl font-semibold text-navy">{displayValue(value)}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-2">
        {DQ_CHARTS.map((config) => <DqChart key={config.endpoint} config={config} />)}
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <DataTable
          endpoint="/data-quality/datasets"
          filters={filters}
          title="Datasets"
          exportName="dq-datasets"
          columns={[
            { key: 'dataset', title: 'Dataset', sortable: true },
            { key: 'records', title: 'Records', type: 'number', sortable: true },
            { key: 'valid_records', title: 'Valid', type: 'number', sortable: true },
            { key: 'invalid_records', title: 'Invalid', type: 'number', sortable: true },
            { key: 'quality_score', title: 'Quality score', type: 'number', sortable: true },
            { key: 'status', title: 'Status', type: 'badge', sortable: true },
          ]}
        />
        <DataTable
          endpoint="/data-quality/rules"
          filters={filters}
          title="Validation rules"
          exportName="dq-rules"
          primaryExport={false}
          columns={[
            { key: 'rule_id', title: 'Rule ID', sortable: true },
            { key: 'rule_name', title: 'Rule', sortable: true },
            { key: 'dataset', title: 'Dataset', sortable: true },
            { key: 'severity', title: 'Severity', type: 'badge', sortable: true },
            { key: 'description', title: 'Description', sortable: true },
            { key: 'status', title: 'Status', type: 'badge', sortable: true },
          ]}
        />
      </div>

      <DataTable
        endpoint="/data-quality/failures"
        filters={filters}
        title="Validation failures"
        exportName="dq-failures"
        primaryExport={false}
        columns={[
          { key: 'validation_id', title: 'Validation ID', sortable: true },
          { key: 'dataset', title: 'Dataset', sortable: true },
          { key: 'record_id', title: 'Record ID', sortable: true },
          { key: 'rule_id', title: 'Rule', sortable: true },
          { key: 'failure_reason', title: 'Failure reason', sortable: true },
          { key: 'severity', title: 'Severity', type: 'badge', sortable: true },
          { key: 'detected_at', title: 'Detected', type: 'date', sortable: true },
          { key: 'run_id', title: 'Pipeline run', sortable: true },
          { key: 'resolution_status', title: 'Resolution', type: 'badge', sortable: true },
        ]}
      />

      <p className="flex items-center gap-2 text-[11px] text-slate-400"><ShieldCheck className="h-3.5 w-3.5" /> Intentional quality issues are documented in the pipeline manifest and never silently discarded.</p>
    </div>
  );
}
