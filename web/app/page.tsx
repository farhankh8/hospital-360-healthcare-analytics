import Link from 'next/link';
import {
  Activity,
  ArrowRight,
  BarChart3,
  BookOpen,
  Building2,
  CalendarClock,
  Database,
  FileCheck2,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  Package,
  Pill,
  Route as RouteIcon,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Stethoscope,
  UsersRound,
  WalletCards,
} from 'lucide-react';

const STATS = [
  { value: '21', label: 'Analytics modules', note: 'Operations, finance, quality, workforce, and governance routes' },
  { value: '159', label: 'Pytest checks', note: 'Measured passing with 2 warnings' },
  { value: '38', label: 'Playwright checks', note: 'Measured end-to-end UI coverage' },
  { value: '24/24', label: 'Static build pages', note: 'Measured Next.js production build' },
];

const DATA_SCALE = [
  { value: '10', label: 'Hospitals', note: 'Synthetic multi-hospital network in dim_hospital' },
  { value: '15,200', label: 'Patients', note: 'Patient records in the generated dataset' },
  { value: '82,000', label: 'Encounters', note: 'Outpatient, inpatient, and emergency encounters' },
  { value: '136,800', label: 'Appointments', note: 'Scheduled appointment records' },
  { value: '1.59M', label: 'Bronze rows', note: '1,588,637 total rows ingested across 41 bronze tables' },
  { value: '12', label: 'Gold tables', note: 'Analytics-ready marts for dashboard consumption' },
];

const MODULES = [
  { icon: LayoutDashboard, name: 'Executive Overview', group: 'Executive', detail: 'System-wide KPIs, trends, and drill-down entry points.' },
  { icon: Building2, name: 'Hospital Comparison', group: 'Executive', detail: 'Cross-hospital benchmarks, rankings, and profile views.' },
  { icon: CalendarClock, name: 'Appointments', group: 'Operations', detail: 'Scheduling volume, completion, no-shows, and wait times.' },
  { icon: Siren, name: 'Emergency', group: 'Operations', detail: 'ED arrivals, triage, boarding, and throughput signals.' },
  { icon: Stethoscope, name: 'Inpatient', group: 'Operations', detail: 'Admissions, occupancy, LOS, and discharge flow.' },
  { icon: Activity, name: 'Procedures', group: 'Operations', detail: 'Procedure volume, duration, and utilization patterns.' },
  { icon: FlaskConical, name: 'Diagnostics', group: 'Operations', detail: 'Lab/radiology turnaround and completion metrics.' },
  { icon: Pill, name: 'Pharmacy', group: 'Operations', detail: 'Medication activity, dispensing, and inventory signals.' },
  { icon: WalletCards, name: 'Finance', group: 'Finance', detail: 'Revenue, cost, margin, and payer-mix views.' },
  { icon: FileCheck2, name: 'Claims & Denials', group: 'Finance', detail: 'Claim status, denial rates, and reimbursement tracking.' },
  { icon: UsersRound, name: 'Workforce', group: 'Workforce', detail: 'Staffing, overtime, and department workforce indicators.' },
  { icon: Package, name: 'Inventory', group: 'Workforce', detail: 'Stock levels, consumption, and replenishment risk.' },
  { icon: ShieldCheck, name: 'Quality & Safety', group: 'Quality', detail: 'Clinical quality, safety events, and compliance metrics.' },
  { icon: BarChart3, name: 'Patient Experience', group: 'Quality', detail: 'Satisfaction, feedback, and service experience trends.' },
  { icon: Database, name: 'Data Explorer', group: 'Governance', detail: 'Record-level exploration with filters and export.' },
  { icon: RouteIcon, name: 'Patient Journey', group: 'Governance', detail: 'Timeline view across encounters and care events.' },
  { icon: ShieldAlert, name: 'Data Quality', group: 'Governance', detail: 'Freshness, completeness, and validation checks.' },
  { icon: GitBranch, name: 'Pipeline', group: 'Governance', detail: 'Run history, lineage, and pipeline health context.' },
  { icon: BookOpen, name: 'KPI Glossary', group: 'Governance', detail: 'Metric definitions, formulas, and ownership.' },
];

const FLOW = [
  {
    step: '01',
    title: 'Ingest and validate',
    detail: 'Synthetic healthcare records are generated and processed through data pipeline steps with validation and manifests.',
  },
  {
    step: '02',
    title: 'Serve API-driven metrics',
    detail: 'FastAPI endpoints provide KPI values, chart datasets, table rows, filters, and glossary metadata.',
  },
  {
    step: '03',
    title: 'Explore in the dashboard',
    detail: 'Next.js pages render shared filters, drill-downs, exports, and role-relevant views without frontend KPI math.',
  },
];

