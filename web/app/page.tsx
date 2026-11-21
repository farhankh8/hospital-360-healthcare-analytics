'use client';

import { useState, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Activity, ArrowRight, Building2, Database, Lock, Mail, ShieldCheck } from 'lucide-react';

const HIGHLIGHTS = [
  { icon: Building2, label: '21 analytics modules', detail: 'Operations, finance, quality, and workforce' },
  { icon: Database, label: 'Synthetic data only', detail: 'Safe for demos, learning, and portfolio use' },
  { icon: ShieldCheck, label: 'Verified quality gates', detail: 'Pytest, Ruff, TypeScript, Playwright checks' },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    if (!email.trim() || !password.trim()) {
      setError('Enter email and password to continue.');
      return;
    }
    setLoading(true);
    try {
      localStorage.setItem('hospital360_auth', '1');
      localStorage.setItem('hospital360_user', email.trim());
    } catch {
      // localStorage may be unavailable; still allow demo entry.
    }
    router.push('/overview');
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="absolute inset-x-0 top-0 h-px bg-line" aria-hidden="true" />

      <div className="relative grid w-full max-w-5xl overflow-hidden rounded-2xl border border-line bg-surface shadow-pop lg:grid-cols-[1.05fr_0.95fr]">
        <section className="flex flex-col justify-between border-b border-line p-8 lg:border-b-0 lg:border-r lg:p-10">
          <div>
            <div className="inline-flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-navy text-base font-bold text-white shadow-card">H</div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal">Healthcare Intelligence</p>
                <h1 className="text-2xl font-semibold tracking-tight text-ink-strong">HOSPITAL 360</h1>
              </div>
            </div>

            <p className="mt-6 max-w-xl text-sm leading-7 text-muted">
              A synthetic multi-hospital analytics platform for operations, finance, quality, workforce, and patient-flow
              monitoring. Explore executive KPIs, drill-downs, and data quality in one workspace.
            </p>

            <div className="mt-8 grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
              {HIGHLIGHTS.map(({ icon: Icon, label, detail }) => (
                <div key={label} className="rounded-xl border border-line bg-surface-alt/60 p-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-teal-light text-teal-dark">
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-ink-strong">{label}</p>
                      <p className="mt-0.5 text-xs leading-5 text-muted">{detail}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-8 flex items-center gap-2 text-[11px] text-muted">
            <Activity className="h-3.5 w-3.5 text-teal" aria-hidden="true" />
            <span>Educational project. Synthetic data only. Not for clinical use.</span>
          </div>
        </section>

        <section className="p-8 lg:p-10">
          <div className="mx-auto max-w-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Sign in</p>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-ink-strong">Access the dashboard</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              Use any demo credentials to enter the analytics workspace.
            </p>

            <form className="mt-8 space-y-4" onSubmit={onSubmit} noValidate>
              <label className="block">
                <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wide text-muted">Email</span>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-soft" aria-hidden="true" />
                  <input
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@hospital360.demo"
                    className="h-11 w-full rounded-lg border border-line bg-surface px-10 text-sm text-ink outline-none transition placeholder:text-muted-soft focus:border-teal focus:ring-2 focus:ring-teal/15"
                    aria-label="Email"
                  />
                </div>
              </label>

              <label className="block">
                <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wide text-muted">Password</span>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-soft" aria-hidden="true" />
                  <input
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter demo password"
                    className="h-11 w-full rounded-lg border border-line bg-surface px-10 text-sm text-ink outline-none transition placeholder:text-muted-soft focus:border-teal focus:ring-2 focus:ring-teal/15"
                    aria-label="Password"
                  />
                </div>
              </label>

              {error && (
                <p className="rounded-md border border-critical/20 bg-critical-light px-3 py-2 text-xs text-critical" role="status">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-navy px-4 text-sm font-medium text-white transition hover:bg-navy-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/30 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {loading ? 'Entering dashboard...' : 'Sign in to HOSPITAL 360'}
                {!loading && <ArrowRight className="h-4 w-4" aria-hidden="true" />}
              </button>

              <p className="text-center text-[11px] leading-5 text-muted">
                Demo access: any email and password will open the workspace.
              </p>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}
