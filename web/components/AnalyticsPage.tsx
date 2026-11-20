'use client';

import { useMemo } from 'react';
import { useApiQuery, useKpis } from '@/lib/api';
import { useFilters } from '@/lib/filters';
import { kpiRoute } from '@/lib/page-configs';
import type { ChartConfig, FilterState, KpiMap, PageConfig, TableRow } from '@/lib/types';
import { cn, displayValue } from '@/lib/utils';
import { ChartContainer } from './ChartContainer';
import { DataTable } from './DataTable';
import { KpiCard } from './KpiCard';
import { Badge, Card, ErrorState, PageHeading, Skeleton } from './ui';

function glossaryDefinitions(data: unknown): Record<string, string> {
  const result: Record<string, string> = {};
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    const array = Object.values(data as Record<string, unknown>).find(Array.isArray);
    if (array) data = array;
  }
  if (Array.isArray(data)) {
    data.forEach((row) => {
      if (!row || typeof row !== 'object') return;
      const item = row as Record<string, unknown>;
      const id = item.kpi_id ?? item.id ?? item.kpiId;
      const definition = item.definition ?? item.business_definition ?? item.description;
      if (id && typeof definition === 'string') result[String(id)] = definition;
    });
  } else if (data && typeof data === 'object') {
    Object.entries(data as Record<string, unknown>).forEach(([id, value]) => {
      if (typeof value === 'string') result[id] = value;
      else if (value && typeof value === 'object') {
        const item = value as Record<string, unknown>;
        const definition = item.definition ?? item.business_definition ?? item.description;
        if (typeof definition === 'string') result[id] = definition;
      }
    });
  }
  return result;
}

function ChartPanel({ config, filters }: { config: ChartConfig; filters: FilterState }) {
  const query = useApiQuery<unknown>(`chart-${config.endpoint}`, config.endpoint, filters);
  return (
    <div className={cn(config.span === 2 && 'xl:col-span-2')}>
      <ChartContainer config={config} data={query.data?.data} loading={query.isLoading} error={query.error} onRetry={() => query.refetch()} />
    </div>
  );
}

function ProfileHeader({ endpoint }: { endpoint: string }) {
  const { filters } = useFilters();
  const query = useApiQuery<TableRow>(`profile-${endpoint}`, endpoint, filters);
  if (query.isLoading) return <Skeleton className="h-28 w-full" />;
  if (query.isError || !query.data?.data) return null;
  const profile = query.data.data;
  const title = String(profile.hospital_name ?? profile.name ?? 'Hospital profile');
  const status = String(profile.status ?? '');
  const fields: Array<[string, string]> = [
    ['Hospital', String(profile.hospital_name ?? profile.name ?? '')],
    ['ID', String(profile.hospital_id ?? profile.id ?? '')],
    ['Location', String(profile.city ?? profile.location ?? profile.address ?? '')],
    ['Type', String(profile.hospital_type ?? profile.type ?? profile.profile ?? '')],
    ['Beds', String(profile.beds ?? profile.bed_capacity ?? profile.total_beds ?? '')],
    ['Specialties', String(profile.specialty_count ?? profile.departments ?? '')],
    ['Status', status],
  ].filter((entry): entry is [string, string] => Boolean(entry[1]) && entry[1] !== 'undefined');

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-navy">{title}</h2>
          <p className="mt-0.5 text-xs text-slate-500">Synthetic hospital record from the API</p>
        </div>
        {status && <Badge tone="info">{status}</Badge>}
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-7">
        {fields.map(([label, value]) => (
          <div key={label}>
            <dt className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</dt>
            <dd className="mt-1 truncate text-xs font-medium text-ink">{displayValue(value)}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

export function AnalyticsPage({ config }: { config: PageConfig }) {
  const { filters } = useFilters();
  const kpiQuery = useKpis(config.kpiEndpoint, filters);
  const glossaryQuery = useApiQuery<unknown>('kpi-glossary', '/kpis/glossary', { ...filters, date_from: '', date_to: '', hospital_ids: [], department_id: '', specialty_id: '', payer_id: '', encounter_type: '', patient_type: '' });
  const definitions = useMemo(() => glossaryDefinitions(glossaryQuery.data?.data), [glossaryQuery.data]);

  const kpiData: KpiMap | undefined = kpiQuery.data?.data && typeof kpiQuery.data.data === 'object' ? (kpiQuery.data.data as KpiMap) : undefined;
  const ids = useMemo(() => {
    if (!kpiData) return config.kpiIds.slice(0, 6);
    const configured = config.kpiIds.filter((id) => kpiData[id] !== undefined && kpiData[id] !== null);
    return configured.length ? configured : Object.keys(kpiData).slice(0, 12);
  }, [kpiData, config.kpiIds]);

  return (
    <div className="space-y-6">
      <PageHeading title={config.title} description={config.description} badge={<Badge tone="info">{config.navGroup}</Badge>} />
      {config.profileEndpoint && <ProfileHeader endpoint={config.profileEndpoint} />}

      {config.kpiEndpoint && (
        <section aria-label="Key performance indicators">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Key indicators</h2>
            <span className="text-[11px] text-slate-400">Values from {config.kpiEndpoint}</span>
          </div>
          {kpiQuery.isError ? (
            <Card><ErrorState message={kpiQuery.error?.message || 'KPIs could not be loaded.'} onRetry={() => kpiQuery.refetch()} /></Card>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
              {kpiQuery.isLoading
                ? ids.map((id) => <Skeleton key={id} className="h-[148px] w-full" />)
                : ids.map((id) => (
                    <KpiCard
                      key={id}
                      kpiId={id}
                      item={kpiData?.[id]}
                      definition={definitions[id]}
                      route={kpiRoute(id, config.path)}
                    />
                  ))}
            </div>
          )}
        </section>
      )}

      {config.charts.length > 0 && (
        <section aria-label="Charts">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Analytics</h2>
            <span className="text-[11px] text-slate-400">Hover for detail · click a point to drill down</span>
          </div>
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            {config.charts.map((chartConfig) => (
              <ChartPanel key={`${chartConfig.title}-${chartConfig.endpoint}`} config={chartConfig} filters={filters} />
            ))}
          </div>
        </section>
      )}

      {config.tableEndpoint && (
        <section aria-label="Records">
          <DataTable endpoint={config.tableEndpoint} columns={config.tableColumns} filters={filters} exportName={config.slug} />
        </section>
      )}
    </div>
  );
}
