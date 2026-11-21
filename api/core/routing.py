"""Helpers for introspecting FastAPI routes across included routers."""
from __future__ import annotations

from collections.abc import Iterator

from fastapi.routing import APIRoute


def iter_api_routes(routes: list[object], prefix: str = "") -> Iterator[tuple[str, APIRoute]]:
    """Yield ``(full_path, route)`` for APIRoutes, including included routers."""
    for route in routes:
        included = getattr(route, "original_router", None)
        if included is not None:
            context = getattr(route, "include_context", None)
            child_prefix = getattr(context, "prefix", "") or ""
            yield from iter_api_routes(included.routes, prefix + child_prefix)
        elif isinstance(route, APIRoute):
            yield prefix + route.path, route
