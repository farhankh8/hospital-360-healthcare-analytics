"""Consistent API response envelopes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.responses import JSONResponse


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def envelope(
    data: Any,
    date_from: str | None = None,
    date_to: str | None = None,
    hospital_ids: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "date_from": date_from,
        "date_to": date_to,
        "hospital_ids": hospital_ids or [],
        "generated_at": utc_now(),
    }
    metadata.update(extra)
    return {"data": data, "metadata": metadata}


def table_envelope(
    data: list[dict[str, Any]],
    total_records: int,
    page: int,
    page_size: int,
    filters_applied: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Return pagination metadata at the top level.

    The same object is retained under ``metadata.pagination`` for backward
    compatibility with clients built before the Phase 3 API contract.
    """
    applied = filters_applied or {}
    pagination = {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": (total_records + page_size - 1) // page_size if page_size else 0,
    }
    resp = envelope(
        data,
        date_from=applied.get("date_from"),
        date_to=applied.get("date_to"),
        hospital_ids=applied.get("hospital_ids") or [],
        pagination=pagination,
        filters_applied=applied,
        **extra,
    )
    resp["pagination"] = pagination
    return resp


def error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    """Build the single structured error body used by every error handler."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "generated_at": utc_now(),
        }
    }


def error_response(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error_payload(code, message, details))
