# HOSPITAL 360 - Deployment (Preparation Only)

> **Status: deployment preparation only.** No live deployment or cloud accounts were created. All artifacts below are prepared for manual deployment.

## Target
- **Frontend:** Vercel (Next.js web app in `web/`).
- **Backend:** Render Docker Web Service (FastAPI + baked seed-42 DuckDB image from `Dockerfile.api`).

**Why Render for backend:** The API is packaged as a Docker image that bakes deterministic seed-42 data during build (proven in CI). Render supports Docker web services, `PORT` injection, health checks, and env vars with a simple `render.yaml` blueprint. A Vercel frontend can point at the Render URL via `NEXT_PUBLIC_API_URL`, and Render CORS can be restricted to the Vercel origin via `CORS_ORIGINS`.

## Prepared artifacts
- `Dockerfile.api` - FastAPI image; bakes seed-42 data; respects `${PORT:-8000}`; opens DuckDB read-only in app code.
- `Dockerfile.web` - Next.js production image.
- `docker-compose.yml` - local full-stack smoke.
- `render.yaml` - Render blueprint for backend.
- `.env.example`, `web/.env.example` - env templates.
- `scripts/smoke_deployed.py` - post-deploy smoke checks.
- `.github/workflows/smoke-deployed.yml` - manual `workflow_dispatch` smoke workflow.

## Environment variables
| Variable | Where | Required | Notes |
|---|---|---:|---|
| `APP_ENV` | Backend | yes | `production` |
| `LOG_LEVEL` | Backend | yes | `INFO` |
| `DATA_PATH` | Backend | yes | `/app/data` |
| `DATABASE_PATH` | Backend | yes | `/app/data/hospital360.duckdb` |
| `CORS_ORIGINS` | Backend | yes | Set to deployed Vercel URL, e.g. `https://your-app.vercel.app` |
| `NEXT_PUBLIC_API_URL` | Frontend | yes | Backend API base, e.g. `https://your-api.onrender.com/api/v1` |

No secrets in repo. Do not put secrets in `NEXT_PUBLIC_*`.

## Backend deployment (Render) - click-by-click
1. Push/merge the branch you want to deploy (after CI green). Do not deploy from an unverified branch.
2. In Render, **New + > Blueprint** (or Web Service). Connect GitHub repo `farhankh8/hospital-360-healthcare-analytics`.
3. If using Blueprint, select `render.yaml`. If manual: choose **Docker**, repo root, Dockerfile `Dockerfile.api`.
4. Set service name `hospital360-api`, plan Free (or as desired), region nearest you.
5. Set env vars: `APP_ENV=production`, `LOG_LEVEL=INFO`, `DATA_PATH=/app/data`, `DATABASE_PATH=/app/data/hospital360.duckdb`, `CORS_ORIGINS=https://<your-vercel-app>.vercel.app` (update after frontend is deployed).
6. Health check path: `/api/v1/health`.
7. Deploy. First Docker build may take several minutes (seed + ETL baked in). Free tier cold starts are expected.
8. Verify: open `https://<api>/api/v1/health` and `https://<api>/api/v1/hospitals?page=1&page_size=5`.

## Frontend deployment (Vercel) - click-by-click
1. In Vercel, **Add New Project**, import same GitHub repo.
2. Set **Root Directory** to `web`.
3. Framework preset: Next.js. Build command: `npm run build` (default). Output: default.
4. Add env var `NEXT_PUBLIC_API_URL=https://<your-render-api>.onrender.com/api/v1`.
5. Deploy. After deployment, copy the Vercel URL.
6. Go back to Render backend env vars and set `CORS_ORIGINS` to the exact Vercel origin; redeploy backend.

## Post-deploy smoke
Local script:
```bash
python scripts/smoke_deployed.py --api https://<api> --web https://<web>
```
Checks: health, hospitals, overview KPIs, DQ summary, records page, CORS header, web home.

GitHub Actions manual smoke:
- Actions > **Deployed Smoke** > Run workflow.
- Inputs: `api_url`, `web_url`.

## Operational notes
- Backend opens DuckDB read-only (`duckdb.connect(..., read_only=True)`), safe for read-only filesystem baked data.
- Backend reads `CORS_ORIGINS` from env; no wildcard required.
- Backend respects platform `PORT` via Docker CMD `${PORT:-8000}`.
- Free-tier services may cold-start; first request can be slow.
- Redeploy: push to deployed branch or trigger manual redeploy in Render/Vercel after env changes.

## Local Docker validation
```bash
docker compose build
docker compose up -d
curl -fsS http://localhost:8000/api/v1/health
curl -fsS http://localhost:3000 >/dev/null
docker compose down -v
```
