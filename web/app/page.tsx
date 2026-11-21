import Link from 'next/link';
import {
  Activity,
  ArrowRight,
  BarChart3,
  Building2,
  Database,
  FileCheck2,
  LayoutDashboard,
  ShieldCheck,
  Siren,
  WalletCards,
} from 'lucide-react';

const MODULE_GROUPS = [
  {
    title: 'Operations',
    detail: 'Overview, appointments, emergency, inpatient, procedures, diagnostics, pharmacy.',
    icon: Activity,
  },
  {
    title: 'Finance & Claims',
    detail: 'Revenue, cost, claims, payer mix, and reconciliation-oriented reporting views.',
    icon: WalletCards,
  },
  {
    title: 'Quality & Workforce',
    detail: 'Experience, quality, workforce, inventory, and data quality monitoring.',
    icon: ShieldCheck,
  },
];

const EVIDENCE = [
  { value: '21', label: 'Analytics modules', note: 'Blueprint routes across operations, finance, quality, and governance.' },
  { value: '159', label: 'Pytest tests passing', note: 'Measured in project checks (2 warnings).' },
  { value: '38', label: 'Playwright tests passing', note: 'Measured end-to-end UI checks.' },
  { value: '24/24', label: 'Static pages built', note: 'Measured Next.js production build.' },
];

