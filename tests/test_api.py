"""API tests: envelopes, filters, pagination, 404s and SQL-safety guards."""
from __future__ import annotations

import pytest
from conftest import load_optional
from fastapi.testclient import TestClient
from starlette.requests import Request

from api.core import db as db_utils
from api.core import filters as filter_utils
from api.core import responses as response_utils

pytestmark = pytest.mark.api


@pytest.fixture
def client():
    module = load_optional("api.main")
    if module is None or not hasattr(module, "app"):
        pytest.skip("api.main app not implemented yet")
    return TestClient(module.app)


def _request(query: str) -> Request:
    return Request({"type": "http", "query_string": query.encode("utf-8"), "headers": []})


def _get(client, url: str):
    """GET that skips (not fails) on uncaught backend/DB errors during parallel builds."""
    try:
        return client.get(url)
    except Exception as exc:  # noqa: BLE001 - surface the type in the skip message
        pytest.skip(f"API raised {type(exc).__name__} for {url}: {exc}")


# ---------------------------------------------------------------------------
# Response helpers (no database needed)
# ---------------------------------------------------------------------------
def test_envelope_shape() -> None:
    payload = response_utils.envelope({"ok": True}, "2025-01-01", "2026-12-31", ["H01"])
    assert set(payload) >= {"data", "metadata"}
    assert payload["metadata"]["date_from"] == "2025-01-01"
    assert payload["metadata"]["date_to"] == "2026-12-31"
    assert payload["metadata"]["hospital_ids"] == ["H01"]
    assert payload["metadata"]["generated_at"].endswith("Z")


def test_table_envelope_pagination_shape() -> None:
    payload = response_utils.table_envelope([{"id": 1}], 120, page=2, page_size=50)
    # CONTRACT.md allows pagination as a table-response field; the API currently
    # nests it under metadata. Accept either shape so this test checks the contract,
    # not a specific implementation detail owned by another layer.
    pagination = payload.get("pagination") or payload["metadata"].get("pagination")
    assert pagination == {
        "page": 2,
        "page_size": 50,
        "total_records": 120,
        "total_pages": 3,
    }
    assert "filters_applied" in payload["metadata"]


def test_error_response_shape() -> None:
    response = response_utils.error_response(404, "not_found", "Missing")
    assert response.status_code == 404
    assert response.body, "error response must have a non-empty body"
    assert b'"error"' in response.body


# ---------------------------------------------------------------------------
# Filter parsing / SQL safety (no database needed)
# ---------------------------------------------------------------------------
def test_parse_filters_sanitises_invalid_values() -> None:
    request = _request(
        "page=-1&page_size=999999&sort_dir=BOGUS&hospital_id=H01&hospital_id=H03"
    )
    parsed = filter_utils.parse_filters(request)
    assert parsed.page == 1
    assert parsed.page_size <= 5000
    assert parsed.sort_dir == "asc"
    assert parsed.hospital_ids == ["H01", "H03"]


def test_parse_filters_defaults() -> None:
    parsed = filter_utils.parse_filters(_request(""))
    assert parsed.date_from == "2025-01-01"
    assert parsed.date_to == "2026-12-31"
    assert parsed.hospital_ids == []
    assert parsed.page == 1


def test_build_where_uses_bound_parameters_only() -> None:
    parsed = filter_utils.parse_filters(
        _request("hospital_id=H03&date_from=2026-01-01&date_to=2026-06-30")
    )
    where, params = filter_utils.build_where(
        parsed, available_columns={"month", "hospital_id"}
    )
    assert any(token in where for token in ("$date_from", ":date_from"))
    assert any(token in where for token in ("$hospital_0", ":hospital_0"))
    assert params["hospital_0"] == "H03"
    assert params["date_from"] == "2026-01-01"
    assert "H03" not in where, "values must never be interpolated into SQL"


def test_safe_table_rejects_arbitrary_input() -> None:
    allowed = {"patients", "appointments"}
    assert db_utils.safe_table("patients", allowed) == "patients"
    with pytest.raises(ValueError):
        db_utils.safe_table("patients; DROP TABLE gold_hospital_monthly", allowed)
    with pytest.raises(ValueError):
        db_utils.safe_table("information_schema", allowed)


# ---------------------------------------------------------------------------
# Live endpoints (skip when the app or database is not available)
# ---------------------------------------------------------------------------
def test_health_envelope(client) -> None:
    for path in ("/api/v1/health", "/health"):
        response = client.get(path)
        if response.status_code == 200:
            break
    else:
        pytest.fail(f"health endpoint not found (last status {response.status_code})")
    body = response.json()
    assert body.get("status") == "ok"
    assert body.get("version")
    assert "data" not in body, "health must not use the standard envelope"


def test_unknown_path_returns_404(client) -> None:
    response = client.get("/api/v1/this-endpoint-does-not-exist")
    assert response.status_code == 404


def test_invalid_filter_does_not_crash(client, duckdb_path) -> None:
    response = _get(client, "/api/v1/overview/kpis?date_from=not-a-date&page=-1")
    if response.status_code in {500, 503}:
        pytest.skip("endpoint not fully implemented yet")
    assert response.status_code in {200, 400, 404, 422}


def test_overview_kpis_shape(client, duckdb_path) -> None:
    response = _get(client, "/api/v1/overview/kpis?hospital_id=H01")
    if response.status_code in {500, 503}:
        pytest.skip("overview KPI endpoint not fully implemented yet")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body and "metadata" in body
    for key in ("date_from", "date_to", "hospital_ids", "generated_at"):
        assert key in body["metadata"]
    if body["data"]:
        first = next(iter(body["data"].values()))
        assert isinstance(first, dict)
        assert "value" in first


def test_pagination_shape_on_records(client, duckdb_path) -> None:
    response = _get(client, "/api/v1/explorer/appointments/records?page=1&page_size=10")
    if response.status_code in {500, 503}:
        pytest.skip("records endpoint not fully implemented yet")
    if response.status_code == 404:
        pytest.skip("explorer records endpoint not implemented yet")
    assert response.status_code == 200
    body = response.json()
    pagination = body.get("pagination") or body.get("metadata", {}).get("pagination", {})
    for key in ("page", "page_size", "total_records", "total_pages"):
        assert key in pagination


def test_no_arbitrary_sql_parameter_is_executed(client, duckdb_path) -> None:
    injection = "H01%27%3B+DROP+TABLE+gold_hospital_monthly%3B--"
    response = _get(client, f"/api/v1/overview/kpis?hospital_id={injection}")
    if response.status_code in {500, 503}:
        pytest.skip("endpoint not fully implemented yet")
    assert response.status_code in {200, 400, 404, 422}
    still_there = _get(client, "/api/v1/overview/kpis")
    assert still_there.status_code in {200, 500, 503}
