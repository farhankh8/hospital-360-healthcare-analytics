'use client';

import { useMemo } from 'react';
import dynamic from 'next/dynamic';
import { Download, LockKeyhole } from 'lucide-react';
import { buildChartOption } from '@/lib/chart';
import { useFilters } from '@/lib/filters';
import { useDrilldown } from './DrilldownDrawer';
import type { ChartConfig, TableRow } from '@/lib/types';
import { downloadCsv } from '@/lib/utils';
import { Badge, Card, CardHeader, EmptyState, ErrorState, Skeleton } from './ui';

const EChart = dynamic(() => import('./EChart'), { ssr: false, loading: () => <Skeleton className="h-full w-full" /> });

interface ChartContainerProps {
  config: ChartConfig;
  data?: unknown;
  loading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
}

export function ChartContainer({ config, data, loading, error, onRetry }: ChartContainerProps) {
  const { openDrilldown } = useDrilldown();
  const { setFilter } = useFilters();
  const built = useMemo(() => buildChartOption(config, data), [config, data]);

  const handleClick = (params: Record<string, unknown>) => {
    const raw = params.data;
    const value = Array.isArray(raw) ? raw[raw.length - 1] : typeof raw === 'object' && raw !== null ? (raw as TableRow).value : raw;
    const record: TableRow = {
      category: params.name ?? (raw as TableRow)?.name,
      series: params.seriesName ?? (raw as TableRow)?.series,
      value,
      chart: config.title,
    };
    if (config.drilldownEndpoint) record.endpoint = config.drilldownEndpoint;
    openDrilldown(record, config.title);
  };

  const handleZoom = (params: Record<string, unknown>) => {
    const batch = Array.isArray(params.batch) ? (params.batch as Array<Record<string, unknown>>) : [params];
    const event = batch[0] || {};
    const start = event.startValue;
    const end = event.endValue;
    const categories = built.categories;
    const toDate = (value: unknown) => {
      if (typeof value === 'number' && categories[value]) return categories[value];
      if (typeof value === 'string') return value;
      return '';
    };
    const from = toDate(start);
    const to = toDate(end);
    if (/^\d{4}-\d{2}-\d{2}/.test(from) && /^\d{4}-\d{2}-\d{2}/.test(to)) {
      setFilter('date_from', from.slice(0, 10));
      setFilter('date_to', to.slice(0, 10));
    }
  };

  const download = () => {
    const rows = built.rows.map((row) =>
      Object.keys(row).reduce<TableRow>((accumulator, key) => {
        accumulator[key] = row[key];
        return accumulator;
      }, {}),
    );
    downloadCsv(`${config.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.csv`, rows);
  };

  const body = loading ? (
    <div className="space-y-2 p-5">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-[260px] w-full" />
    </div>
  ) : error ? (
    <ErrorState message={error.message || 'Unable to load chart data.'} onRetry={onRetry} />
  ) : built.rows.length === 0 ? (
    <EmptyState message="No chart data" hint="The API returned no rows for the active filters." />
  ) : (
    <EChart option={built.option} height={config.height ?? 320} onClick={handleClick} onDataZoom={handleZoom} />
  );

  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader
        title={config.title}
        subtitle={config.description}
        action={
          <>
            {config.unfilteredBenchmark && (
              <Badge tone="warning">
                <LockKeyhole className="mr-1 h-3 w-3" /> Unfiltered benchmark
              </Badge>
            )}
            <button
              type="button"
              onClick={download}
              disabled={!built.rows.length}
              title="Download chart data as CSV"
              className="inline-flex h-7 w-7 items-center justify-center rounded border border-line text-slate-500 transition hover:border-teal hover:text-teal disabled:opacity-40"
            >
              <Download className="h-3.5 w-3.5" />
            </button>
          </>
        }
      />
      <div className="min-h-[280px] flex-1">{body}</div>
    </Card>
  );
}
