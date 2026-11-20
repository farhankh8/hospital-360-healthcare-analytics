'use client';

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { useParams, usePathname } from 'next/navigation';
import { X } from 'lucide-react';
import { resolveEndpoint, useApiQuery } from '@/lib/api';
import { useFilters } from '@/lib/filters';
import { displayValue } from '@/lib/utils';
import { formatCell, inferColumnType } from '@/lib/format';
import { getPageConfigByPath } from '@/lib/page-configs';
import type { TableRow } from '@/lib/types';
import { Badge, EmptyState, Spinner } from './ui';

interface DrilldownContextValue {
  openDrilldown: (record: TableRow, title?: string) => void;
  closeDrilldown: () => void;
  isOpen: boolean;
  record: TableRow | null;
  title: string;
}

const DrilldownContext = createContext<DrilldownContextValue | null>(null);

export function DrilldownProvider({ children }: { children: ReactNode }) {
  const [record, setRecord] = useState<TableRow | null>(null);
  const [title, setTitle] = useState('Record details');

  const openDrilldown = useCallback((next: TableRow, nextTitle?: string) => {
    setRecord(next);
    setTitle(nextTitle || 'Record details');
  }, []);
  const closeDrilldown = useCallback(() => setRecord(null), []);

  const value = useMemo<DrilldownContextValue>(
    () => ({ openDrilldown, closeDrilldown, isOpen: Boolean(record), record, title }),
    [openDrilldown, closeDrilldown, record, title],
  );

  return (
    <DrilldownContext.Provider value={value}>
      {children}
      <DrilldownDrawer />
    </DrilldownContext.Provider>
  );
}

export function useDrilldown(): DrilldownContextValue {
  const context = useContext(DrilldownContext);
  if (!context) throw new Error('useDrilldown must be used inside DrilldownProvider');
  return context;
}

function findRecordId(record: TableRow | null): string {
  if (!record) return '';
  const preferredKeys = ['patient_id', 'encounter_id', 'admission_id', 'appointment_id', 'claim_id', 'invoice_id', 'procedure_id', 'lab_order_id', 'feedback_id', 'incident_id', 'hospital_id', 'department_id'];
  for (const key of preferredKeys) {
    if (record[key] !== undefined && record[key] !== null && record[key] !== '') return String(record[key]);
  }
  const fallback = Object.keys(record).find((key) => key.endsWith('_id') || key === 'id');
  return fallback ? String(record[fallback]) : '';
}

export function DrilldownDrawer() {
  const { isOpen, record, title, closeDrilldown, openDrilldown } = useDrilldown();
  const pathname = usePathname();
  const params = useParams<Record<string, string | string[]>>();
  const { filters } = useFilters();
  const config = getPageConfigByPath(pathname);
  const routeId = params?.id ? (Array.isArray(params.id) ? params.id[0] : params.id) : '';
  const endpoint = useMemo(() => resolveEndpoint(config?.tableEndpoint, { id: routeId }), [config?.tableEndpoint, routeId]);
  const recordId = findRecordId(record);

  const relatedQuery = useApiQuery<TableRow[]>(
    'drilldown-related',
    endpoint,
    filters,
    { search: recordId, page_size: 5 },
    Boolean(isOpen && endpoint && recordId),
  );

  if (!isOpen || !record) return null;

  const entries = Object.entries(record).filter(([key]) => key !== 'endpoint');
  const timeline = entries
    .filter(([key, value]) => inferColumnType(key, value) === 'date' && value !== null && value !== undefined && value !== '')
    .sort((a, b) => String(a[1]).localeCompare(String(b[1])));
  const details = entries.filter(([key]) => !timeline.some(([dateKey]) => dateKey === key));
  const relatedRows = Array.isArray(relatedQuery.data?.data) ? relatedQuery.data.data.slice(0, 5) : [];

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label={title}>
      <button type="button" className="absolute inset-0 bg-navy/30 backdrop-blur-[1px]" onClick={closeDrilldown} aria-label="Close details" />
      <aside className="relative flex h-full w-full max-w-lg flex-col overflow-hidden bg-white shadow-drawer">
        <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-teal">Drill-down</p>
            <h2 className="mt-0.5 text-base font-semibold text-navy">{title}</h2>
          </div>
          <button type="button" onClick={closeDrilldown} className="rounded p-1 text-slate-400 hover:bg-canvas hover:text-ink" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
          <section>
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Record details</h3>
            <dl className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2">
              {details.map(([key, value]) => (
                <div key={key} className="min-w-0 border-b border-line pb-2">
                  <dt className="truncate text-[10px] uppercase tracking-wide text-slate-400">{key.replace(/_/g, ' ')}</dt>
                  <dd className="mt-0.5 break-words text-xs font-medium text-ink">{formatCell(value, inferColumnType(key, value))}</dd>
                </div>
              ))}
            </dl>
          </section>

          {timeline.length > 0 && (
            <section>
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Timeline</h3>
              <ol className="relative ml-2 border-l border-line pl-5">
                {timeline.map(([key, value]) => (
                  <li key={key} className="relative mb-3 last:mb-0">
                    <span className="absolute -left-[26px] top-1 h-2.5 w-2.5 rounded-full border-2 border-white bg-teal" />
                    <p className="text-[11px] font-semibold text-ink">{displayValue(value)}</p>
                    <p className="text-[10px] uppercase tracking-wide text-slate-400">{key.replace(/_/g, ' ')}</p>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Related records</h3>
              {recordId && <Badge tone="info">Search: {recordId}</Badge>}
            </div>
            {!recordId && <EmptyState message="No identifier available" hint="This record does not expose a searchable identifier." />}
            {recordId && relatedQuery.isLoading && <div className="flex items-center gap-2 text-xs text-slate-400"><Spinner /> Loading related records…</div>}
            {recordId && relatedQuery.isError && <p className="text-xs text-critical">Related records could not be loaded.</p>}
            {recordId && !relatedQuery.isLoading && !relatedQuery.isError && relatedRows.length === 0 && <EmptyState message="No related records found" />}
            <div className="space-y-2">
              {relatedRows.map((row, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => openDrilldown(row, `Related record ${index + 1}`)}
                  className="w-full rounded-md border border-line p-2.5 text-left text-xs transition hover:border-teal hover:bg-teal-light/40"
                >
                  <span className="line-clamp-1 font-medium text-ink">
                    {displayValue(row[Object.keys(row).find((key) => key.endsWith('_id')) || Object.keys(row)[0]])}
                  </span>
                  <span className="mt-0.5 block truncate text-[10px] text-slate-400">
                    {Object.entries(row)
                      .slice(0, 4)
                      .map(([key, value]) => `${key}: ${displayValue(value)}`)
                      .join(' · ')}
                  </span>
                </button>
              ))}
            </div>
          </section>
        </div>
      </aside>
    </div>
  );
}
