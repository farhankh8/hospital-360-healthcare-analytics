'use client';

import { useMemo, useState, type FormEvent } from 'react';
import { Download, Route as RouteIcon, Search, Sparkles, UserRound } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { apiExportCsv, apiGet, useApiQuery } from '@/lib/api';
import { useFilters } from '@/lib/filters';
import { NO_FILTERS, type TableRow } from '@/lib/types';
import { displayValue } from '@/lib/utils';
import { useDrilldown } from './DrilldownDrawer';
import { Badge, Card, CardHeader, EmptyState, ErrorState, PageHeading, Skeleton } from './ui';

type JourneyPayload = {
  patient?: Record<string, unknown>;
  encounter_summary?: Record<string, unknown>;
  admission_summary?: Record<string, unknown>;
  billing_summary?: Record<string, unknown>;
  claim_summary?: Record<string, unknown>;
  feedback_summary?: Record<string, unknown>;
  appointments?: TableRow[];
  encounters?: TableRow[];
  admissions?: TableRow[];
  transfers?: TableRow[];
  procedures?: TableRow[];
  lab_orders?: TableRow[];
  lab_results?: TableRow[];
  prescriptions?: TableRow[];
  dispensing?: TableRow[];
  diagnoses?: TableRow[];
  diagnoses_note?: string;
  billing_claims?: TableRow[];
  invoices?: TableRow[];
  payments?: TableRow[];
  feedback?: TableRow[];
  timeline?: Array<{ event_type: string; event_label: string; event_date?: string; event_id?: string; table?: string; detail?: TableRow }>;
  event_types?: string[];
  synthetic_notice?: string;
};

function inferIdParam(id: string): { patient_id?: string; encounter_id?: string; admission_id?: string } {
  const v = id.trim().toUpperCase();
  if (v.startsWith('ENC')) return { encounter_id: id.trim() };
  if (v.startsWith('ADM')) return { admission_id: id.trim() };
  return { patient_id: id.trim() };
}

