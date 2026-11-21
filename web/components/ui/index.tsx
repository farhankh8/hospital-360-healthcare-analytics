'use client';

import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react';
import { AlertTriangle, Inbox, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SelectOption } from '@/lib/types';

export function Card({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('rounded-lg border border-line bg-white shadow-card', className)} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
  className,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4', className)}>
      <div className="min-w-0">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {subtitle && <p className="mt-1 text-xs text-slate-600">{subtitle}</p>}
      </div>
      {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
    </div>
  );
}

type BadgeTone = 'neutral' | 'positive' | 'negative' | 'warning' | 'info';

const badgeStyles: Record<BadgeTone, string> = {
  neutral: 'bg-slate-100 text-slate-600',
  positive: 'bg-success-light text-success',
  negative: 'bg-critical-light text-critical',
  warning: 'bg-warning-light text-warning',
  info: 'bg-teal-light text-teal-dark',
};

export function Badge({ tone = 'neutral', children, className }: { tone?: BadgeTone; children: ReactNode; className?: string }) {
  return <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium', badgeStyles[tone], className)}>{children}</span>;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded bg-slate-100', className)} aria-hidden="true" />;
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('h-4 w-4 animate-spin', className)} aria-hidden="true" />;
}

export function EmptyState({ message = 'No data available', hint, className }: { message?: string; hint?: string; className?: string }) {
  return (
    <div className={cn('flex min-h-[120px] flex-col items-center justify-center gap-2 px-4 py-8 text-center', className)}>
      <Inbox className="h-6 w-6 text-slate-600" aria-hidden="true" />
      <p className="text-sm font-medium text-slate-600">{message}</p>
      {hint && <p className="max-w-sm text-xs text-slate-600">{hint}</p>}
    </div>
  );
}

export function ErrorState({
  message = 'Unable to load data from the API.',
  onRetry,
  className,
}: {
  message?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div className={cn('flex min-h-[120px] flex-col items-center justify-center gap-2 px-4 py-8 text-center', className)} role="alert">
      <AlertTriangle className="h-6 w-6 text-critical" aria-hidden="true" />
      <p className="max-w-md text-sm font-medium text-critical">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="text-xs font-semibold text-navy underline underline-offset-2">
          Try again
        </button>
      )}
    </div>
  );
}

export function Select({
  options,
  placeholder,
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { options: SelectOption[]; placeholder?: string }) {
  const ariaLabel = props['aria-label'] ?? props['aria-labelledby'] ? undefined : (placeholder || 'Select option');
  return (
    <select
      aria-label={ariaLabel}
      {...props}
      className={cn(
        'h-9 w-full rounded-md border border-line bg-white px-2.5 text-xs text-ink outline-none transition focus:border-teal focus:ring-2 focus:ring-teal/15 disabled:cursor-not-allowed disabled:bg-slate-50',
        className,
      )}
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

export function DateRangePicker({
  from,
  to,
  onFromChange,
  onToChange,
  className,
}: {
  from: string;
  to: string;
  onFromChange: (value: string) => void;
  onToChange: (value: string) => void;
  className?: string;
}) {
  const inputClass =
    'h-9 w-full rounded-md border border-line bg-white px-2.5 text-xs text-ink outline-none focus:border-teal focus:ring-2 focus:ring-teal/15';
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <input type="date" aria-label="Date from" value={from} max={to || undefined} onChange={(event) => onFromChange(event.target.value)} className={inputClass} />
      <span className="text-xs text-slate-600">to</span>
      <input type="date" aria-label="Date to" value={to} min={from || undefined} onChange={(event) => onToChange(event.target.value)} className={inputClass} />
    </div>
  );
}

export function IconButton({ className, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className={cn(
        'inline-flex h-8 w-8 items-center justify-center rounded-md border border-line bg-white text-slate-600 transition hover:border-teal hover:text-teal disabled:opacity-50',
        className,
      )}
    >
      {children}
    </button>
  );
}

export function PageHeading({ title, description, badge }: { title: string; description?: string; badge?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold tracking-tight text-navy">{title}</h1>
          {badge}
        </div>
        {description && <p className="mt-1 max-w-3xl text-sm text-slate-600">{description}</p>}
      </div>
    </div>
  );
}
