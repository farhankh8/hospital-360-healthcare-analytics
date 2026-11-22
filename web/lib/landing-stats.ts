export interface LandingStats {
  manifest_run_id?: string;
  manifest_path?: string;
  hospitals?: number;
  patients?: number;
  encounters?: number;
  appointments?: number;
  bronze_rows?: number;
  bronze_tables?: number;
  valid_records?: number;
  quarantined_records?: number;
  gold_tables?: number;
  doctors?: number;
  staff?: number;
  beds?: number;
  admissions?: number;
  lab_orders?: number;
  invoices?: number;
  claims?: number;
  pytest_collected?: number;
  playwright_tests?: number;
  generated_at?: string;
}

function readStats(): LandingStats {
  try {
    return require('./landing-stats.json') as LandingStats;
  } catch {
    return {};
  }
}

export const landingStats: LandingStats = readStats();

export function fmt(n?: number): string | null {
  if (typeof n !== 'number' || !Number.isFinite(n)) return null;
  return n.toLocaleString('en-US');
}

export function fmtCompact(n?: number): string | null {
  if (typeof n !== 'number' || !Number.isFinite(n)) return null;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2).replace(/\.?0+$/, '')}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(/\.0$/, '')}K`;
  return n.toLocaleString('en-US');
}
