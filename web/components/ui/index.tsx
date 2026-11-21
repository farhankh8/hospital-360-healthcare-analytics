'use client';

import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react';
import { AlertTriangle, Inbox, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SelectOption } from '@/lib/types';

export function Card({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'rounded-md border border-line bg-surface shadow-card transition-colors',
        className,
      )}
      {...props}
    >
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
        <h3 className="text-sm font-semibold tracking-tight text-ink-strong">{title}</h3>
        {subtitle && <p className="mt-1 text-xs leading-relaxed text-muted">{subtitle}</p>}
      </div>
      {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
    </div>
  );
}

export function Button({
  className,
  variant = 'secondary',
  size = 'sm',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md';
}) {
  return (
    <button
      type="button"
      className={cn(
        'inline-flex items-center justify-center gap-1.5 rounded-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/30 disabled:cursor-not-allowed disabled:opacity-45',
        size === 'sm' ? 'h-8 px-3 text-xs' : 'h-9 px-4 text-sm',
        variant === 'primary' && 'bg-teal text-white hover:bg-teal-dark',
        variant === 'secondary' && 'border border-line bg-surface text-ink hover:border-teal/40 hover:bg-surface-hover',
        variant === 'ghost' && 'text-muted hover:bg-surface-hover hover:text-ink',
        variant === 'danger' && 'border border-critical/30 bg-critical-light text-critical hover:bg-critical/10',
        className,
      )}
      {...props}
    />
  );
}

export function Badge({
  children,
  tone = 'neutral',
  className,
}: {
  children: ReactNode;
  tone?: 'neutral' | 'success' | 'warning' | 'critical' | 'info' | 'teal' | 'positive' | 'negative';
  className?: string;
}) {
  const tones: Record<string, string> = {
    neutral: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200',
    success: 'bg-success-light text-success',
    positive: 'bg-success-light text-success',
    warning: 'bg-warning-light text-warning',
    critical: 'bg-critical-light text-critical',
    negative: 'bg-critical-light text-critical',
    info: 'bg-info-light text-info',
    teal: 'bg-teal-light text-teal',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-sm px-2 py-0.5 text-[11px] font-semibold leading-5',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('h-4 w-4 animate-spin text-muted', className)} aria-label="Loading" />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-sm bg-slate-200/80 dark:bg-slate-700/60', className)} />;
}

export function EmptyState({
  message = 'No data available',
  hint,
  className,
  action,
}: {
  message?: string;
  hint?: string;
  className?: string;
  action?: ReactNode;
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-2 px-6 py-12 text-center', className)}>
      <div className="rounded-full bg-surface-alt p-3 ring-1 ring-line">
        <Inbox className="h-5 w-5 text-muted" />
      </div>
      <p className="text-sm font-medium text-ink">{message}</p>
      {hint && <p className="max-w-sm text-xs leading-relaxed text-muted">{hint}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  message = 'Something went wrong',
  onRetry,
  className,
}: {
  message?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-2 px-6 py-12 text-center', className)}>
      <div className="rounded-full bg-critical-light p-3 ring-1 ring-critical/10">
        <AlertTriangle className="h-5 w-5 text-critical" />
      </div>
      <p className="text-sm font-medium text-ink">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 rounded-sm border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink transition hover:border-teal/40 hover:text-teal"
        >
          Retry
        </button>
      )}
    </div>
  );
}

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label?: string;
  options: SelectOption[];
  placeholder?: string;
}

export function Select({ label, options, placeholder, className, id, ...props }: SelectProps) {
  const selectId = id || (label ? label.toLowerCase().replace(/[^a-z0-9]+/g, '-') : undefined);
  return (
    <label className={cn('flex flex-col gap-1', className)} htmlFor={selectId}>
      {label && <span className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</span>}
      <select
        id={selectId}
        aria-label={label ?? props['aria-label'] ?? props.name}
        className="h-9 rounded-sm border border-line bg-surface px-2.5 text-xs text-ink outline-none transition focus:border-teal focus:ring-2 focus:ring-teal/15 disabled:bg-surface-alt disabled:text-slate-600 disabled:opacity-100"
        {...props}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'h-9 rounded-sm border border-line bg-surface px-3 text-xs text-ink outline-none transition placeholder:text-muted-soft focus:border-teal focus:ring-2 focus:ring-teal/15',
        className,
      )}
      {...props}
    />
  );
}

export function Delta({
  value,
  tone,
  className,
}: {
  value: string;
  tone: 'positive' | 'negative' | 'neutral';
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-[11px] font-semibold tabular-nums',
        tone === 'positive' && 'bg-success-light text-success',
        tone === 'negative' && 'bg-critical-light text-critical',
        tone === 'neutral' && 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
        className,
      )}
    >
      {value}
    </span>
  );
}

export function IconButton({ className, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className={cn(
        'inline-flex h-8 w-8 items-center justify-center rounded-sm border border-line bg-surface text-muted transition hover:border-teal/40 hover:text-teal disabled:opacity-50',
        className,
      )}
    >
      {children}
    </button>
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
    'h-9 w-full rounded-sm border border-line bg-surface px-2.5 text-xs text-ink outline-none transition focus:border-teal focus:ring-2 focus:ring-teal/15';
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <input
        type="date"
        aria-label="Date from"
        value={from}
        max={to || undefined}
        onChange={(event) => onFromChange(event.target.value)}
        className={inputClass}
      />
      <span className="text-xs text-muted">to</span>
      <input
        type="date"
        aria-label="Date to"
        value={to}
        min={from || undefined}
        onChange={(event) => onToChange(event.target.value)}
        className={inputClass}
      />
    </div>
  );
}

export function PageHeading({
  title,
  description,
  badge,
}: {
  title: string;
  description?: string;
  badge?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold tracking-tight text-ink-strong">{title}</h1>
          {badge}
        </div>
        {description && <p className="mt-1 max-w-3xl text-sm leading-relaxed text-muted">{description}</p>}
      </div>
    </div>
  );
}
