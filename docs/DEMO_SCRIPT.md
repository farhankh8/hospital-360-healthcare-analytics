# HOSPITAL 360 - Demo Script (5 minutes)

## Setup (before recording)
- API: `python -m uvicorn api.main:app --host 127.0.0.1 --port 8000`
- Web: `cd web && npm run dev`
- Optional: reset filters and open `/overview`.

## Minute 1 - Executive overview (Overview)
- Open **Overview**. Explain that HOSPITAL 360 unifies multi-hospital operational, financial, and quality signals on synthetic data.
- Point out KPI cards, trend charts, and hospital ranking.
- Apply a date range/hospital filter to show all visuals respond through API-driven state.

## Minute 2 - Operational investigation (Appointments/Inpatient or Hospital Profile)
- Navigate to **Appointments** or **Inpatient** and identify an outlier (e.g., no-show, occupancy, LOS/wait).
- Drill into a row/chart segment and show the detail drawer/table.
- Explain: users move from KPI to underlying records without leaving the governed metric definitions.

## Minute 3 - Finance and trust (Finance)
- Open **Finance**. Show revenue/collections/receivables visuals and invoice table.
- Highlight that values come from backend APIs and follow the same global filter state.
- Mention export capability and validation/export limits.

## Minute 4 - Data trust and engineering (Data Quality + Pipeline)
- Open **Data Quality**: show DQ score, quarantine/rule-failure visibility, and dataset checks.
- Open **Pipeline**: show latest run/manifest lineage and run comparison.
- State measured run: 1,588,637 source; 1,585,844 valid; 2,793 quarantined; 2,833 rule failures; DQ 100.0 (`RUN_20261121_001`).

## Minute 5 - Explorer and close (Explorer/Patient Journey)
- Open **Data Explorer** or **Patient Journey** to show record-level traceability.
- Close with engineering evidence: FastAPI + DuckDB + Next.js, pytest/Playwright/ruff/tsc/build checks, deployment prep artifacts.
- Reinforce disclaimer: synthetic data only, no real PHI/hospital identities.
