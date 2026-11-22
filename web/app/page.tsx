'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import {
  Activity, ArrowRight, BarChart3, BookOpen, Building2, CalendarClock, Database,
  ExternalLink, FileCheck2, FileText, FlaskConical, GitBranch, Github, LayoutDashboard,
  Moon, Package, Pill, Route as RouteIcon, ShieldAlert, ShieldCheck, Siren,
  Stethoscope, Sun, UsersRound, WalletCards,
} from 'lucide-react';
import { landingStats, fmt, fmtCompact } from '@/lib/landing-stats';
import { useTheme } from '@/components/ThemeProvider';

const REPO_URL = process.env.NEXT_PUBLIC_REPO_URL;
const DEMO_URL = process.env.NEXT_PUBLIC_DEMO_URL;
const AUTHOR_NAME = process.env.NEXT_PUBLIC_AUTHOR_NAME;
const LINKEDIN_URL = process.env.NEXT_PUBLIC_LINKEDIN_URL;
const PORTFOLIO_URL = process.env.NEXT_PUBLIC_PORTFOLIO_URL;

type Module = { icon: typeof Activity; name: string; group: string; href: string; detail: string };

const MODULES: Module[] = [
  { icon: LayoutDashboard, name: 'Executive Overview', group: 'Executive', href: '/overview', detail: 'System-wide KPIs, trends, and drill-down entry points.' },
  { icon: Building2, name: 'Hospital Comparison', group: 'Executive', href: '/hospitals', detail: 'Cross-hospital benchmarks, rankings, and profile views.' },
  { icon: Building2, name: 'Hospital Profile', group: 'Executive', href: '/hospitals', detail: 'Operational, financial, and experience detail for a single hospital.' },
  { icon: CalendarClock, name: 'Appointments', group: 'Operations', href: '/appointments', detail: 'Scheduling, completion, no-shows, and wait times.' },
  { icon: Siren, name: 'Emergency', group: 'Operations', href: '/emergency', detail: 'ED arrivals, triage, boarding, and throughput signals.' },
  { icon: Stethoscope, name: 'Inpatient', group: 'Operations', href: '/inpatient', detail: 'Admissions, occupancy, LOS, and discharge flow.' },
  { icon: Activity, name: 'Procedures', group: 'Operations', href: '/procedures', detail: 'Procedure volume, duration, and utilization patterns.' },
  { icon: FlaskConical, name: 'Diagnostics', group: 'Operations', href: '/diagnostics', detail: 'Lab/radiology turnaround and completion metrics.' },
  { icon: Pill, name: 'Pharmacy', group: 'Operations', href: '/pharmacy', detail: 'Medication activity, dispensing, and inventory signals.' },
  { icon: WalletCards, name: 'Finance', group: 'Finance', href: '/finance', detail: 'Gross/net revenue, collections, receivables, and leakage.' },
  { icon: FileCheck2, name: 'Claims & Denials', group: 'Finance', href: '/claims', detail: 'Claim submission, adjudication, denials, payer mix, and appeals.' },
  { icon: UsersRound, name: 'Workforce', group: 'Workforce', href: '/workforce', detail: 'Staffing, shift coverage, overtime, absence, and workforce cost.' },
  { icon: Package, name: 'Inventory', group: 'Workforce', href: '/inventory', detail: 'Stock levels, stockouts, expiry, waste, and supplier performance.' },
  { icon: ShieldCheck, name: 'Quality & Safety', group: 'Quality', href: '/quality', detail: 'Clinical quality, safety events, and compliance metrics.' },
  { icon: BarChart3, name: 'Patient Experience', group: 'Quality', href: '/experience', detail: 'Satisfaction, feedback, and service experience trends.' },
  { icon: Database, name: 'Data Explorer', group: 'Governance', href: '/explorer', detail: 'Record-level exploration with filters and export.' },
  { icon: RouteIcon, name: 'Patient Journey', group: 'Governance', href: '/patient-journey', detail: 'Timeline view across encounters and care events.' },
  { icon: ShieldAlert, name: 'Data Quality', group: 'Governance', href: '/data-quality', detail: 'Freshness, completeness, and validation checks.' },
  { icon: GitBranch, name: 'Pipeline', group: 'Governance', href: '/pipeline', detail: 'Run history, lineage, and pipeline health context.' },
  { icon: BookOpen, name: 'KPI Glossary', group: 'Governance', href: '/kpi-glossary', detail: 'Metric definitions, formulas, and ownership.' },
  { icon: FileText, name: 'Methodology', group: 'Governance', href: '/methodology', detail: 'How synthetic data, validation, and metrics are produced.' },
];

