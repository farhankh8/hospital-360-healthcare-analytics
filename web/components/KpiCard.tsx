'use client';

import { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { Info } from 'lucide-react';
import type { EChartsOption } from 'echarts';
import { useFilters } from '@/lib/filters';
import { changeTone, formatChange, formatValue, isLowerBetter, kpiLabel } from '@/lib/format';
import type { KpiValue } from '@/lib/types';
import { cn, routeWithFilters, toNumber } from '@/lib/utils';
import { Card, Delta, EmptyState, ErrorState, Skeleton } from './ui';

const EChart = dynamic(() => import('./EChart'), { ssr: false, loading: () => <Skeleton className="h-10 w-full" /> });

const SNAPSHOT_KPIS = new Set(['hospitals_selected', 'total_beds', 'active_employees']);

interface KpiCardProps {
  kpiId: string;
  item?: KpiValue;
  loading?: boolean;
  error?: Error | null;
  definition?: string;
  route?: string;
  onRetry?: () => void;
}

export function KpiCard({ kpiId, item, loading, error, definition, route, onRetry }: KpiCardProps) {
  const router = useRouter();
  const { filters } = useFilters();
  const lowerIsBetter = isLowerBetter(kpiId, item);
  const tone = changeTone(item?.change_pct, lowerIsBetter);
  const unit = item?.unit;

  const sparkOption = useMemo<EChartsOption>(() => {
    const data = Array.isArray(item?.sparkline) ? (item?.sparkline as number[]) : [];
    const colour = tone === 'negative' ? '#EF4444' : tone === 'positive' ? '#22C55E' : '#14B8A6';
    return {
      animation: false,
      grid: { left: 0, right: 0, top: 4, bottom: 0 },
      xAxis: { type: 'category', show: false, data: data.map((_value, index) => index) },
      yAxis: { type: 'value', show: false, scale: true },
      tooltip: {
        trigger: 'axis',
        confine: true,
        backgroundColor: 'rgba(15,23,42,0.92)',
        borderWidth: 0,
        padding: [4, 8],
        textStyle: { color: '#F8FAFC', fontSize: 11 },
        formatter: (params: unknown) => {
          const list = params as Array<{ data: number }>;
          return String(list?.[0]?.data ?? '');
        },
      },
      series: [
        {
          type: 'line',
          data,
          smooth: 0.35,
          showSymbol: false,
          lineStyle: { width: 1.75, color: colour },
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: `${colour}33` }, { offset: 1, color: `${colour}00` }],
            },
          },
        },
      ],
    } as EChartsOption;
  }, [item?.sparkline, tone]);

  if (loading) {
    return (
      <Card className="relative overflow-hidden p-4">
        <div className="absolute inset-y-0 left-0 w-[2px] bg-teal/30" />
        <Skeleton className="h-3 w-24" />
        <Skeleton className="mt-4 h-8 w-32" />
        <Skeleton className="mt-4 h-9 w-full" />
      </Card>
    );
  }

  if (error) return <Card className="p-2"><ErrorState message="KPI unavailable" onRetry={onRetry} /></Card>;
  if (!item) return <Card className="p-2"><EmptyState message="No value returned" hint="This KPI is not present in the API response." /></Card>;

  const dateUnavailable = item.date_filter_available === false || SNAPSHOT_KPIS.has(kpiId);
  const note = item.date_filter_note || 'Date filter unavailable: this is a snapshot KPI with no date field.';
  const tooltipText = `${definition || item.definition || 'Definition not available in the KPI glossary.'}${dateUnavailable ? ` ${note}` : ''}`;
  const railColor = tone === 'positive' ? 'bg-success' : tone === 'negative' ? 'bg-critical' : 'bg-teal/60';

  return (
    <Card
      data-testid={`kpi-${kpiId}`}
      className={cn(
        'group relative flex min-h-[152px] flex-col justify-between overflow-hidden p-4 transition-all duration-200',
        route && 'cursor-pointer hover:-translate-y-[1px] hover:border-teal/40 hover:shadow-pop',
      )}
      onClick={route ? () => router.push(routeWithFilters(route, filters)) : undefined}
      role={route ? 'link' : undefined}
      tabIndex={route ? 0 : undefined}
      onKeyDown={route ? (event) => event.key === 'Enter' && router.push(routeWithFilters(route, filters)) : undefined}
    >
      <div className={cn('absolute inset-y-3 left-0 w-[2px] rounded-r', railColor)} aria-hidden="true" />
      <div className="flex items-start justify-between gap-2 pl-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <p className="truncate text-[11px] font-medium uppercase tracking-wide text-muted">{kpiLabel(kpiId, item)}</p>
          {dateUnavailable && (
            <span className="shrink-0 rounded-sm border border-line bg-surface-alt px-1.5 py-0.5 text-[9px] font-medium text-muted">
              No date filter
            </span>
          )}
          <span className="group/tooltip relative">
            <Info className="h-3.5 w-3.5 shrink-0 text-muted-soft" aria-hidden="true" />
            <span className="pointer-events-none absolute bottom-5 left-1/2 z-50 hidden w-60 -translate-x-1/2 rounded-md bg-slate-900 px-3 py-2 text-[11px] font-normal leading-relaxed text-slate-100 shadow-pop group-hover/tooltip:block dark:bg-slate-700">
              {tooltipText}
            </span>
          </span>
        </div>
        <span className="text-[10px] uppercase tracking-wide text-muted-soft">{unit || 'value'}</span>
      </div>

      <div className="mt-3 flex items-end gap-3 pl-2">
        <div className="min-w-0">
          <p data-testid="metric-value" className="truncate text-kpi-sm font-semibold tracking-tight text-ink-strong tabular-nums">{formatValue(item.value, unit)}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px]">
            <Delta
              tone={tone}
              value={`${tone === 'positive' ? '↑' : tone === 'negative' ? '↓' : '→'} ${formatChange(item.change_pct)}`}
            />
            {(() => {
              const currentNum = toNumber(item.value);
              const prevNum = toNumber(item.previous);
              if (currentNum === null || prevNum === null) return null;
              const delta = currentNum - prevNum;
              const sign = delta > 0 ? '+' : delta < 0 ? '-' : '';
              return <span className="text-muted tabular-nums">{sign}{formatValue(Math.abs(delta), unit)} abs</span>;
            })()}
            <span className="text-muted">vs previous</span>
            {item.previous !== undefined && item.previous !== null && (
              <span className="text-muted tabular-nums">({formatValue(item.previous, unit)})</span>
            )}
          </div>
        </div>
        {Array.isArray(item.sparkline) && item.sparkline.length > 1 && (
          <div className="ml-auto h-10 w-24 shrink-0 opacity-90">
            <EChart option={sparkOption} height={40} />
          </div>
        )}
      </div>
    </Card>
  );
}
