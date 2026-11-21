# Before / After — HOSPITAL 360 UI Redesign

## Scope
- Branch: `feature/ui-redesign`
- Baseline: Phase 0 captures in `docs/ui/before/` (2026-11-21)
- After: captures in `docs/ui/after/` (2026-11-21)
- Viewports: 1440x900 and 390x844, full-page screenshots
- Pages: 21 blueprint routes

## Design direction
- Calm, clinical, trustworthy, data-dense enterprise healthcare analytics.
- Restrained navy/teal/neutral palette; semantic color only for meaning.
- Signature detail: thin teal status rail on KPI cards.
- Inter via `next/font`, tabular numerals, token-driven light/dark themes.

## Key improvements
- **Design tokens**: CSS variable token system (`globals.css`) mapped through Tailwind (`tailwind.config.ts`), including dark mode overrides and legacy compatibility.
- **Core primitives**: refreshed Card/Button/Badge/Delta/Empty/Error/Skeleton, hardened Select a11y, DateRange presets, Tabs, Tooltip, MultiSelect.
- **Shells**: tokenized DataTable and DrilldownDrawer shells; FilterBar/AppShell/ChartContainer polished for consistency and dark-mode compatibility.
- **Charts**: dark-aware ECharts theme in `web/lib/chart.ts`; ChartContainer passes theme; EChart toolbox themed.
- **A11y**: fixed select-name/contrast regressions; labeled raw selects/inputs; visible focus ring; preserved data-testid/aria behavior.
- **States**: loading/error/empty states preserved and styled through shared primitives.

## Evidence
- Before screenshots: `docs/ui/before/*.png`
- After screenshots: `docs/ui/after/*.png`
- Checks (2026-11-21): `pytest 159 passed, 2 warnings`; `ruff check .` pass; `npm run lint` pass; `npx tsc --noEmit` pass; `npm run build` pass; Playwright `38 passed, 0 failed`.

## Known limits
- This pass focuses on shared design system, shells, charts, token sweep, and a11y/regression safety. Some page-specific visual refinements can continue in follow-up PRs.
- No backend/API/SQL/KPI/data/generator changes. No deployment performed.
