"""Server-side CSV export helpers with a single enforced row cap."""
from __future__ import annotations

import csv
import inspect
import io
import json
from typing import Any
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import Response
from fastapi.routing import APIRoute

from api.core.config import API_PREFIX, MAX_EXPORT_ROWS, MAX_PAGE_SIZE
from api.core.errors import ExportLimitExceeded
from api.core.routing import iter_api_routes


def enforce_export_limit(total_records: int) -> None:
    """Reject an export whose filtered result set exceeds the global cap."""
    if total_records > MAX_EXPORT_ROWS:
        raise ExportLimitExceeded(
            f"Export contains {total_records:,} rows; the maximum is {MAX_EXPORT_ROWS:,}",
            {"requested_rows": total_records, "maximum_rows": MAX_EXPORT_ROWS},
        )


def resolve_export_route(request: Request, path: str) -> tuple[APIRoute, dict[str, str]]:
    """Resolve an API-relative path to an existing GET route and its path params."""
    if ".." in path or "?" in path or "#" in path:
        raise ValueError("Invalid export path")
    normalized = path.strip()
    if normalized.startswith("http://") or normalized.startswith("https://"):
        raise ValueError("Invalid export path")
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    full_path = normalized if normalized.startswith(API_PREFIX) else f"{API_PREFIX}{normalized}"
    relative_path = full_path[len(API_PREFIX):]
    if not relative_path.startswith("/"):
        relative_path = f"/{relative_path}"
    for route_path, route in iter_api_routes(request.app.routes):
        if "GET" not in route.methods or route_path.endswith("/exports/csv"):
            continue
        match = route.path_regex.fullmatch(relative_path)
        if match:
            return route, match.groupdict()
    raise LookupError(f"Unknown export endpoint: {path}")


def invoke_export_route(
    request: Request,
    route: APIRoute,
    path_params: dict[str, str],
) -> dict[str, Any]:
    """Call the source endpoint with the caller's filters and path parameters."""
    query = [
        (key, value)
        for key, value in request.query_params.multi_items()
        if key not in {"path", "filename"}
    ]
    scope = dict(request.scope)
    scope["query_string"] = urlencode(query).encode("utf-8")
    scope["path_params"] = path_params
    scoped_request = Request(scope, request.receive)

    kwargs: dict[str, Any] = {}
    for name, parameter in inspect.signature(route.endpoint).parameters.items():
        if name in {"request", "req"}:
            kwargs[name] = scoped_request
        elif name in path_params:
            kwargs[name] = path_params[name]
        elif name in request.query_params:
            kwargs[name] = request.query_params.get(name)
        elif parameter.default is inspect.Parameter.empty:
            raise ValueError(f"Unsupported export endpoint signature: {route.path}")
    payload = route.endpoint(**kwargs)
    if not isinstance(payload, dict):
        raise TypeError(f"Export endpoint returned an unexpected payload: {route.path}")
    return payload


def export_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract exportable rows and enforce the cap before serialisation."""
    data = payload.get("data")
    pagination = payload.get("pagination") or payload.get("metadata", {}).get("pagination") or {}
    total = int(pagination.get("total_records", 0) or 0)
    enforce_export_limit(total)

    if isinstance(data, dict):
        rows = [
            {"kpi_id": key, **(value if isinstance(value, dict) else {"value": value})}
            for key, value in data.items()
        ]
    elif isinstance(data, list):
        rows = [row if isinstance(row, dict) else {"value": row} for row in data]
    else:
        rows = []
    enforce_export_limit(len(rows))
    return rows


def csv_response(rows: list[dict[str, Any]], filename: str) -> Response:
    """Serialise rows to CSV with safe headers and UTF-8 BOM for spreadsheets."""
    headers = sorted({key for row in rows for key in row})
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({
            key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
            for key, value in row.items()
        })
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in filename).strip("-") or "export"
    return Response(
        content="\ufeff" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.csv"'},
    )


__all__ = [
    "MAX_EXPORT_ROWS",
    "MAX_PAGE_SIZE",
    "csv_response",
    "enforce_export_limit",
    "export_rows",
    "invoke_export_route",
    "resolve_export_route",
]
