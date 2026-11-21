# Phase 8 Report — UI Redesign

## Scope
- Branch: `feature/ui-redesign`
- Date: 2026-11-21
- No backend/API/SQL/KPI/data/generator changes. No deployment. No PR merge.

## Playwright
- Command: `cd web && npx playwright test --config=e2e/playwright.config.ts`
- Result: **38 passed, 0 failed** (2.8m)
- Coverage includes: a11y (overview/finance/explorer/data-quality), analytics flows, glossary, hospitals/profile, patient journey, pipeline, all 21 routes smoke, mobile viewport checks.

## Axe / Accessibility
- Axe checks in `web/e2e/a11y.spec.ts` pass for overview, finance, explorer, data-quality on chromium and mobile.
- Fixed regressions during Phase 1: select-name (missing accessible names on FilterBar/Explorer selects) and color-contrast (muted text/select disabled state).
- Added/verified labels and aria attributes for FilterBar, Explorer, Analytics, KPI Glossary controls.

## Bundle / Build
- Command: `cd web && npm run build`
- Result: **pass** (Next.js 15.5.29, static generation 24/24)
- Key route sizes from build output:
  - `/overview` 210 B / First Load JS 154 kB
  - `/explorer` 2.83 kB / 147 kB
  - `/kpi-glossary` 2.84 kB / 130 kB
  - `/methodology` 3.3 kB / 109 kB
  - `/patient-journey` 3.84 kB / 131 kB
  - `/pipeline` 376 kB / 524 kB (largest route; ECharts-heavy)
  - Shared First Load JS: 103 kB

## Quality gates
- `python -m pytest -q`: **159 passed, 2 warnings**
- `python -m ruff check .`: **pass**
- `web npm run lint`: **pass**
- `web npx tsc --noEmit`: **pass**
- `web npm run build`: **pass**
- `web npx playwright test --config=e2e/playwright.config.ts`: **38 passed**

## Risks / Follow-ups
- `next build` corrupts a running `next dev` .next cache; restart dev after build.
- Pipeline route remains heavy due to ECharts/data payloads; consider further code-splitting in a follow-up.
- Some page-level visual refinements can continue, but shared system, shells, charts, a11y, and tests are green.
