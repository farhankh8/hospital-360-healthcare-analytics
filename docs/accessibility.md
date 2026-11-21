# HOSPITAL 360 - Accessibility Audit (Phase 8)

**Date:** 2026-11-21  
**Scope:** Overview (`/overview`), Finance (`/finance`), Data Explorer (`/explorer`), Data Quality (`/data-quality`)  
**Tool:** `@axe-core/playwright` with WCAG 2A/2AA/21A/21AA tags  
**Browsers:** Chromium desktop + Pixel 5 mobile (Playwright projects)

## Result

| Page | Chromium | Mobile (Pixel 5) | Serious/Critical |
|---|---|---|---:|
| `/overview` | PASS | PASS | 0 |
| `/finance` | PASS | PASS | 0 |
| `/explorer` | PASS | PASS | 0 |
| `/data-quality` | PASS | PASS | 0 |

Automated test: `web/e2e/a11y.spec.ts` (8 tests passed).

## Remediations applied
- Added/normalized accessible names for select controls (`Select` fallback aria-label).
- Fixed hospital filter button accessible-name mismatch (visible text included in aria-label).
- Improved color contrast for muted text/labels on light backgrounds and sidebar section labels on navy.
- Kept existing keyboard/focus-visible styles and semantic landmarks.

## Mobile viewport
Playwright config includes a `mobile` project using Pixel 5 viewport/device settings; all e2e specs run under chromium and mobile projects.

## Notes
- Automated axe checks do not cover all WCAG criteria; manual keyboard/screen-reader review remains recommended.
- No serious/critical axe violations found on the four audited pages at time of test.