function fmtMoney(v: unknown): string {
  const n = Number(v);
  if (!Number.isFinite(n)) return '$0';
  return `$${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

export function PatientJourneyPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { openDrilldown } = useDrilldown();
  const { filters } = useFilters();
  const idParam = searchParams.get('patient_id') || searchParams.get('encounter_id') || searchParams.get('admission_id') || '';
  const [input, setInput] = useState(idParam);
  const [eventFilter, setEventFilter] = useState<string>('');

  const idQuery = useMemo(() => inferIdParam(idParam), [idParam]);

  const journeyQuery = useApiQuery<JourneyPayload>(
    'patient-journey',
    '/journey',
    filters,
    { ...idQuery, ...(eventFilter ? { event_type: eventFilter } : {}) },
    Boolean(idParam),
  );

  const payload = (journeyQuery.data?.data as JourneyPayload | undefined) ?? null;
  const timeline = Array.isArray(payload?.timeline) ? payload.timeline : [];
  const eventTypes = Array.isArray(payload?.event_types) ? payload.event_types : [];
  const patient = (payload?.patient as Record<string, unknown> | undefined) ?? null;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const id = input.trim();
    const params = new URLSearchParams(searchParams.toString());
    params.delete('patient_id'); params.delete('encounter_id'); params.delete('admission_id');
    if (id) {
      const inferred = inferIdParam(id);
      const [k, v] = Object.entries(inferred)[0];
      params.set(k, String(v));
    }
    router.push(`${pathname}?${params.toString()}`);
  };

  const trySample = async () => {
    try {
      const res = await apiGet<{ patient_id?: string }>('/journey/sample-patient', NO_FILTERS);
      const pid = String((res.data as any)?.patient_id || '');
      if (!pid) return;
      setInput(pid);
      const params = new URLSearchParams(searchParams.toString());
      params.delete('encounter_id'); params.delete('admission_id');
      params.set('patient_id', pid);
      router.push(`${pathname}?${params.toString()}`);
    } catch {
      // ignore - button is convenience
    }
  };

  const exportEvents = async () => {
    if (!idParam) return;
    await apiExportCsv('/journey/events', filters, { ...idQuery, ...(eventFilter ? { event_type: eventFilter } : {}) }, `patient-journey-${idParam}`);
  };

  const isLoading = journeyQuery.isLoading;
  const hasError = journeyQuery.isError;

  return (
    <div className="space-y-5" data-testid="patient-journey-page">
      <PageHeading
        title="Patient Journey"
        description="Chronological synthetic patient timeline across encounters, admissions, labs, medications, billing, claims, and feedback."
        badge="Synthetic IDs only"
      />

      <Card className="border-l-4 border-l-teal p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <form onSubmit={submit} className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label htmlFor="journey-id" className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-600">Patient / Encounter / Admission ID</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-600" />
                <input
                  id="journey-id"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="e.g. PAT003840, ENC..., ADM..."
                  data-testid="journey-search"
                  className="h-9 w-full rounded-md border border-line pl-9 pr-3 text-xs outline-none focus:border-teal focus:ring-2 focus:ring-teal/15"
                />
              </div>
            </div>
            <button type="submit" className="h-9 rounded-md bg-navy px-4 text-xs font-medium text-white hover:bg-navy-light">View journey</button>
          </form>
          <div className="flex gap-2">
            <button type="button" onClick={trySample} data-testid="journey-sample" className="inline-flex h-9 items-center gap-1.5 rounded-md border border-line px-3 text-xs font-medium text-slate-600 hover:border-teal hover:text-teal">
              <Sparkles className="h-3.5 w-3.5" /> Try a sample patient
            </button>
            <button type="button" onClick={exportEvents} disabled={!idParam} data-testid="journey-export" className="inline-flex h-9 items-center gap-1.5 rounded-md border border-line px-3 text-xs font-medium text-slate-600 hover:border-teal hover:text-teal disabled:opacity-40">
              <Download className="h-3.5 w-3.5" /> Export CSV
            </button>
          </div>
        </div>
        <p className="mt-3 text-[11px] text-slate-600">{String(payload?.synthetic_notice || 'Synthetic data only. No real patient identities, no clinical recommendations.')}</p>
      </Card>

      {!idParam && <Card><EmptyState message="Enter a synthetic ID" hint="Search by patient_id, encounter_id, or admission_id. All identities are synthetic." /></Card>}
      {hasError && <Card><ErrorState message={`Journey could not be loaded. ${String((journeyQuery.error as any)?.message || '')}`.trim()} /></Card>}
      {idParam && isLoading && <Card className="p-5"><Skeleton className="h-48 w-full" /></Card>}

      {idParam && !isLoading && !hasError && payload && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="p-4" data-testid="journey-card-patient"><p className="text-[10px] uppercase tracking-wide text-slate-600">Patient</p><p className="mt-1 text-sm font-semibold text-navy">{String(patient?.patient_id || idParam)}</p><p className="text-[11px] text-slate-600">{String(patient?.gender || '')} {patient?.age_group ? `• ${patient.age_group}` : ''} {patient?.patient_type ? `• ${patient.patient_type}` : ''}</p></Card>
            <Card className="p-4"><p className="text-[10px] uppercase tracking-wide text-slate-600">Encounters / Admissions</p><p className="mt-1 text-lg font-semibold text-navy">{displayValue(payload.encounter_summary?.encounter_count)} / {displayValue(payload.admission_summary?.admission_count)}</p><p className="text-[11px] text-slate-600">Readmissions: {displayValue(payload.admission_summary?.readmissions)}</p></Card>
            <Card className="p-4"><p className="text-[10px] uppercase tracking-wide text-slate-600">Billed / Paid</p><p className="mt-1 text-lg font-semibold text-navy">{fmtMoney(payload.billing_summary?.net_amount)} / {fmtMoney(payload.billing_summary?.paid_amount)}</p><p className="text-[11px] text-slate-600">Balance: {fmtMoney(payload.billing_summary?.balance_amount)}</p></Card>
            <Card className="p-4"><p className="text-[10px] uppercase tracking-wide text-slate-600">Claims / Feedback</p><p className="mt-1 text-lg font-semibold text-navy">{displayValue(payload.claim_summary?.claim_count)} / {displayValue(payload.feedback_summary?.feedback_count)}</p><p className="text-[11px] text-slate-600">Avg rating: {displayValue(payload.feedback_summary?.avg_rating)}</p></Card>
          </div>

          <Card>
            <CardHeader title="Timeline filters" subtitle="Filter by event type. Date range follows global filters." action={<RouteIcon className="h-4 w-4 text-teal" />} />
            <div className="flex flex-wrap gap-2 p-4 pt-0">
              <button type="button" onClick={() => setEventFilter('')} className={`rounded-full border px-3 py-1 text-[11px] ${!eventFilter ? 'border-teal bg-teal-light/40 text-teal-dark' : 'border-line text-slate-600'}`}>All</button>
              {eventTypes.map((t) => (
                <button key={t} type="button" data-testid={`journey-filter-${t}`} onClick={() => setEventFilter((c) => c === t ? '' : t)} className={`rounded-full border px-3 py-1 text-[11px] ${eventFilter === t ? 'border-teal bg-teal-light/40 text-teal-dark' : 'border-line text-slate-600'}`}>{t.replace(/_/g, ' ')}</button>
              ))}
            </div>
          </Card>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader title="Timeline" subtitle={`${timeline.length} events`} action={<Badge tone="info">{eventFilter || 'all events'}</Badge>} />
              {timeline.length === 0 ? (
                <EmptyState message="No timeline events found" hint="Try clearing event type filter or widening the date range." />
              ) : (
                <ol className="max-h-[720px] space-y-0 overflow-y-auto px-5 py-4" data-testid="journey-timeline">
                  {timeline.map((event, index) => (
                    <li key={`${event.event_type}-${event.event_id}-${index}`} className="relative border-l border-line pb-5 pl-6 last:pb-0">
                      <span className="absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-teal" />
                      <button type="button" onClick={() => openDrilldown(event.detail as TableRow, `${event.event_label} ${event.event_id || ''}`)} className="w-full text-left">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs font-semibold text-navy">{String(event.event_date || 'No date')}</span>
                          <Badge tone="info">{event.event_label}</Badge>
                          <span className="text-[10px] text-slate-600">{String(event.event_id || '')}</span>
                        </div>
                        <p className="mt-1 text-[11px] text-slate-600">
                          {Object.entries((event.detail as TableRow) || {})
                            .filter(([k, v]) => v !== null && v !== undefined && v !== '' && !['patient_id'].includes(k))
                            .slice(0, 6)
                            .map(([k, v]) => `${k}: ${displayValue(v)}`)
                            .join(' · ')}
                        </p>
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </Card>

            <div className="space-y-5">
              <Card>
                <CardHeader title="Summary" subtitle="Synthetic patient overview" action={<UserRound className="h-4 w-4 text-teal" />} />
                <div className="space-y-2 p-4 text-xs text-slate-600">
                  {Object.entries(patient || {}).slice(0, 12).map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-3 border-b border-line/60 pb-1"><span className="text-slate-600">{k}</span><span className="text-right font-medium text-slate-700">{displayValue(v)}</span></div>
                  ))}
                </div>
              </Card>
              <Card>
                <CardHeader title="Clinical & billing sections" subtitle="Available records" />
                <div className="space-y-2 p-4 text-xs">
                  {([
                    ['appointments', payload.appointments], ['encounters', payload.encounters], ['admissions', payload.admissions],
                    ['lab_orders', payload.lab_orders], ['lab_results', payload.lab_results], ['prescriptions', payload.prescriptions],
                    ['diagnoses', payload.diagnoses], ['billing_claims', payload.billing_claims], ['invoices', payload.invoices],
                    ['payments', payload.payments], ['feedback', payload.feedback],
                  ] as Array<[string, unknown]>).map(([name, arr]) => (
                    <div key={name} className="flex items-center justify-between rounded border border-line px-2 py-1.5">
                      <span className="text-slate-600">{name.replace(/_/g, ' ')}</span>
                      <span className="font-semibold text-navy">{Array.isArray(arr) ? arr.length : 0}</span>
                    </div>
                  ))}
                  {payload.diagnoses_note ? <p className="text-[10px] text-slate-600">{payload.diagnoses_note}</p> : null}
                </div>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