const GROUPS = ['All', 'Executive', 'Operations', 'Finance', 'Workforce', 'Quality', 'Governance'] as const;

const GALLERY = [
  { src: '/landing/overview-1440.png', title: 'Network Overview', detail: 'Executive KPIs and trends', href: '/overview' },
  { src: '/landing/hospitals-1440.png', title: 'Hospital Comparison', detail: 'Benchmarks across hospitals', href: '/hospitals' },
  { src: '/landing/finance-1440.png', title: 'Finance & Revenue', detail: 'Revenue, collections, leakage', href: '/finance' },
  { src: '/landing/claims-1440.png', title: 'Claims & Denials', detail: 'Payer mix and adjudication', href: '/claims' },
  { src: '/landing/data-quality-1440.png', title: 'Data Quality', detail: 'Freshness and validation checks', href: '/data-quality' },
  { src: '/landing/pipeline-1440.png', title: 'Pipeline', detail: 'Run history and lineage', href: '/pipeline' },
];

const ARCH = [
  { name: 'Generator', note: 'Synthetic healthcare records' },
  { name: 'Bronze', note: landingStats.bronze_rows ? `${fmtCompact(landingStats.bronze_rows)} rows ingested` : 'Raw ingested tables' },
  { name: 'Silver', note: landingStats.valid_records ? `${fmtCompact(landingStats.valid_records)} valid records` : 'Validated records' },
  { name: 'Quality gate', note: landingStats.quarantined_records != null ? `${fmt(landingStats.quarantined_records)} quarantined` : 'Quarantine & reconciliation' },
  { name: 'Gold', note: landingStats.gold_tables ? `${landingStats.gold_tables} analytics marts` : 'Analytics marts' },
  { name: 'DuckDB', note: 'SQL analytics engine' },
  { name: 'FastAPI', note: 'KPI & data API' },
  { name: 'Next.js', note: 'Dashboard UI' },
];

function Stat({ value, label, note }: { value: string; label: string; note: string }) {
  return (
    <div className="rounded-xl border border-line bg-canvas px-4 py-4">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-2 text-2xl font-semibold tracking-tight text-ink-strong tabular-nums">{value}</dd>
      <p className="mt-1 text-xs leading-5 text-muted">{note}</p>
    </div>
  );
}

