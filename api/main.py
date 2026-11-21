"""HOSPITAL 360 — FastAPI application entry point.

Run with:  uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.core.config import API_PREFIX, API_VERSION, APP_ENV, CORS_ORIGINS, LOG_LEVEL
from api.core.db import DatabaseNotReadyError, database_exists
from api.core.errors import ApiContractError
from api.core.responses import error_response, utc_now
from api.core.routing import iter_api_routes
from api.models.responses import (
    ChartEnvelope,
    ErrorEnvelope,
    KpiEnvelope,
    PaginatedEnvelope,
)
from api.routes import charts, domains, hospitals, overview, system

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("hospital360.api")

ERROR_RESPONSES: dict[int, dict[str, object]] = {
    400: {"model": ErrorEnvelope, "description": "Bad request"},
    404: {"model": ErrorEnvelope, "description": "Resource not found"},
    413: {"model": ErrorEnvelope, "description": "Export limit exceeded"},
    422: {"model": ErrorEnvelope, "description": "Validation error"},
    500: {"model": ErrorEnvelope, "description": "Internal error"},
    503: {"model": ErrorEnvelope, "description": "Analytical database not ready"},
}

app = FastAPI(
    title="HOSPITAL 360 Analytics API",
    description="Healthcare intelligence & operations analytics API. All data is synthetic.",
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router, prefix=API_PREFIX, responses=ERROR_RESPONSES)
app.include_router(hospitals.router, prefix=API_PREFIX, responses=ERROR_RESPONSES)
app.include_router(domains.router, prefix=API_PREFIX, responses=ERROR_RESPONSES)
app.include_router(charts.router, prefix=API_PREFIX, responses=ERROR_RESPONSES)
app.include_router(system.router, prefix=API_PREFIX, responses=ERROR_RESPONSES)

# Document the real response shapes without duplicating KPI definitions: the
# models describe the envelope and card structure, while formulas stay in the
# canonical KPI contract.
for route_path, route in iter_api_routes(app.routes):
    if not route_path.startswith(API_PREFIX) or route_path.endswith("/exports/csv"):
        continue
    if route_path.endswith("/kpis"):
        route.response_model = KpiEnvelope
    elif route_path.endswith(("/records", "/failures")):
        route.response_model = PaginatedEnvelope
    else:
        route.response_model = ChartEnvelope


@app.get("/health", include_in_schema=False)
@app.get(f"{API_PREFIX}/health", tags=["meta"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": API_VERSION,
        "environment": APP_ENV,
        "database_ready": str(database_exists()).lower(),
        "generated_at": utc_now(),
    }


@app.exception_handler(DatabaseNotReadyError)
async def database_not_ready(_: Request, exc: DatabaseNotReadyError) -> JSONResponse:
    return error_response(503, "DATABASE_NOT_READY", str(exc))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(422, "VALIDATION_ERROR", "Invalid request parameters", exc.errors())


@app.exception_handler(ApiContractError)
async def contract_error(_: Request, exc: ApiContractError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
    }.get(exc.status_code, "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return error_response(exc.status_code, code, message)


@app.exception_handler(ValueError)
async def value_error(_: Request, exc: ValueError) -> JSONResponse:
    return error_response(400, "BAD_REQUEST", str(exc))


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
