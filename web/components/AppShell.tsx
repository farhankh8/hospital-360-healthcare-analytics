'use client';

import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  Activity,
  BedDouble,
  BookOpen,
  Building2,
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  Database,
  FileCheck2,
  FlaskConical,
  GitBranch,
  HeartPulse,
  Info,
  LayoutDashboard,
  Menu,
  Moon,
  Package,
  Pill,
  Route as RouteIcon,
  Search,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Sun,
  UserRound,
  UsersRound,
  WalletCards,
  X,
  type LucideIcon,
} from 'lucide-react';
import { useFilters } from '@/lib/filters';
import { useTheme } from '@/components/ThemeProvider';
import { type PageSlug } from '@/lib/page-configs';
import { pages } from '@/lib/page-configs';
import { NAV_GROUPS, type PageConfig } from '@/lib/types';
import { cn } from '@/lib/utils';
import { FilterBar } from './FilterBar';
import { Badge } from './ui';

const ICONS: Record<PageSlug, LucideIcon> = {
  overview: LayoutDashboard,
  hospitals: Building2,
  hospitalsProfile: HeartPulse,
  appointments: CalendarClock,
  emergency: Siren,
  inpatient: BedDouble,
  procedures: Activity,
  diagnostics: FlaskConical,
  pharmacy: Pill,
  finance: WalletCards,
  claims: FileCheck2,
  workforce: UsersRound,
  inventory: Package,
  experience: HeartPulse,
  quality: ShieldCheck,
  explorer: Database,
  patientJourney: RouteIcon,
  dataQuality: ShieldAlert,
  pipeline: GitBranch,
  kpiGlossary: BookOpen,
  methodology: Info,
};

