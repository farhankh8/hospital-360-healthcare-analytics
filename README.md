# HOSPITAL 360 - Healthcare Intelligence & Operations Analytics Platform

## 1. Project title
**HOSPITAL 360** - a full-stack, multi-hospital healthcare analytics platform built on synthetic data.

## 2. Project overview
HOSPITAL 360 consolidates synthetic hospital operations data into an interactive analytics product covering executive, clinical, financial, workforce, supply chain, experience, quality, data explorer, data quality, and pipeline views. The system uses a reproducible Python/DuckDB pipeline, a FastAPI backend, and a Next.js frontend.

## 3. Business problem
Healthcare operational data is fragmented across systems, making it difficult for management to monitor performance, investigate root causes, and trust KPI consistency across hospitals and departments.

## 4. Solution
A unified analytics platform that:
- generates reproducible synthetic multi-hospital data,
- validates and quarantines data quality issues,
- serves KPI/chart/table APIs from DuckDB,
- presents 21 connected dashboard pages with global filters, drilldowns, exports, and glossary.

## 5. Features
- **21 frontend routes**: Overview, Hospitals, Comparison, Appointments, Emergency, Inpatient, Procedures, Diagnostics, Pharmacy, Finance, Claims, Workforce, Inventory, Experience, Quality, Explorer, Data Quality, Pipeline, Glossary, Hospital Profile, Patient Journey.
- **Global filters**: date range, hospital, department, specialty, doctor, payer, service category, diagnosis group; URL-synced.
- **API-driven analytics**: KPI/chart/table endpoints under /api/v1.
- **Data quality**: quarantine, rule failures, DQ score, lineage, manifest/run history.
- **Exports**: CSV export endpoints with configured export limit.
- **Accessibility/perf checks**: axe serious/critical checks, Playwright e2e, measured local performance report.

## 6. Screenshots
Screenshots can be captured with the rerunnable script:

`ash
python scripts/capture_screenshots.py --base-url http://127.0.0.1:3000 --out docs/screenshots
`

Required shots: overview, finance, data-quality, explorer, patient-journey, pipeline. Store generated PNGs in docs/screenshots/.

## 7. Architecture
`mermaid
flowchart LR
  A[Synthetic CSV Generator] --> B[Bronze Parquet]
  B --> C[Silver Validation/Quarantine]
  C --> D[Gold DuckDB Tables]
  D --> E[FastAPI /api/v1]
  E --> F[Next.js 15 Dashboard]
  C --> G[DQ Results/Manifests]
  G --> E
  G --> F
`

Detailed docs: [docs/architecture.md](docs/architecture.md), [docs/data_model.md](docs/data_model.md).

## 8. Technology stack
| Layer | Technology | Evidence |
|---|---|---|
| Frontend | Next.js 15.5, React 19, TypeScript, Tailwind, ECharts 6 | web/package.json |
| Backend | FastAPI, Pydantic, Uvicorn | pi/ |
| Data | DuckDB, Parquet, Pandas/NumPy | tl/, data/ |
| Testing | pytest, Playwright, axe-core | 	ests/, web/e2e/ |
| CI | GitHub Actions | .github/workflows/ci.yml |

## 9. Dataset
Synthetic only; no real hospital names/PHI. Current measured pipeline manifest (data/manifests/pipeline_RUN_20261121_001.json):

| Metric | Value |
|---|---:|
| Source records | 1,588,637 |
| Valid records | 1,585,844 |
| Quarantined records | 2,793 |
| Quarantine rule failures | 2,833 |
| Tables created | 58 |
| DQ score | 100.0 |

## 10. Data model
Bronze/Silver/Gold layered model with dimensional/fact tables in DuckDB. See [docs/data_model.md](docs/data_model.md) and [docs/ERD.dbml](docs/ERD.dbml).

## 11. KPI definitions
KPI contracts and glossary are documented in [docs/kpi_dictionary.md](docs/kpi_dictionary.md) and served by API glossary endpoints. Frontend renders API-provided KPI values; business KPI calculations are not performed in frontend components.

## 12. Data quality
- DQ results: data/manifests/dq_results.json (DQ score 100.0 for run RUN_20261121_001).
- Quarantine/rule failures tracked in manifests and DQ pages/endpoints.
- Security/quality checks include parameterized SQL practices, allowlisted dynamic identifiers, CORS env config, export limit (MAX_EXPORT_ROWS=5000).
- Details: [docs/data_quality_report.md](docs/data_quality_report.md), [docs/accessibility.md](docs/accessibility.md).

Measured checks (local, 2026-11-21): `python -m pytest -q` => 159 passed, 2 warnings; `ruff check .` => pass; `web`: `npm run lint`, `npx tsc --noEmit`, `npm run build` => pass; `npx playwright test --config=e2e/playwright.config.ts` => 38 passed.

## 13. Installation
`ash
git clone <repo-url>
cd hospital360
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd web && npm ci
`

## 14. Running locally
`ash
# from hospital360/
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
# new terminal
cd web
npm run dev
`
API: http://127.0.0.1:8000/api/v1/health  
Web: http://127.0.0.1:3000

## 15. API documentation
- OpenAPI: http://127.0.0.1:8000/docs
- API reference: [docs/api_reference.md](docs/api_reference.md)
- Measured route handlers: 43 (@router decorator static scan).

## 16. Demo
Follow [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) for a 5-minute walkthrough.

## 17. Limitations
- Synthetic data only; not for clinical decisions.
- Local performance numbers are measured on dev machine, not production SLO guarantees.
- Deployment docs are prepared; no live deployment performed in this environment.
- Some legacy artifact/report files outside hospital360/ may exist in workspace but are not product deliverables.

## 18. Disclaimer
**HOSPITAL 360 uses entirely synthetic data. No real patient data, real hospital identities, or PHI are included. Outputs are for demonstration and portfolio purposes only and must not be used for clinical, operational, or financial decisions.**