export default function LandingPage() {
  const { theme, toggleTheme } = useTheme();
  const [group, setGroup] = useState<(typeof GROUPS)[number]>('All');
  const [activeShot, setActiveShot] = useState(GALLERY[0]);

  const modules = useMemo(() => (group === 'All' ? MODULES : MODULES.filter((m) => m.group === group)), [group]);
  const productStats = [
    landingStats.hospitals != null ? { value: fmt(landingStats.hospitals)!, label: 'Hospitals', note: 'Synthetic multi-hospital network' } : null,
    landingStats.bronze_rows != null ? { value: fmtCompact(landingStats.bronze_rows)!, label: 'Records processed', note: `${fmt(landingStats.bronze_rows)} source rows in bronze` } : null,
    { value: String(MODULES.length), label: 'Dashboard modules', note: 'Executive, operations, finance, quality, governance' },
  ].filter((s): s is { value: string; label: string; note: string } => s !== null);

  const evidence = [
    landingStats.pytest_collected != null ? { value: fmt(landingStats.pytest_collected)!, label: 'Pytest tests collected', note: 'Measured by pytest --collect-only' } : null,
    landingStats.playwright_tests != null ? { value: fmt(landingStats.playwright_tests)!, label: 'Playwright tests', note: 'Measured by Playwright --list' } : null,
    landingStats.bronze_rows != null ? { value: fmtCompact(landingStats.bronze_rows)!, label: 'Bronze rows', note: `Manifest ${landingStats.manifest_run_id ?? ''}`.trim() } : null,
    landingStats.quarantined_records != null ? { value: fmt(landingStats.quarantined_records)!, label: 'Quarantined records', note: 'Quality gate captured invalid rows' } : null,
  ].filter((s): s is { value: string; label: string; note: string } => s !== null);

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-navy text-sm font-bold text-white">H</div>
            <div className="leading-tight">
              <p className="text-sm font-semibold tracking-tight text-ink-strong">HOSPITAL 360</p>
              <p className="text-[11px] text-muted">Healthcare intelligence</p>
            </div>
          </div>
          <nav className="hidden items-center gap-5 md:flex">
            <a href="#modules" className="text-xs font-medium text-muted hover:text-ink">Modules</a>
            <a href="#preview" className="text-xs font-medium text-muted hover:text-ink">Preview</a>
            <a href="#architecture" className="text-xs font-medium text-muted hover:text-ink">Architecture</a>
            <a href="#evidence" className="text-xs font-medium text-muted hover:text-ink">Evidence</a>
          </nav>
          <div className="flex items-center gap-2">
            {REPO_URL ? (
              <a href={REPO_URL} target="_blank" rel="noreferrer" className="inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 text-xs font-medium text-muted hover:bg-surface-hover hover:text-ink">
                <Github className="h-3.5 w-3.5" aria-hidden="true" /> GitHub
              </a>
            ) : null}
            <button type="button" onClick={toggleTheme} aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-line text-muted hover:bg-surface-hover hover:text-ink">
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <Link href={DEMO_URL || '/overview'} className="inline-flex h-9 items-center gap-2 rounded-md bg-navy px-4 text-xs font-medium text-white hover:bg-navy-light">
              {DEMO_URL ? 'Live demo' : 'Open dashboard'} <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="border-b border-line bg-surface">
          <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8 lg:py-20">
            <div className="grid gap-12 lg:grid-cols-[1fr_1.1fr] lg:items-center">
              <div>
                <p className="inline-flex items-center rounded-full border border-line bg-surface-alt px-3 py-1 text-[11px] font-medium text-muted">Synthetic multi-hospital analytics platform</p>
                <h1 className="mt-5 max-w-3xl text-4xl font-semibold tracking-tight text-ink-strong sm:text-5xl sm:leading-[1.1]">Operational clarity for every hospital decision.</h1>
                <p className="mt-5 max-w-2xl text-base leading-7 text-muted">HOSPITAL 360 is an API-driven healthcare analytics workspace for operations, finance, quality, workforce, and governance. All data is synthetic and for educational use only.</p>
                <div className="mt-8 flex flex-wrap items-center gap-3">
                  <Link href="/overview" className="inline-flex h-11 items-center gap-2 rounded-lg bg-navy px-5 text-sm font-medium text-white hover:bg-navy-light">Enter dashboard <ArrowRight className="h-4 w-4" aria-hidden="true" /></Link>
                  {REPO_URL ? <a href={REPO_URL} target="_blank" rel="noreferrer" className="inline-flex h-11 items-center gap-2 rounded-lg border border-line bg-surface px-5 text-sm font-medium text-ink hover:bg-surface-hover"><Github className="h-4 w-4" aria-hidden="true" /> View on GitHub</a> : <Link href="/data-quality" className="inline-flex h-11 items-center gap-2 rounded-lg border border-line bg-surface px-5 text-sm font-medium text-ink hover:bg-surface-hover">View data quality</Link>}
                </div>
                <dl className="mt-10 grid gap-4 sm:grid-cols-3">{productStats.map((s) => <Stat key={s.label} {...s} />)}</dl>
              </div>
              <div className="rounded-2xl border border-line bg-canvas p-3 shadow-card">
                <div className="flex items-center gap-1.5 border-b border-line px-2 pb-3">
                  <span className="h-2.5 w-2.5 rounded-full bg-slate-300" /><span className="h-2.5 w-2.5 rounded-full bg-slate-300" /><span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
                  <span className="ml-3 text-[11px] text-muted">Network Overview</span>
                </div>
                <div className="relative mt-3 overflow-hidden rounded-xl border border-line bg-surface">
                  <Image src="/landing/overview-1440.png" alt="HOSPITAL 360 Network Overview dashboard showing KPI cards, trends, and charts" width={1440} height={900} priority className="h-auto w-full" />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="preview" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">Workspace preview</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-strong sm:text-3xl">See the dashboard before you enter it</h2>
            <p className="mt-3 text-sm leading-7 text-muted">Real screenshots from the application. Select a module to preview its layout and metrics.</p>
          </div>
          <div className="mt-8 grid gap-6 lg:grid-cols-[280px_1fr]">
            <div className="flex flex-row gap-2 overflow-x-auto lg:flex-col lg:overflow-visible">
              {GALLERY.map((shot) => (
                <button key={shot.src} type="button" onClick={() => setActiveShot(shot)} className={`min-w-[180px] rounded-lg border px-3 py-3 text-left transition lg:min-w-0 ${activeShot.src === shot.src ? 'border-teal bg-teal-light/30' : 'border-line bg-surface hover:bg-surface-hover'}`}>
                  <p className="text-sm font-medium text-ink-strong">{shot.title}</p>
                  <p className="mt-0.5 text-xs text-muted">{shot.detail}</p>
                </button>
              ))}
            </div>
            <div className="rounded-2xl border border-line bg-surface p-3 shadow-card">
              <div className="relative overflow-hidden rounded-xl border border-line bg-canvas">
                <Image src={activeShot.src} alt={`${activeShot.title} screenshot`} width={1440} height={900} loading="lazy" className="h-auto w-full" />
              </div>
              <div className="mt-3 flex items-center justify-between px-1">
                <div><p className="text-sm font-medium text-ink-strong">{activeShot.title}</p><p className="text-xs text-muted">{activeShot.detail}</p></div>
                <Link href={activeShot.href} className="inline-flex items-center gap-1 text-sm font-medium text-teal hover:text-teal-dark">Open page <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" /></Link>
              </div>
            </div>
          </div>
        </section>

        <section id="modules" className="border-y border-line bg-surface">
          <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">Modules</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-strong sm:text-3xl">{MODULES.length} dashboard modules across the healthcare workflow</h2>
              <p className="mt-3 text-sm leading-7 text-muted">Each module uses shared filters, consistent cards/tables/charts, and drill-down behavior.</p>
            </div>
            <div className="mt-6 flex flex-wrap gap-2" role="tablist" aria-label="Module categories">
              {GROUPS.map((g) => (
                <button key={g} type="button" role="tab" aria-selected={group === g} onClick={() => setGroup(g)} className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${group === g ? 'border-teal bg-teal-light/40 text-teal-dark' : 'border-line bg-canvas text-muted hover:text-ink'}`}>{g}</button>
              ))}
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {modules.map(({ icon: Icon, name, group: g, detail, href }) => (
                <Link key={name} href={href} className="group rounded-xl border border-line bg-canvas p-4 transition hover:border-teal/40 hover:bg-surface-hover">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-alt text-teal"><Icon className="h-4 w-4" aria-hidden="true" /></div>
                      <div><h3 className="text-sm font-semibold text-ink-strong group-hover:text-teal-dark">{name}</h3><p className="text-[11px] text-muted">{g}</p></div>
                    </div>
                    <ArrowRight className="mt-1 h-3.5 w-3.5 text-slate-300 group-hover:text-teal" aria-hidden="true" />
                  </div>
                  <p className="mt-3 text-xs leading-5 text-muted">{detail}</p>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section id="architecture" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">Architecture</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-strong sm:text-3xl">From synthetic data to decision-ready views</h2>
            <p className="mt-3 text-sm leading-7 text-muted">The pipeline validates and quarantines records before they reach analytics marts. The frontend renders API data and never calculates business KPIs.</p>
          </div>
          <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {ARCH.map((step, i) => (
              <div key={step.name} className="relative rounded-xl border border-line bg-surface p-4 shadow-card">
                <div className="flex items-center gap-2">
                  <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-teal-light text-[11px] font-semibold text-teal-dark">{i + 1}</span>
                  <p className="text-sm font-semibold text-ink-strong">{step.name}</p>
                </div>
                <p className="mt-2 text-xs leading-5 text-muted">{step.note}</p>
              </div>
            ))}
          </div>
          <div className="mt-6 rounded-xl border border-line bg-surface-alt px-4 py-3 text-xs text-muted">
            <span className="font-medium text-ink">Engineering highlights:</span> parameterized SQL, quarantine with reconciliation, CI with Docker, independent KPI verification.
          </div>
        </section>

        <section id="evidence" className="border-y border-line bg-surface">
          <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">Evidence</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-strong sm:text-3xl">Measured numbers, not marketing claims</h2>
              <p className="mt-3 text-sm leading-7 text-muted">Counts below are read from the pipeline manifest and test tooling at build time. Source: <span className="font-medium text-ink">{landingStats.manifest_path ?? 'pipeline manifest'}</span>{landingStats.generated_at ? ` (generated ${landingStats.generated_at.slice(0, 10)})` : ''}.</p>
            </div>
            <dl className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{evidence.map((s) => <Stat key={s.label} {...s} />)}</dl>
            <div className="mt-6 flex flex-wrap gap-3 text-sm">
              <Link href="/methodology" className="text-teal hover:text-teal-dark">Methodology</Link>
              <Link href="/kpi-glossary" className="text-teal hover:text-teal-dark">KPI glossary</Link>
              <Link href="/data-quality" className="text-teal hover:text-teal-dark">Data quality</Link>
              {REPO_URL ? <a href={REPO_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-teal hover:text-teal-dark">Repository <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" /></a> : null}
            </div>
          </div>
        </section>

        {(AUTHOR_NAME || LINKEDIN_URL || PORTFOLIO_URL || REPO_URL) ? (
          <section className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
            <div className="rounded-2xl border border-line bg-surface p-6 shadow-card">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">About</p>
              <h2 className="mt-2 text-xl font-semibold tracking-tight text-ink-strong">{AUTHOR_NAME ?? 'Project author'}</h2>
              <p className="mt-2 max-w-3xl text-sm leading-7 text-muted">HOSPITAL 360 is an educational healthcare analytics project demonstrating data pipeline design, API-driven KPI delivery, and dashboard UX with synthetic data only.</p>
              <div className="mt-4 flex flex-wrap gap-3 text-sm">
                {REPO_URL ? <a href={REPO_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-2 text-muted hover:text-ink"><Github className="h-4 w-4" aria-hidden="true" /> GitHub</a> : null}
                {LINKEDIN_URL ? <a href={LINKEDIN_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-2 text-muted hover:text-ink"><ExternalLink className="h-4 w-4" aria-hidden="true" /> LinkedIn</a> : null}
                {PORTFOLIO_URL ? <a href={PORTFOLIO_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-2 text-muted hover:text-ink"><ExternalLink className="h-4 w-4" aria-hidden="true" /> Portfolio</a> : null}
              </div>
            </div>
          </section>
        ) : null}

        <section className="px-4 pb-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl rounded-2xl border border-line bg-navy px-6 py-10 text-white sm:px-10">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-light">Ready to explore</p>
            <h2 className="mt-3 max-w-3xl text-2xl font-semibold tracking-tight sm:text-3xl">Open the dashboard and follow the data from KPI to record.</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-200">Start with the executive overview, apply filters, compare hospitals, inspect patient journeys, and review data quality and glossary definitions.</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/overview" className="inline-flex h-11 items-center gap-2 rounded-lg bg-teal px-5 text-sm font-medium text-white hover:bg-teal-dark">Enter dashboard <ArrowRight className="h-4 w-4" aria-hidden="true" /></Link>
              <Link href="/kpi-glossary" className="inline-flex h-11 items-center gap-2 rounded-lg border border-white/20 px-5 text-sm font-medium text-white hover:bg-white/10">Open KPI glossary</Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 text-[11px] text-muted sm:flex-row sm:items-center sm:justify-between">
          <p>HOSPITAL 360 · Synthetic healthcare analytics platform</p>
          <p>Educational project only · Synthetic data · Not for clinical use</p>
        </div>
      </footer>
    </div>
  );
}