function navHref(page: PageConfig, firstHospitalId?: string): string {
  if (!page.path.includes('[id]')) return page.path;
  return firstHospitalId ? page.path.replace('[id]', firstHospitalId) : '/hospitals';
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { filters, hospitals, compare, drawerOpen, setDrawerOpen } = useFilters();
  const { theme, toggleTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [search, setSearch] = useState('');
  const profileRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) setProfileOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const grouped = useMemo(
    () =>
      NAV_GROUPS.map((group) => ({
        group,
        items: (Object.values(pages) as PageConfig[]).filter((page) => page.navGroup === group),
      })),
    [],
  );

  const hospitalLabel = filters.hospital_ids.length
    ? filters.hospital_ids.length === 1
      ? hospitals.find((hospital) => hospital.value === filters.hospital_ids[0])?.label || filters.hospital_ids[0]
      : `${filters.hospital_ids.length} hospitals`
    : 'All hospitals';

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    if (!search.trim()) return;
    router.push(`/explorer?search=${encodeURIComponent(search.trim())}`);
  };

  const sidebar = (
    <nav className="flex h-full flex-col">
      <div className={cn('flex h-16 items-center gap-2 border-b border-white/10 px-4', collapsed && 'justify-center px-2')}>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-teal text-sm font-bold text-white">H</div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-wide text-white">HOSPITAL 360</p>
            <p className="truncate text-[10px] text-slate-400">Healthcare intelligence</p>
          </div>
        )}
        <button
          type="button"
          onClick={() => setCollapsed((value) => !value)}
          className="ml-auto hidden rounded p-1 text-slate-400 hover:bg-white/10 hover:text-white lg:block"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-4">
        {grouped.map(({ group, items }) => (
          <div key={group} className="mb-5">
            {!collapsed && <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-slate-300">{group}</p>}
            {collapsed && <div className="mx-auto mb-2 h-px w-8 bg-white/10" />}
            <ul className="space-y-0.5">
              {items.map((page) => {
                const Icon = ICONS[page.slug as PageSlug] || Activity;
                const href = navHref(page, hospitals[0]?.value);
                const active = pathname === href || (page.path.includes('[id]') && /^\/hospitals\/[^/]+$/.test(pathname)) || pathname === page.path;
                return (
                  <li key={page.slug}>
                    <Link
                      href={href}
                      title={page.title}
                      className={cn(
                        'flex items-center gap-3 rounded-md px-3 py-2 text-xs transition',
                        collapsed && 'justify-center px-2',
                        active ? 'bg-teal/15 font-semibold text-white' : 'text-slate-300 hover:bg-white/5 hover:text-white',
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      {!collapsed && <span className="truncate">{page.title}</span>}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>

      {!collapsed && (
        <div className="border-t border-white/10 p-4">
          <p className="text-[10px] leading-relaxed text-slate-400">
            Synthetic data only. Not a clinical system.
          </p>
        </div>
      )}
    </nav>
  );

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-teal focus:px-3 focus:py-2 focus:text-sm focus:text-white">Skip to main content</a>
      <aside aria-label="Primary navigation" className={cn('fixed inset-y-0 left-0 z-40 hidden bg-navy transition-all lg:block', collapsed ? 'w-[72px]' : 'w-[260px]')}>{sidebar}</aside>

      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <button type="button" className="absolute inset-0 bg-slate-900/40" onClick={() => setMobileNavOpen(false)} aria-label="Close navigation" />
          <aside className="relative h-full w-[270px] bg-navy shadow-drawer">
            <button type="button" onClick={() => setMobileNavOpen(false)} className="absolute right-2 top-4 z-10 rounded p-1 text-slate-300" aria-label="Close navigation">
              <X className="h-5 w-5" />
            </button>
            {sidebar}
          </aside>
        </div>
      )}

      <div className={cn('transition-all', collapsed ? 'lg:pl-[72px]' : 'lg:pl-[260px]')}>
        <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur">
          <div className="flex h-16 items-center gap-3 px-4 lg:px-6">
            <button type="button" onClick={() => setMobileNavOpen(true)} className="rounded p-1.5 text-slate-500 hover:bg-canvas lg:hidden" aria-label="Open navigation">
              <Menu className="h-5 w-5" />
            </button>

            <form onSubmit={submitSearch} className="relative max-w-sm flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search records…"
                aria-label="Search records"
                className="h-9 w-full rounded-md border border-line bg-canvas/60 pl-9 pr-3 text-xs outline-none focus:border-teal focus:bg-white focus:ring-2 focus:ring-teal/15"
              />
            </form>

            <div className="ml-auto flex items-center gap-2">
              <div className="hidden items-center gap-2 rounded-md border border-line px-2.5 py-1.5 text-xs text-slate-600 md:flex">
                <CalendarClock className="h-3.5 w-3.5 text-teal" />
                <span>{filters.date_from || '—'} → {filters.date_to || '—'}</span>
              </div>
              <div className="hidden items-center gap-2 rounded-md border border-line px-2.5 py-1.5 text-xs text-slate-600 sm:flex">
                <Building2 className="h-3.5 w-3.5 text-teal" />
                <span className="max-w-[140px] truncate">{hospitalLabel}</span>
              </div>
              <button
                type="button"
                onClick={toggleTheme}
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-line bg-surface text-muted transition hover:bg-surface-hover hover:text-ink"
                aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
                title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
              >
                {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>
              {compare && <Badge tone="info">Compare</Badge>}
              <div className="relative" ref={profileRef}>
                <button
                  type="button"
                  onClick={() => setProfileOpen((value) => !value)}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-navy text-white transition hover:bg-navy-light"
                  aria-label="Profile menu"
                >
                  <UserRound className="h-4 w-4" />
                </button>
                {profileOpen && (
                  <div className="absolute right-0 top-11 z-40 w-52 rounded-lg border border-line bg-white p-2 shadow-lg">
                    <p className="px-2 py-1 text-[10px] font-semibold uppercase text-slate-400">Synthetic workspace</p>
                    <Link href="/kpi-glossary" className="block rounded px-2 py-1.5 text-xs text-ink hover:bg-canvas">KPI glossary</Link>
                    <Link href="/methodology" className="block rounded px-2 py-1.5 text-xs text-ink hover:bg-canvas">Methodology</Link>
                    <Link href="/data-quality" className="block rounded px-2 py-1.5 text-xs text-ink hover:bg-canvas">Data quality</Link>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="border-t border-line px-4 py-2.5 lg:px-6">
            <FilterBar />
          </div>
        </header>

        <main id="main-content" tabIndex={-1} className="mx-auto w-full max-w-[1600px] px-4 py-6 outline-none lg:px-6">{children}</main>
        <footer className="border-t border-line px-4 py-4 text-center text-[11px] text-slate-600 lg:px-6">
          HOSPITAL 360 · Educational analytics project using entirely synthetic data · Not for clinical use
        </footer>
      </div>

      {drawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button type="button" className="absolute inset-0 bg-slate-900/40" onClick={() => setDrawerOpen(false)} aria-label="Close filters" />
          <div className="absolute inset-y-0 right-0 w-full max-w-sm overflow-y-auto bg-surface p-5 shadow-pop">
            <p className="mb-4 text-sm font-semibold text-navy">Global filters</p>
            <FilterBar inDrawer />
          </div>
        </div>
      )}
    </div>
  );
}
