# Design System — HOSPITAL 360

## Tokens

Defined in `web/app/globals.css` as CSS variables (light default, `.dark` overrides) and mapped in `web/tailwind.config.ts`.

### Color
- **Canvas/Surface**: `canvas`, `surface`, `surface-alt`, `surface-hover`
- **Text**: `ink`/`ink-strong`, `muted`/`muted-soft`
- **Border**: `line`, `line-strong`
- **Brand**: `navy`, `teal` (+ soft/dark)
- **Semantic**: `success`, `warning`, `critical`, `info` (each with soft bg)
- **Rule**: color carries meaning. Green=favorable, red=unfavorable, amber=warning, grey=neutral, blue=info. Polarity reversed for lower-is-better metrics.

### Typography
- Font: Inter via `next/font/google` (`--font-inter`), self-hosted at build.
- Numeric: `font-variant-numeric: tabular-nums` on body; use `tabular-nums` on data.
- Scale: page title `text-xl font-semibold`, section/card title `text-sm font-semibold`, KPI value `text-kpi-sm`, labels `text-[11px] uppercase tracking-wide`, body `text-sm`, caption `text-xs`.

### Shape & depth
- Radius: `sm` 6px, `md` 10px, `lg` 14px (default 8px).
- Shadows: `shadow-card` (subtle), `shadow-pop` (overlay/dropdown). No heavy shadows.
- Borders: `border-line` default; avoid noisy borders.

### Spacing & layout
- 4px grid. Card padding `p-4`/`p-5`. Page max width `max-w-[1600px]`. Section gaps `gap-4`/`gap-6`.

### Motion
- 150-200ms transitions. `prefers-reduced-motion: reduce` disables animation/transition.

### Dark mode
- `ThemeProvider` sets `.dark` on `html`; persisted in `localStorage` key `h360-theme` with try/catch; defaults to `prefers-color-scheme`.
- Tokens switch via CSS vars; legacy class compat in globals for gradual migration.

## Core components (`web/components/ui/index.tsx`)

- **Card/CardHeader**: surface, border, subtle shadow, header with title/subtitle/action.
- **Button**: primary/secondary/ghost/danger, sm/md.
- **Badge**: neutral/success/warning/critical/info/teal (+ positive/negative aliases).
- **Delta**: compact trend pill with tone.
- **Skeleton/Spinner**: loading states.
- **EmptyState/ErrorState**: icon, message, hint, optional action/retry.
- **Select/Input**: labeled form controls, token-styled focus ring.
- **DateRangePicker/IconButton/PageHeading**: compatibility exports used by existing pages.

## Chart/theme guidance
- ECharts: muted grid, readable labels, max 6-8 categorical colors, subtle area, rounded bars, styled tooltip. Toolbox minimal; save/download in actions.
- Chart container: title/subtitle/definition, action area, loading/empty/error, benchmark badge.

## Accessibility
- Visible focus ring via `:focus-visible` teal outline.
- WCAG AA contrast target in light and dark.
- No color-only meaning: pair red/green with arrows/icons/text.
- Keyboard support for nav, filters, tables, drawers.