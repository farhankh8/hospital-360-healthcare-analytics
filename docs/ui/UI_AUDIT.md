# UI Audit — HOSPITAL 360 (Phase 0 Baseline)

**Date:** 2026-11-21  
**Branch:** `feature/ui-redesign` (from `feature/final-completion`)  
**Baseline screenshots:** `docs/ui/before/*-{1440,390}.png` (11 pages × 2 viewports)  
**Scope:** Code-based audit + baseline capture. Unslop skill not installed in `.claude/skills`; manual audit performed.

## Summary

The app is functional and coherent, but it reads as a competent default dashboard rather than a premium enterprise healthcare product. The main issues are weak visual hierarchy, default ECharts styling, dense/uneven card rhythm, limited design-token depth, and a filter bar that competes with content.

## Findings (by area)

### 1. Design tokens / theme foundation
- **`web/tailwind.config.ts`**: limited token set (navy/teal/success/warning/critical/canvas/ink/line, one shadow, one radius extension). No neutral scale, no semantic foreground/background pairs, no z-index scale, no spacing/radius system, no dark mode tokens.
- **`web/app/globals.css`**: hardcoded colors (`#f4f7fa`, `#1e293b`, focus outline `#0f766e`); no CSS variable token layer; no dark theme; font family duplicated instead of tokenized.
- **Impact**: hard to maintain consistency; dark mode and chart theming require refactor.

### 2. Typography & numbers
- **Font**: Inter referenced in Tailwind/globals but not loaded via `next/font` (runtime/external fetch risk; inconsistent rendering).
- **Hierarchy**: page titles, section labels, KPI values, captions lack a deliberate scale/letter-spacing system. KPI value is `text-2xl font-semibold` (`KpiCard.tsx`) - adequate but not premium.
- **Numbers**: not consistently tabular (`font-variant-numeric: tabular-nums`) across KPI cards, tables, charts, tooltips. Tables do not consistently right-align numeric columns.

### 3. App shell & navigation (`web/components/AppShell.tsx`)
- Sidebar is functional but visually heavy; active state is subtle; collapse behavior exists but no tooltip-on-collapsed affordance polish; icon rail spacing can be tighter.
- Header mixes search, date/hospital pills, compare badge, profile - useful but cluttered; no theme toggle; no global breadcrumb/title hierarchy beyond page content.
- Filter bar is always visible and dense (`FilterBar.tsx`); on desktop it wraps awkwardly; mobile drawer exists but the bar still feels heavy.
- Footer disclaimer present (good) but could be calmer/smaller.

### 4. KPI cards (`web/components/KpiCard.tsx`)
- Good: value, previous, abs change, % change, trend icon, sparkline, tooltip, click-through, loading/error/empty states.
- Issues: card density is high; 10-12 KPI grids feel overwhelming (no primary/secondary grouping). Sparkline is acceptable but could be quieter. Delta pill styling is text-only, not a clear semantic pill. Status rail/signature detail missing. Layout jump risk in some states.

### 5. Charts (`web/components/EChart.tsx`, `web/components/ChartContainer.tsx`, `web/lib/chart.ts`)
- Default/near-default ECharts look: generic grid, axis, legend, tooltip styling; toolbox icons are functional but visually noisy.
- Color palette not governed by a single design-system chart theme; dark mode unreadable without token-driven colors.
- Chart cards lack refined action menu (download/fullscreen/view data) - download exists, but presentation is basic.
- Heatmap/ranking polarity and legend clarity need verification per chart; some charts may have dense labels on mobile.

### 6. Tables (`web/components/DataTable.tsx`)
- Functional: search, sort, pagination, column visibility, export, loading/error/empty. Good baseline.
- Visual issues: header styling plain; no density toggle; no sticky header polish; row hover subtle but not premium; numeric alignment inconsistent; mobile horizontal scroll needs shadow hint; pagination footer could be clearer ("1-50 of 12,430").

### 7. Drilldown / drawers (`web/components/DrilldownDrawer.tsx`)
- Functional but visually utilitarian. Needs sectioned key-value layout, stronger header/badges, better timeline/related-record presentation, focus trap verification.

### 8. Filters (`web/components/FilterBar.tsx`, `web/lib/filters.tsx`, `web/lib/page-filters.ts`)
- Powerful but visually noisy. Many controls in one row; date range lacks presets; no active filter chips with remove; reset/export/compare compete for attention. Mobile drawer exists, but desktop needs a calmer single-row + popover pattern.

### 9. Page-specific issues
- **Overview**: information-dense but lacks clear “what changed” narrative; chart/grid hierarchy can be stronger.
- **Hospital Comparison**: metric selector exists; hospital selection/multi-select UX can be clearer with chips.
- **Hospital Profile**: header/tabs functional; needs stronger profile header card and underline tab styling.
- **Emergency**: flow visualization is chart/data-driven; could be clearer as stepper/Sankey-like flow.
- **Pipeline**: run detail/compare exist; stage diagram can be more visual with status dots/durations.
- **Data Quality**: has strong content; score/gauge and injected-vs-detected presentation can be more polished.
- **KPI Glossary/Methodology**: readable but long-form typography/TOC/formula blocks can be improved.
- **Data Explorer**: functional; toolbar/schema/records layout can be cleaner.
- **Patient Journey**: timeline exists; event-type color coding and filter chips can be improved.

### 10. Responsive / accessibility / motion
- Responsive classes exist, but 390px layouts need careful review for filter bar, KPI grids, charts, and table containers.
- Focus styles exist globally, but component-level focus rings/keyboard behavior need full pass.
- No `prefers-reduced-motion` handling. No dark mode. Axe serious/critical was previously addressed, but redesign risks regressions.

## Priority order

1. **Design tokens + typography + theme plumbing** (enables everything)
2. **ECharts theme + chart container** (largest visual lift)
3. **KPI card redesign** (most visible)
4. **App shell/filter bar** (first impression)
5. **Tables/drawers/states** (trust/usability)
6. **Page-specific polish** (21 pages)
7. **Dark mode, a11y, responsive, perf verification**

## Files inspected (primary)

- `web/tailwind.config.ts`, `web/app/globals.css`, `web/app/layout.tsx`
- `web/components/AppShell.tsx`, `web/components/FilterBar.tsx`
- `web/components/KpiCard.tsx`, `web/components/ChartContainer.tsx`, `web/components/EChart.tsx`, `web/lib/chart.ts`
- `web/components/DataTable.tsx`, `web/components/DrilldownDrawer.tsx`, `web/components/ui.tsx`
- `web/lib/page-configs.ts`, `web/lib/filters.tsx`