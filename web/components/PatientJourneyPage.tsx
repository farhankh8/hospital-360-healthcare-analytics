'use client';

import { useMemo, useState, type FormEvent } from 'react';
import { useQueries } from '@tanstack/react-query';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Route as RouteIcon, Search, UserRound } from 'lucide-react';
import { apiGet, useApiQuery } from '@/lib/api';
import { NO_FILTERS, type TableRow } from '@/lib/types';
import { displayValue } from '@/lib/utils';
import { useDrilldown } from './DrilldownDrawer';
import { Badge, Card, CardHeader, EmptyState, ErrorState, PageHeading, Skeleton } from './ui';

const DATE_HINTS = ['date', '_at', 'time', 'month'];

function firstDate(row: TableRow): [string, string] | null {
  const entry = Object.entries(row).find(([key, value]) => DATE_HINTS.some((hint) => key.toLowerCase().includes(hint)) && value !== null && value !== undefined && value !== '');
  return entry ? [entry[0], String(entry[1])] : null;
}

export function PatientJourneyPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { openDrilldown } = useDrilldown();
  const patientId = searchParams.get('patient_id') || '';
  const [input, setInput] = useState(patientId);
  const [datasetFilter, setDatasetFilter] = useState('');

  const datasetsQuery = useApiQuery<unknown>('journey-datasets', '/explorer/datasets', NO_FILTERS);
  const datasets = useMemo(() => {
    const data = datasetsQuery.data?.data;
    const list = Array.isArray(data) ? data : data && typeof data === 'object' ? (Object.values(data as Record<string, unknown>).find(Array.isArray) as unknown[]) || [] : [];
    return list
      .map((item) => {
        if (typeof item === 'string') return { value: item, label: item.replace(/_/g, ' ') };
        if (item && typeof item === 'object') {
          const row = item as Record<string, unknown>;
          const value = String(row.dataset_name ?? row.name ?? row.id ?? row.table_name ?? row.dataset ?? '');
          return value ? { value, label: String(row.label ?? row.display_name ?? value.replace(/_/g, ' ')) } : null;
        }
        return null;
      })
      .filter((item): item is { value: string; label: string } => Boolean(item));
  }, [datasetsQuery.data]);

  const results = useQueries({
    queries: datasets.map((dataset) => ({
      queryKey: ['patient-journey', dataset.value, patientId],
      queryFn: ({ signal }: { signal: AbortSignal }) =>
        apiGet<TableRow[]>(`/explorer/${encodeURIComponent(dataset.value)}/records`, NO_FILTERS, { params: { search: patientId, page_size: 500 }, signal }),
      enabled: Boolean(patientId),
      staleTime: 60_000,
    })),
  });

  const events = useMemo(
    () =>
      results
        .flatMap((result, index) => {
          const rows = Array.isArray(result.data?.data) ? result.data.data : [];
          return rows.map((row) => ({ row, dataset: datasets[index]?.label || datasets[index]?.value || '', datasetKey: datasets[index]?.value || '' }));
        })
        .map((item) => ({ ...item, date: firstDate(item.row) }))
        .filter((item) => item.date)
        .sort((a, b) => (a.date?.[1] || '').localeCompare(b.date?.[1] || '')),
    [results, datasets],
  );

  const visibleEvents = useMemo(
    () => (datasetFilter ? events.filter((event) => event.datasetKey === datasetFilter || event.dataset === datasetFilter) : events),
    [events, datasetFilter],
  );

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    events.forEach((event) => map.set(event.datasetKey, (map.get(event.datasetKey) || 0) + 1));
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1]);
  }, [events]);

  const totals = useMemo(() => {
    let billed = 0;
    let paid = 0;
    events.forEach(({ row, datasetKey }) => {
      if (!/invoice|billing|claim|payment/i.test(datasetKey)) return;
      Object.entries(row).forEach(([key, value]) => {
        const numeric = typeof value === 'number' ? value : typeof value === 'string' && value.trim() !== '' && !Number.isNaN(Number(value)) ? Number(value) : null;
        if (numeric === null) return;
        if (/billed|gross|claimed_amount|net_amount|amount/i.test(key)) billed += numeric;
        if (/paid_amount|collected|paid/i.test(key)) paid += numeric;
      });
    });
    return { billed, paid };
  }, [events]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!input.trim()) return;
    setDatasetFilter('');
    const params = new URLSearchParams(searchParams.toString());
    params.set('patient_id', input.trim());
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const isLoading = datasetsQuery.isLoading || (Boolean(patientId) && results.some((result) => result.isLoading));
  const hasError = datasetsQuery.isError || results.some((result) => result.isError);

  return (
    <div className="space-y-6">
      <PageHeading title="Patient Journey" description="Follow one synthetic identity through encounters, tests, billing and feedback." badge={<Badge tone="info">Synthetic identity</Badge>} />

      <Card className="p-5">
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
          <div className="min-w-[300px] flex-1">
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-400">Patient / encounter / admission ID</label>
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="e.g. PAT000123, ENC000456 or ADM000789"
                data-testid="journey-search"
                className="h-9 w-full rounded-md border border-line pl-9 pr-3 text-xs outline-none focus:border-teal focus:ring-2 focus:ring-teal/15"
              />
            </div>
          </div>
          <button type="submit" className="h-9 rounded-md bg-navy px-4 text-xs font-medium text-white hover:bg-navy-light">View journey</button>
        </form>
        <p className="mt-3 text-[11px] text-slate-400">The search runs across all {datasets.length} record datasets and is not limited by the global date range.</p>
      </Card>

      {!patientId && <Card><EmptyState message="Enter a synthetic ID" hint="All identities in this project are synthetic." /></Card>}
      {hasError && <Card><ErrorState message="Journey records could not be loaded." /></Card>}
      {patientId && isLoading && <Card className="p-5"><Skeleton className="h-48 w-full" /></Card>}

      {patientId && !isLoading && !hasError && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="p-4"><p className="text-[10px] uppercase tracking-wide text-slate-400">Synthetic ID</p><p className="mt-1 text-lg font-semibold text-navy">{patientId}</p></Card>
            <Card className="p-4"><p className="text-[10px] uppercase tracking-wide text-slate-400">Timeline events</p><p className="mt-1 text-lg font-semibold text-navy">{events.length}</p></Card>
            <Card className="p-4"><p className="text-[10px] uppercase tracking-wide text-slate-400">Billed (invoices/claims)</p><p className="mt-1 text-lg font-semibold text-navy">${totals.billed.toLocaleString('en-US')}</p></Card>
            <Card className="p-4"><p className="text-[10px] uppercase tracking-wide text-slate-400">Paid (invoices/claims)</p><p className="mt-1 text-lg font-semibold text-navy">${totals.paid.toLocaleString('en-US')}</p></Card>
          </div>

          {events.length === 0 ? (
            <Card><EmptyState message="No journey records found" hint="The API returned no records for this synthetic ID." /></Card>
          ) : (
            <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
              <Card className="xl:col-span-2">
                <CardHeader title="Timeline" subtitle={`${visibleEvents.length} dated events`} action={<RouteIcon className="h-4 w-4 text-teal" />} />
                <ol className="max-h-[720px] space-y-0 overflow-y-auto px-5 py-4">
                  {visibleEvents.map((event, index) => (
                    <li key={index} className="relative border-l border-line pb-5 pl-6 last:pb-0">
                      <span className="absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-teal" />
                      <button type="button" onClick={() => openDrilldown(event.row, `${event.dataset} record`)} className="w-full text-left">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs font-semibold text-navy">{event.date?.[1]}</span>
                          <Badge tone="info">{event.dataset}</Badge>
                          <span className="text-[10px] text-slate-400">Open record →</span>
                        </div>
                        <p className="mt-1 text-[11px] text-slate-500">
                          {Object.entries(event.row)
                            .filter(([key]) => !DATE_HINTS.some((hint) => key.toLowerCase().includes(hint)))
                            .slice(0, 6)
                            .map(([key, value]) => `${key}: ${displayValue(value)}`)
                            .join(' · ')}
                        </p>
                      </button>
                    </li>
                  ))}
                </ol>
              </Card>
              <Card>
                <CardHeader title="Records by dataset" subtitle="Click a dataset to filter the timeline" action={<UserRound className="h-4 w-4 text-teal" />} />
                <div className="space-y-2 p-4">
                  {counts.map(([datasetKey, count]) => (
                    <button key={datasetKey} type="button" onClick={() => setDatasetFilter((current) => current === datasetKey ? '' : datasetKey)} data-testid={`journey-count-${datasetKey}`} className={`flex w-full items-center justify-between rounded border px-2 py-2 text-left text-xs ${datasetFilter === datasetKey ? 'border-teal bg-teal-light/40 text-teal-dark' : 'border-line text-slate-600 hover:border-teal'}`}>
                      <span>{datasetKey.replace(/_/g, ' ')}</span>
                      <span className="font-semibold">{count}</span>
                    </button>
                  ))}
                </div>
                <div className="border-t border-line p-4 text-[11px] text-slate-500">
                  <Link href="/explorer" className="font-medium text-teal hover:underline">Open Data Explorer →</Link>
                </div>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
}