const PRINCIPLES = [
  'API is the single source of truth for KPI values.',
  'Frontend renders and formats; it does not calculate business KPIs.',
  'Global filters, drill-downs, exports, and loading/error/empty states are preserved.',
  'Synthetic data only. Educational project, not for clinical use.',
];

export default function LandingPage() {
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
            <a href="#modules" className="text-xs font-medium text-muted transition hover:text-ink">Modules</a>
            <a href="#data" className="text-xs font-medium text-muted transition hover:text-ink">Data</a>
            <a href="#flow" className="text-xs font-medium text-muted transition hover:text-ink">How it works</a>
            <a href="#evidence" className="text-xs font-medium text-muted transition hover:text-ink">Evidence</a>
          </nav>
          <Link
            href="/overview"
            className="inline-flex h-9 items-center gap-2 rounded-md bg-navy px-4 text-xs font-medium text-white transition hover:bg-navy-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/30"
          >
            Open dashboard <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </div>
      </header>

      <main>
        <section className="border-b border-line bg-surface">
          <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8 lg:py-20">
            <div className="grid gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:items-start">
              <div>
                <p className="inline-flex items-center rounded-full border border-line bg-surface-alt px-3 py-1 text-[11px] font-medium text-muted">
                  Synthetic multi-hospital analytics platform
                </p>
                <h1 className="mt-5 max-w-3xl text-4xl font-semibold tracking-tight text-ink-strong sm:text-5xl sm:leading-[1.1]">
                  Operational clarity for every hospital decision.
                </h1>
                <p className="mt-5 max-w-2xl text-base leading-7 text-muted">
                  HOSPITAL 360 is a healthcare analytics workspace that combines executive KPIs, operational drill-downs,
                  finance, quality, workforce, and data governance. It is designed as a measurable, API-driven project with
                  synthetic data only.
                </p>

                <div className="mt-8 flex flex-wrap items-center gap-3">
                  <Link
                    href="/overview"
                    className="inline-flex h-11 items-center gap-2 rounded-lg bg-navy px-5 text-sm font-medium text-white transition hover:bg-navy-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/30"
                  >
                    Enter dashboard <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                  <Link
                    href="/data-quality"
                    className="inline-flex h-11 items-center gap-2 rounded-lg border border-line bg-surface px-5 text-sm font-medium text-ink transition hover:bg-surface-hover"
                  >
                    View data quality
                  </Link>
                </div>

                <dl className="mt-10 grid gap-4 sm:grid-cols-2">
                  {STATS.map((stat) => (
                    <div key={stat.label} className="rounded-xl border border-line bg-canvas px-4 py-4">
                      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">{stat.label}</dt>
                      <dd className="mt-2 text-2xl font-semibold tracking-tight text-ink-strong tabular-nums">{stat.value}</dd>
                      <p className="mt-1 text-xs leading-5 text-muted">{stat.note}</p>
                    </div>
                  ))}
                </dl>
              </div>

              <div className="rounded-2xl border border-line bg-canvas p-5 shadow-card">
                <div className="flex items-center justify-between border-b border-line pb-4">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Workspace preview</p>
                    <h2 className="mt-1 text-sm font-semibold text-ink-strong">What you can inspect</h2>
                  </div>
                  <span className="rounded-md bg-teal-light px-2 py-1 text-[11px] font-medium text-teal-dark">API-driven</span>
                </div>

                <div className="mt-4 space-y-3">
                  {[
                    { icon: LayoutDashboard, title: 'Executive overview', text: 'Track KPI cards, trends, compare periods, and drill into modules.' },
                    { icon: Building2, title: 'Hospital profiles', text: 'Compare hospitals, open profiles, and inspect operational differences.' },
                    { icon: Database, title: 'Explorer and exports', text: 'Filter records, inspect tables, and export data for analysis.' },
                    { icon: ShieldAlert, title: 'Governance', text: 'Review data quality, pipeline runs, glossary, and methodology.' },
                  ].map(({ icon: Icon, title, text }) => (
                    <div key={title} className="flex gap-3 rounded-xl border border-line bg-surface p-4">
                      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface-alt text-teal">
                        <Icon className="h-4 w-4" aria-hidden="true" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-ink-strong">{title}</p>
                        <p className="mt-0.5 text-xs leading-5 text-muted">{text}</p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-4 rounded-xl border border-line bg-surface px-4 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Design system</p>
                  <p className="mt-1 text-sm text-muted">Calm clinical palette, token-based light/dark UI, tabular numerals, and accessible focus states.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="modules" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">Modules</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-strong sm:text-3xl">21 modules across the healthcare workflow</h2>
            <p className="mt-3 text-sm leading-7 text-muted">
              Each module uses shared filters, consistent cards/tables/charts, and drill-down behavior. The list below reflects the platform areas available in the dashboard.
            </p>
          </div>

          <div className="mt-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {MODULES.map(({ icon: Icon, name, group, detail }) => (
              <article key={name} className="rounded-xl border border-line bg-surface p-4 shadow-card">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-alt text-teal">
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-ink-strong">{name}</h3>
                      <p className="text-[11px] text-muted">{group}</p>
                    </div>
                  </div>
                </div>
                <p className="mt-3 text-xs leading-5 text-muted">{detail}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="data" className="border-y border-line bg-surface">
          <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div className="max-w-3xl">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">Data scale</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-strong sm:text-3xl">Synthetic data, measured at pipeline scale</h2>
                <p className="mt-3 text-sm leading-7 text-muted">
                  The dashboard runs on generated healthcare data. Counts below are measured from the latest pipeline manifest
                  (<span className="font-medium text-ink">RUN_20261121_001</span>), not estimates.
                </p>
              </div>
            </div>

            <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {DATA_SCALE.map((item) => (
                <div key={item.label} className="rounded-xl border border-line bg-canvas p-5">
                  <p className="text-3xl font-semibold tracking-tight text-ink-strong tabular-nums">{item.value}</p>
                  <p className="mt-2 text-sm font-medium text-ink">{item.label}</p>
                  <p className="mt-2 text-xs leading-5 text-muted">{item.note}</p>
                </div>
              ))}
            </div>

            <p className="mt-4 text-[11px] leading-5 text-muted">
              Additional measured volumes from the same manifest include 690 doctors, 2,980 staff, 3,450 beds, 24,804 admissions, 106,000 lab orders, 66,000 invoices, and 52,000 claims.
            </p>
          </div>
        </section>

        <section id="flow" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="grid gap-10 lg:grid-cols-[0.95fr_1.05fr]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">How it works</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-strong sm:text-3xl">From pipeline to decision-ready views</h2>
              <p className="mt-3 text-sm leading-7 text-muted">
                The platform is structured so data generation, API contracts, and UI rendering stay separate. That keeps metrics traceable and the interface predictable.
              </p>
              <div className="mt-6 rounded-xl border border-line bg-canvas p-5">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Project principles</p>
                <ul className="mt-3 space-y-2">
                  {PRINCIPLES.map((item) => (
                    <li key={item} className="flex gap-2 text-sm leading-6 text-muted">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal" aria-hidden="true" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="space-y-4">
              {FLOW.map((item) => (
                <div key={item.step} className="rounded-xl border border-line bg-canvas p-5">
                  <div className="flex items-center gap-3">
                    <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-teal-light text-xs font-semibold text-teal-dark">{item.step}</span>
                    <h3 className="text-sm font-semibold text-ink-strong">{item.title}</h3>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-muted">{item.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="evidence" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div className="max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">Evidence</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-strong sm:text-3xl">Measured checks, visible in the repo</h2>
              <p className="mt-3 text-sm leading-7 text-muted">
                The project includes automated backend, lint/type/build, and Playwright checks. Counts below are measured from project runs.
              </p>
            </div>
            <Link href="/methodology" className="text-sm font-medium text-teal hover:text-teal-dark">Read methodology</Link>
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {STATS.map((stat) => (
              <div key={stat.label} className="rounded-xl border border-line bg-surface p-5 shadow-card">
                <p className="text-3xl font-semibold tracking-tight text-ink-strong tabular-nums">{stat.value}</p>
                <p className="mt-2 text-sm font-medium text-ink">{stat.label}</p>
                <p className="mt-2 text-xs leading-5 text-muted">{stat.note}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="px-4 pb-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl rounded-2xl border border-line bg-navy px-6 py-10 text-white sm:px-10">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-light">Ready to explore</p>
            <h2 className="mt-3 max-w-3xl text-2xl font-semibold tracking-tight sm:text-3xl">Open the dashboard and follow the data from KPI to record.</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-200">
              Start with the executive overview, apply filters, compare hospitals, inspect patient journeys, and review data quality and glossary definitions.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/overview"
                className="inline-flex h-11 items-center gap-2 rounded-lg bg-teal px-5 text-sm font-medium text-white transition hover:bg-teal-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30"
              >
                Enter dashboard <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                href="/kpi-glossary"
                className="inline-flex h-11 items-center gap-2 rounded-lg border border-white/20 px-5 text-sm font-medium text-white transition hover:bg-white/10"
              >
                Open KPI glossary
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 text-[11px] text-muted sm:flex-row sm:items-center sm:justify-between">
          <p>HOSPITAL 360 · Synthetic healthcare analytics platform</p>
          <p>Educational project only · Not for clinical use</p>
        </div>
      </footer>
    </div>
  );
}