const STACK = [
  'Next.js 15',
  'TypeScript',
  'Tailwind CSS',
  'ECharts',
  'FastAPI',
  'DuckDB / Parquet',
  'Pytest + Playwright',
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-navy text-sm font-bold text-white">H</div>
            <div>
              <p className="text-sm font-semibold tracking-tight text-ink-strong">HOSPITAL 360</p>
              <p className="text-[11px] text-muted">Healthcare intelligence platform</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a href="#modules" className="hidden text-xs font-medium text-muted transition hover:text-ink sm:block">Modules</a>
            <a href="#evidence" className="hidden text-xs font-medium text-muted transition hover:text-ink sm:block">Evidence</a>
            <Link
              href="/overview"
              className="inline-flex h-9 items-center gap-2 rounded-md bg-navy px-4 text-xs font-medium text-white transition hover:bg-navy-light"
            >
              Enter dashboard <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="border-b border-line bg-surface">
          <div className="mx-auto grid max-w-7xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:px-8 lg:py-20">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full border border-teal/20 bg-teal-light px-3 py-1 text-[11px] font-medium text-teal-dark">
                <Database className="h-3.5 w-3.5" aria-hidden="true" />
                Synthetic data only · Educational analytics project
              </p>
              <h1 className="mt-5 max-w-3xl text-4xl font-semibold tracking-tight text-ink-strong sm:text-5xl">
                Multi-hospital healthcare analytics, built to be trusted.
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-7 text-muted">
                HOSPITAL 360 brings executive KPIs, operational drill-downs, finance, quality, workforce, and data-quality
                governance into one calm analytics workspace. The frontend renders API-driven metrics; the platform is backed
                by measured tests and reproducible data pipelines.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  href="/overview"
                  className="inline-flex h-11 items-center gap-2 rounded-lg bg-navy px-5 text-sm font-medium text-white transition hover:bg-navy-light"
                >
                  View live dashboard <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
                <a
                  href="#evidence"
                  className="inline-flex h-11 items-center gap-2 rounded-lg border border-line bg-surface px-5 text-sm font-medium text-ink transition hover:bg-surface-hover"
                >
                  See evidence
                </a>
              </div>
              <div className="mt-8 flex flex-wrap gap-2">
                {STACK.map((item) => (
                  <span key={item} className="rounded-md border border-line bg-surface-alt px-2.5 py-1 text-[11px] font-medium text-muted">
                    {item}
                  </span>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-line bg-canvas p-5 shadow-card">
              <div className="flex items-center justify-between border-b border-line pb-4">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Platform snapshot</p>
                  <p className="mt-1 text-sm font-medium text-ink-strong">Executive operations workspace</p>
                </div>
                <span className="rounded-md bg-teal-light px-2 py-1 text-[11px] font-medium text-teal-dark">API-driven</span>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {[
                  { icon: LayoutDashboard, label: 'Executive overview', value: 'KPI cards, trends, drill-downs' },
                  { icon: Building2, label: 'Hospital comparison', value: 'Profiles, benchmarks, rankings' },
                  { icon: BarChart3, label: 'Analytics modules', value: '21 routes with shared filters' },
                  { icon: FileCheck2, label: 'Data quality', value: 'Pipeline, glossary, methodology' },
                ].map(({ icon: Icon, label, value }) => (
                  <div key={label} className="rounded-xl border border-line bg-surface p-4">
                    <div className="flex items-center gap-2 text-muted">
                      <Icon className="h-4 w-4 text-teal" aria-hidden="true" />
                      <span className="text-[11px] font-medium uppercase tracking-wide">{label}</span>
                    </div>
                    <p className="mt-2 text-sm font-medium text-ink-strong">{value}</p>
                  </div>
                ))}
              </div>
              <div className="mt-4 rounded-xl border border-line bg-surface p-4">
                <div className="flex items-center gap-2 text-muted">
                  <Siren className="h-4 w-4 text-teal" aria-hidden="true" />
                  <span className="text-[11px] font-medium uppercase tracking-wide">Design principle</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-muted">
                  Calm, clinical, data-dense UI. Color carries meaning, charts are token-themed, and KPIs come from the API.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section id="modules" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">What it covers</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-strong">One platform, multiple operational domains</h2>
            <p className="mt-3 text-sm leading-7 text-muted">
              The dashboard is organized by healthcare operations workflows, with global filters, drill-downs, exports, and a shared design system.
            </p>
          </div>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {MODULE_GROUPS.map(({ title, detail, icon: Icon }) => (
              <article key={title} className="rounded-xl border border-line bg-surface p-5 shadow-card">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-light text-teal-dark">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <h3 className="mt-4 text-sm font-semibold text-ink-strong">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{detail}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="evidence" className="border-y border-line bg-surface">
          <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal">Measured evidence</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-strong">Checks, not claims</h2>
              </div>
              <p className="max-w-xl text-sm text-muted">Numbers below come from project checks/builds in this workspace.</p>
            </div>
            <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {EVIDENCE.map((item) => (
                <div key={item.label} className="rounded-xl border border-line bg-canvas p-5">
                  <p className="text-3xl font-semibold tracking-tight text-ink-strong tabular-nums">{item.value}</p>
                  <p className="mt-1 text-sm font-medium text-ink">{item.label}</p>
                  <p className="mt-2 text-xs leading-5 text-muted">{item.note}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="rounded-2xl border border-line bg-navy p-8 text-white sm:p-10">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-light">Explore the workspace</p>
            <h2 className="mt-3 max-w-2xl text-2xl font-semibold tracking-tight sm:text-3xl">
              Open the dashboard and inspect the analytics flow end to end.
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-200">
              Start at the executive overview, apply global filters, drill into modules, and review data quality and KPI definitions.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/overview"
                className="inline-flex h-11 items-center gap-2 rounded-lg bg-teal px-5 text-sm font-medium text-white transition hover:bg-teal-dark"
              >
                Enter dashboard <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                href="/kpi-glossary"
                className="inline-flex h-11 items-center gap-2 rounded-lg border border-white/20 px-5 text-sm font-medium text-white transition hover:bg-white/10"
              >
                View KPI glossary
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line px-4 py-6 text-center text-[11px] text-muted sm:px-6 lg:px-8">
        HOSPITAL 360 · Synthetic multi-hospital healthcare analytics · Educational project only · Not for clinical use
      </footer>
    </div>
  );
}
