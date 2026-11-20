'use client';

import { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { ArrowDownRight, ArrowUpRight, Info, Minus } from 'lucide-react';
import type { EChartsOption } from 'echarts';
import { useFilters } from '@/lib/filters';
import { changeTone, formatChange, formatValue, isLowerBetter, kpiLabel } from '@/lib/format';
import type { KpiValue } from '@/lib/types';
import { cn, routeWithFilters } from '@/lib/utils';
import { Card, EmptyState, ErrorState, Skeleton } from './ui';

const EChart = dynamic(() => import('./EChart'), { ssr: false, loading: () => <Skeleton className="h-10 w-full" /> });

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
    const colour = tone === 'negative' ? '#C0392B' : tone === 'positive' ? '#16803C' : '#0E9384';
    return {
      animation: false,
      grid: { left: 0, right: 0, top: 3, bottom: 0 },
      xAxis: { type: 'category', show: false, data: data.map((_value, index) => index) },
      yAxis: { type: 'value', show: false, scale: true },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#0B2545',
        borderWidth: 0,
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
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 2, color: colour },
          areaStyle: { color: colour, opacity: 0.1 },
        },
      ],
    } as EChartsOption;
  }, [item?.sparkline, tone]);

  if (loading) {
    return (
      <Card className="p-4">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="mt-4 h-8 w-32" />
        <Skeleton className="mt-4 h-8 w-full" />
      </Card>
    );
  }

  if (error) return <Card className="p-2"><ErrorState message="KPI unavailable" onRetry={onRetry} /></Card>;
  if (!item) return <Card className="p-2"><EmptyState message="No value returned" hint="This KPI is not present in the API response." /></Card>;

  const ChangeIcon = tone === 'positive' ? ArrowUpRight : tone === 'negative' ? ArrowDownRight : Minus;
  const tooltipText = definition || item.definition || 'Definition not available in the KPI glossary.';

  return (
    <Card
      data-testid={`kpi-${kpiId}`}
      className={cn('group relative flex min-h-[148px] flex-col justify-between p-4 transition', route && 'cursor-pointer hover:border-teal hover:shadow-md')}
      onClick={route ? () => router.push(routeWithFilters(route, filters)) : undefined}
      role={route ? 'link' : undefined}
      tabIndex={route ? 0 : undefined}
      onKeyDown={route ? (event) => event.key === 'Enter' && router.push(routeWithFilters(route, filters)) : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <p className="truncate text-xs font-medium text-slate-500">{kpiLabel(kpiId, item)}</p>
          <span className="group/tooltip relative">
            <Info className="h-3.5 w-3.5 shrink-0 text-slate-300" aria-hidden="true" />
            <span className="pointer-events-none absolute bottom-5 left-1/2 z-50 hidden w-56 -translate-x-1/2 rounded-md bg-navy px-2.5 py-2 text-[11px] font-normal leading-relaxed text-white shadow-lg group-hover/tooltip:block">
              {tooltipText}
            </span>
          </span>
        </div>
        <span className="text-[10px] uppercase tracking-wide text-slate-300">{unit || 'value'}</span>
      </div>

      <div className="mt-3 flex items-end gap-3">
        <div className="min-w-0">
          <p data-testid="metric-value" className="truncate text-2xl font-semibold tracking-tight text-navy">{formatValue(item.value, unit)}</p>
          <div className="mt-1 flex items-center gap-1.5 text-[11px]">
            <span className={cn('inline-flex items-center gap-0.5 font-semibold', tone === 'positive' ? 'text-success' : tone === 'negative' ? 'text-critical' : 'text-slate-400')}>
              <ChangeIcon className="h-3.5 w-3.5" />
              {formatChange(item.change_pct)}
            </span>
            <span className="text-slate-400">vs previous</span>
            {item.previous !== undefined && item.previous !== null && (
              <span className="text-slate-400">({formatValue(item.previous, unit)})</span>
            )}
          </div>
        </div>
        {Array.isArray(item.sparkline) && item.sparkline.length > 1 && (
          <div className="ml-auto h-10 w-24 shrink-0">
            <EChart option={sparkOption} height={40} />
          </div>
        )}
      </div>
    </Card>
  );
}
