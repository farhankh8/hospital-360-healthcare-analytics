# HOSPITAL 360 - Performance

> Measured locally on 2026-11-21 during final completion run (Windows dev machine, local API + Next.js production build, seed-42 DuckDB). Values are indicative, not production SLAs.

## Targets (blueprint)
| Metric | Target |
|---|---:|
| KPI endpoint response | < 2s |
| Chart endpoint response | < 3s |
| Table endpoint response | < 2s |
| Page load (local) | < 3s |

## Measured API timings (local, warm)
| Endpoint | Time (ms) | Target | Result |
|---|---:|---:|---|
| `/api/v1/overview/kpis?date_from=2025-01-01&date_to=2026-12-31` | 240 | <2000 | PASS |
| `/api/v1/overview/trends?date_from=2025-01-01&date_to=2026-12-31` | 108 | <3000 | PASS |
| `/api/v1/hospitals?page=1&page_size=25&date_from=2025-01-01&date_to=2026-12-31` | 83 | <2000 | PASS |
| `/api/v1/appointments/records?page=1&page_size=25&date_from=2025-01-01&date_to=2026-12-31` | 130 | <2000 | PASS |
| `/api/v1/data-quality/summary` | 180 | <2000 | PASS |
| `/api/v1/exports/csv?path=/appointments/records&...&page_size=1000` | 251 | <5000 | PASS |

## Method
- Start API: `$env:H360_SEED='42'; python -m uvicorn api.main:app --host 127.0.0.1 --port 8000`
- Start web: `cd web; npm run build; npm run start -- -p 3000 -H 127.0.0.1`
- Warm once, then measure second request with PowerShell `Measure-Command` + `Invoke-WebRequest`.
- Data: seed 42 baked DuckDB (`data/hospital360.duckdb`).

## Notes
- All measured endpoints were within blueprint targets on this run.
- If a target is missed in another environment, add indexes/precomputed aggregates only where needed and record before/after here.
