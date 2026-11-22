# Landing Page Audit

Date: 2026-11-22
Branch: feature/landing-polish
Scope: web/app/page.tsx landing page claims vs measured sources

## Stats / Claims

| Claim on landing page | Value shown | Real source | Status |
|---|---:|---|---|
| Analytics modules | 21 | web/lib/page-configs.ts has 21 page configs; web/e2e/routes.spec.ts covers 21 blueprint routes | **Mismatch fixed**: module card list had 19 entries and omitted Methodology (and Hospital Profile was not represented as a module card). Updated to include all 21 configured pages. |
| Pytest checks | 159, 2 warnings | python -m pytest --collect-only -q collected 159 tests (2026-11-22). Prior measured run reported 159 passed, 2 warnings. | **Source needs build-time wiring**. Count is currently hard-coded. |
| Playwright checks | 38 | 
px playwright test --config=e2e/playwright.config.ts --list reports Total: 38 tests in 7 files (2026-11-22). | **Correct number**. Prompt note said "last audit said 22"; actual current Playwright suite is 38. Hard-coded value remains a source issue. |
| Static build pages | 24/24 | Latest measured 
ext build output (2026-11-22) reported 24/24 static pages. | **Source needs build-time wiring**. Hard-coded. |
| Hospitals | 10 | data/manifests/pipeline_RUN_20261121_001.json ronze.tables.dim_hospital.row_count=10 | **Correct**, but hard-coded. |
| Patients | 15,200 | Manifest ronze.tables.dim_patient.row_count=15200 | **Correct**, but hard-coded. |
| Encounters | 82,000 | Manifest ronze.tables.encounters.row_count=82000 | **Correct**, but hard-coded. |
| Appointments | 136,800 | Manifest ronze.tables.appointments.row_count=136800 | **Correct**, but hard-coded. |
| Bronze rows | 1.59M / 1,588,637 across 41 tables | Manifest 	otals.source_records=1588637, bronze has 41 tables | **Correct**, but hard-coded. |
| Gold tables | 12 | Manifest gold tables count needs canonical confirmation from manifest gold.tables/duckdb outputs; prior measured value used in UI. | **Verify in Phase 2**; keep only manifest-derived value. |

## Module/Content Mismatches

| Area | Issue | Fix |
|---|---|---|
| Modules list | Said "21 modules" but rendered 19 cards; missing Methodology and Hospital Profile. | Add missing modules; make rendered count match claim/source. |
| Finance card | Said "Revenue, cost, margin, and payer-mix views." | Finance config is Finance & Revenue: "Gross and net revenue, collections, receivables and revenue leakage." Claims page covers payer mix/denials. Updated card to match actual page scope. |
| Claims card | "Claim status..." is broad | Kept aligned with claims config: submission, adjudication, denials, payer mix, appeals. |
| Workforce card | Said "overtime" but config emphasizes staffing/shift coverage/overtime/absence/workforce cost | Adjusted to match config. |
| Repeated stats | Pytest/Playwright/modules repeated in hero and Evidence. | Planned for Phase 3/8. |
| No screenshots/GitHub/demo | Hero has text-only preview. | Planned for Phase 3/4. |
| Data scale vs Evidence overlap | Both sections present measured counts. | Planned for Phase 8 merge/differentiation. |

## Verified Counts (2026-11-22)

- Pytest collected: **159 tests** (python -m pytest --collect-only -q)
- Playwright listed: **38 tests in 7 files** (
px playwright test --config=e2e/playwright.config.ts --list)
- Blueprint routes: **21 routes** in web/e2e/routes.spec.ts
- Page configs: **21** in web/lib/page-configs.ts
- Manifest: pipeline_RUN_20261121_001.json, 10 hospitals, 15,200 patients, 82,000 encounters, 136,800 appointments, 1,588,637 bronze source records, 1,585,844 valid, 2,793 quarantined, 41 bronze tables.
