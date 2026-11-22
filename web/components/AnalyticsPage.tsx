'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useApiQuery, useKpis } from '@/lib/api';
import { useFilters } from '@/lib/filters';
import { usePageFilters } from '@/lib/page-filters';
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

function ChartPanel({ config, tableEndpoint, filters, params }: { config: ChartConfig; tableEndpoint?: string; filters: FilterState; params: Record<string, string> }) {
  const query = useApiQuery<unknown>(`chart-${config.endpoint}`, config.endpoint, filters, params);
  const drillable = tableEndpoint ? { ...config, drilldownEndpoint: config.drilldownEndpoint ?? tableEndpoint } : config;
  return (
    <div className={cn(config.span === 2 && 'xl:col-span-2')}>
      <ChartContainer config={drillable} data={query.data?.data} loading={query.isLoading} error={query.error} onRetry={() => query.refetch()} />
    </div>
  );
}

function ProfileHeader({ endpoint, params }: { endpoint: string; params: Record<string, string> }) {
  const { filters } = useFilters();
  const query = useApiQuery<TableRow>(`profile-${endpoint}`, endpoint, filters, params);
  if (query.isLoading) return <Skeleton className="h-28 w-full" />;
  if (query.isError || !query.data?.data) return null;
  const raw = query.data.data as Record<string, unknown>;
  const nested = (raw.hospital && typeof raw.hospital === 'object' ? raw.hospital : raw) as Record<string, unknown>;
  const profile = { ...nested, ...raw } as Record<string, unknown>;
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
  ].filter((entry): entry is [string, string] => Boolean(entry[1]) && entry[1] !== 'undefined' && entry[1] !== '');

  return (
    <Card className="p-5" data-testid="hospital-profile-header">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-navy">{title}</h2>
          <p className="mt-0.5 text-xs text-slate-600">Synthetic hospital record from the API</p>
        </div>
        {status && <Badge tone="info">{status}</Badge>}
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-7">
        {fields.map(([label, value]) => (
          <div key={label}>
            <dt className="text-[10px] font-semibold uppercase tracking-wide text-slate-600">{label}</dt>
            <dd className="mt-1 truncate text-xs font-medium text-ink">{displayValue(value)}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

function ComparisonControls() {
  const { params, setPageParam } = usePageFilters();
  const metric = params.metric || 'revenue';
  const rankSort = params.rank_sort || 'desc';
  return (
    <Card className="p-4" data-testid="comparison-controls">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-600">Comparison metric</label>
          <select value={metric} onChange={(e) => setPageParam('metric', e.target.value)} className="h-9 rounded-md border border-line px-3 text-xs" data-testid="comparison-metric">
            <option value="revenue">Revenue</option>
            <option value="patient_volume">Patient volume</option>
            <option value="occupancy">Occupancy</option>
            <option value="los">Length of stay</option>
            <option value="satisfaction">Satisfaction</option>
            <option value="denial_rate">Claim denial rate</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-600">Ranking sort</label>
          <select value={rankSort} onChange={(e) => setPageParam('rank_sort', e.target.value)} className="h-9 rounded-md border border-line px-3 text-xs" data-testid="comparison-sort">
            <option value="desc">Highest first</option>
            <option value="asc">Lowest first</option>
          </select>
        </div>
        <p className="text-[11px] text-slate-600">Use global hospital filters to select up to 10 hospitals for comparison. Click a hospital row to open its profile.</p>
      </div>
    </Card>
  );
}

export function AnalyticsPage({ config }: { config: PageConfig }) {
  const router = useRouter();
  const { filters, compare } = useFilters();
  const { params: pageParams } = usePageFilters();
  const [activeTab, setActiveTab] = useState(config.tabs?.[0]?.id || '');
  const kpiQuery = useKpis(config.kpiEndpoint, filters, { ...pageParams, ...(compare ? { previous: 'true' } : {}) });
  const glossaryQuery = useApiQuery<unknown>('kpi-glossary', '/kpis/glossary', { ...filters, date_from: '', date_to: '', hospital_ids: [], department_id: '', specialty_id: '', payer_id: '', encounter_type: '', patient_type: '' });
  const definitions = useMemo(() => glossaryDefinitions(glossaryQuery.data?.data), [glossaryQuery.data]);

  const kpiData: KpiMap | undefined = kpiQuery.data?.data && typeof kpiQuery.data.data === 'object' ? (kpiQuery.data.data as KpiMap) : undefined;
  const ids = useMemo(() => {
    if (!kpiData) return config.kpiIds.slice(0, 6);
    const configured = config.kpiIds.filter((id) => kpiData[id] !== undefined && kpiData[id] !== null);
    return configured.length ? configured : Object.keys(kpiData).slice(0, 12);
  }, [kpiData, config.kpiIds]);

  const activeTabConfig = config.tabs?.find((t) => t.id === activeTab) || config.tabs?.[0];
  const visibleCharts = useMemo(() => {
    if (!activeTabConfig?.chartTitles) return config.charts;
    const set = new Set(activeTabConfig.chartTitles);
    return config.charts.filter((c) => set.has(c.title));
  }, [config.charts, activeTabConfig]);
  const showTable = !activeTabConfig || activeTabConfig.showTable !== false;
  const showKpis = !activeTabConfig || activeTabConfig.showKpis !== false;

  const onHospitalRowClick = config.slug === 'hospitals'
    ? (row: TableRow) => {
        const id = String(row.hospital_id || row.id || '');
        if (id) router.push(`/hospitals/${encodeURIComponent(id)}`);
      }
    : undefined;

  return (
    <div className="space-y-6">
      <PageHeading title={config.title} description={config.description} badge={<Badge tone="info">{config.navGroup}</Badge>} />
      {config.profileEndpoint && <ProfileHeader endpoint={config.profileEndpoint} params={pageParams} />}

      {config.tabs && config.tabs.length > 0 && (
        <div className="flex flex-wrap gap-2 border-b border-line pb-2" data-testid="profile-tabs">
          {config.tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={cn('rounded-md px-3 py-1.5 text-xs font-medium', activeTab === tab.id ? 'bg-teal-light/40 text-teal-dark' : 'text-slate-600 hover:text-navy')}
              data-testid={`tab-${tab.id}`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {config.slug === 'hospitals' && <ComparisonControls />}

      {config.kpiEndpoint && showKpis && (
        <section aria-label="Key performance indicators">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-600">Key indicators</h2>
            <span className="text-[11px] text-slate-600">Values from {config.kpiEndpoint}</span>
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

      {visibleCharts.length > 0 && (
        <section aria-label="Charts">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-600">Analytics</h2>
            <span className="text-[11px] text-slate-600">Hover for detail, click a point to drill down</span>
          </div>
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            {visibleCharts.map((chartConfig) => (
              <ChartPanel key={`${chartConfig.title}-${chartConfig.endpoint}`} config={chartConfig} tableEndpoint={config.tableEndpoint} filters={filters} params={pageParams} />
            ))}
          </div>
        </section>
      )}

      {config.tableEndpoint && showTable && (
        <section aria-label="Records">
          <DataTable endpoint={config.tableEndpoint} columns={config.tableColumns} filters={filters} params={pageParams} exportName={config.slug} onRowClick={onHospitalRowClick} />
        </section>
      )}
    </div>
  );
}
