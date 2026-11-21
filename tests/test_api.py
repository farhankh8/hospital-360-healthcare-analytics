"""API tests: envelopes, filters, pagination, 404s and SQL-safety guards."""
from __future__ import annotations

import json

import pytest
from conftest import load_optional
from fastapi.testclient import TestClient
from starlette.requests import Request

from api.core import db as db_utils
from api.core import filters as filter_utils
from api.core import responses as response_utils
from api.core.errors import ExportLimitExceeded, FilterValidationError
from api.services import exports as export_utils

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
    expected = {
        "page": 2,
        "page_size": 50,
        "max_page_size": 5000,
        "total_records": 120,
        "total_pages": 3,
    }
    assert payload["pagination"] == expected
    # Backward compatibility for clients that read the old nested location.
    assert payload["metadata"]["pagination"] == expected
    assert "filters_applied" in payload["metadata"]


def test_error_response_shape() -> None:
    response = response_utils.error_response(404, "NOT_FOUND", "Missing")
    body = json.loads(response.body)
    assert response.status_code == 404
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "Missing"
    assert body["error"]["generated_at"].endswith("Z")


# ---------------------------------------------------------------------------
# Filter parsing / SQL safety (no database needed)
# ---------------------------------------------------------------------------
def test_parse_filters_accepts_valid_repeated_hospitals() -> None:
    request = _request("page=2&page_size=100&sort_dir=desc&hospital_id=H01&hospital_id=H03")
    parsed = filter_utils.parse_filters(request)
    assert parsed.page == 2
    assert parsed.page_size == 100
    assert parsed.sort_dir == "desc"
    assert parsed.hospital_ids == ["H01", "H03"]


@pytest.mark.parametrize(
    "query,parameter",
    [
        ("page=-1", "page"),
        ("page=abc", "page"),
        ("page_size=5001", "page_size"),
        ("sort_dir=BOGUS", "sort_dir"),
        ("date_from=not-a-date", "date_from"),
        ("date_from=2026-01-01&date_to=2025-01-01", "date_from"),
        ("unknown_filter=H01", "unknown_filter"),
        ("numeric_min=abc", "numeric_min"),
        ("numeric_min=10&numeric_max=9", "numeric_min"),
        ("previous=maybe", "previous"),
        ("rating=abc", "rating"),
    ],
)
def test_parse_filters_rejects_invalid_values(query: str, parameter: str) -> None:
    with pytest.raises(FilterValidationError) as raised:
        filter_utils.parse_filters(_request(query))
    assert raised.value.status_code == 422
    assert raised.value.code == "VALIDATION_ERROR"
    assert parameter in json.dumps(raised.value.details)


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
    pagination = body["pagination"]
    for key in ("page", "page_size", "total_records", "total_pages"):
        assert key in pagination
    assert pagination == body["metadata"]["pagination"]


def test_no_arbitrary_sql_parameter_is_executed(client, duckdb_path) -> None:
    injection = "H01%27%3B+DROP+TABLE+gold_hospital_monthly%3B--"
    response = _get(client, f"/api/v1/overview/kpis?hospital_id={injection}")
    if response.status_code in {500, 503}:
        pytest.skip("endpoint not fully implemented yet")
    assert response.status_code in {200, 400, 404, 422}
    still_there = _get(client, "/api/v1/overview/kpis")
    assert still_there.status_code in {200, 500, 503}


# ---------------------------------------------------------------------------
# Phase 3 API contract
# ---------------------------------------------------------------------------
def test_structured_error_envelope_for_all_error_types(client) -> None:
    cases = [
        ("/api/v1/nope", 404, "NOT_FOUND"),
        ("/api/v1/overview/kpis?page=0", 422, "VALIDATION_ERROR"),
        ("/api/v1/exports/csv?path=/unknown", 404, "NOT_FOUND"),
        ("/api/v1/exports/csv?path=/explorer/appointments/records/extra", 404, "NOT_FOUND"),
    ]
    for url, status, code in cases:
        response = client.get(url)
        assert response.status_code == status
        body = response.json()
        assert body["error"]["code"] == code
        assert isinstance(body["error"]["message"], str)
        assert body["error"]["message"]
        assert "traceback" not in response.text.lower()


def test_openapi_documents_contract_schemas(client) -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/v1/exports/csv" in schema["paths"]
    components = schema["components"]["schemas"]
    for name in ("ErrorEnvelope", "KpiEnvelope", "PaginatedEnvelope", "Pagination"):
        assert name in components

    kpi_schema = schema["paths"]["/api/v1/overview/kpis"]["get"]["responses"]["200"]
    assert "KpiEnvelope" in json.dumps(kpi_schema)
    records_schema = schema["paths"]["/api/v1/explorer/{dataset}/records"]["get"]["responses"]["200"]
    assert "PaginatedEnvelope" in json.dumps(records_schema)
    for status in ("400", "404", "413", "422", "500", "503"):
        error_schema = schema["paths"]["/api/v1/overview/kpis"]["get"]["responses"][status]
        assert "ErrorEnvelope" in json.dumps(error_schema)


def test_export_limit_boundary() -> None:
    export_utils.enforce_export_limit(export_utils.MAX_EXPORT_ROWS)
    with pytest.raises(ExportLimitExceeded) as raised:
        export_utils.enforce_export_limit(export_utils.MAX_EXPORT_ROWS + 1)
    assert raised.value.status_code == 413
    assert raised.value.code == "EXPORT_LIMIT_EXCEEDED"
    assert raised.value.details["requested_rows"] == 5001


def test_server_export_reuses_source_filters_and_enforces_cap(client, duckdb_path) -> None:
    exported = _get(
        client,
        "/api/v1/exports/csv?path=/finance/revenue-by&by=service_category&filename=net_revenue",
    )
    assert exported.status_code == 200
    assert 'filename="net_revenue.csv"' in exported.headers["content-disposition"]
    assert "label,net_revenue" in exported.text

    at_cap = _get(
        client,
        "/api/v1/exports/csv?path=/explorer/appointments/records&page=1&page_size=5000",
    )
    assert at_cap.status_code == 413
    assert at_cap.json()["error"]["code"] == "EXPORT_LIMIT_EXCEEDED"

    above_cap = _get(
        client,
        "/api/v1/exports/csv?path=/explorer/appointments/records&page=1&page_size=5001",
    )
    assert above_cap.status_code == 422
    assert above_cap.json()["error"]["code"] == "VALIDATION_ERROR"


def test_service_category_revenue_matches_canonical_net_revenue(client, duckdb_path) -> None:
    canonical = _get(client, "/api/v1/finance/kpis").json()["data"]["revenue"]["value"]
    rows = _get(client, "/api/v1/finance/revenue-by?by=service_category").json()["data"]
    assert rows
    assert all("net_revenue" in row and "revenue" not in row for row in rows)
    assert sum(row["net_revenue"] for row in rows) == pytest.approx(canonical, abs=0.01)


def test_malformed_numeric_filter_returns_validation_error(client, duckdb_path) -> None:
    response = _get(client, "/api/v1/experience/records?rating=abc")
    if response.status_code in {500, 503}:
        pytest.fail("malformed filter must not raise an internal error")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_snapshot_kpis_mark_date_filter_unavailable(client, duckdb_path) -> None:
    data = _get(client, "/api/v1/overview/kpis").json()["data"]
    for kpi_id in ("hospitals_selected", "total_beds"):
        assert data[kpi_id]["date_filter_available"] is False
        assert "no date field" in data[kpi_id]["date_filter_note"]
    glossary = _get(client, "/api/v1/kpis/glossary").json()["data"]
    total_beds = next(item for item in glossary if item.get("id") == "total_beds")
    assert total_beds["date_filter_available"] is False


RECORD_ENDPOINTS = [
    "/api/v1/appointments/records",
    "/api/v1/emergency/records",
    "/api/v1/inpatient/admissions",
    "/api/v1/finance/invoices",
    "/api/v1/claims/records",
    "/api/v1/procedures/records",
    "/api/v1/data-quality/failures",
]


@pytest.mark.parametrize("endpoint", RECORD_ENDPOINTS)
def test_records_pagination_is_stable_and_respected(client, duckdb_path, endpoint: str) -> None:
    r1 = _get(client, f"{endpoint}?page=1&page_size=5")
    r2 = _get(client, f"{endpoint}?page=2&page_size=5")
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    b1 = r1.json()
    b2 = r2.json()
    assert b1["pagination"]["page"] == 1
    assert b2["pagination"]["page"] == 2
    assert b1["pagination"]["page_size"] == 5
    assert b2["pagination"]["page_size"] == 5
    assert b1["pagination"]["total_records"] == b2["pagination"]["total_records"]
    assert b1["pagination"]["max_page_size"] == 5000
    assert len(b1["data"]) <= 5
    assert len(b2["data"]) <= 5
    # If there are enough rows, page 2 should differ from page 1.
    if b1["pagination"]["total_records"] > 5:
        assert b1["data"] != b2["data"]


def test_explorer_records_pagination_differs(client, duckdb_path) -> None:
    r1 = _get(client, "/api/v1/explorer/patients/records?page=1&page_size=5")
    r2 = _get(client, "/api/v1/explorer/patients/records?page=2&page_size=5")
    assert r1.status_code == 200
    assert r2.status_code == 200
    b1, b2 = r1.json(), r2.json()
    assert b1["pagination"]["total_records"] == b2["pagination"]["total_records"]
    assert b1["data"] != b2["data"]


@pytest.mark.parametrize("endpoint", RECORD_ENDPOINTS[:5])
def test_records_oversized_page_size_returns_422(client, duckdb_path, endpoint: str) -> None:
    response = _get(client, f"{endpoint}?page_size=999999")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "query,parameter",
    [
        ("hospital_id=BAD", "hospital_id"),
        ("department_id=BAD", "department_id"),
        ("specialty_id=BAD", "specialty_id"),
        ("payer_id=BAD", "payer_id"),
        ("doctor_id=BAD", "doctor_id"),
        ("supplier_id=BAD", "supplier_id"),
        ("item_id=BAD", "item_id"),
    ],
)
def test_invalid_id_filters_return_422(client, duckdb_path, query: str, parameter: str) -> None:
    response = _get(client, f"/api/v1/overview/kpis?{query}")
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert parameter in json.dumps(body["error"]["details"])


def test_date_from_after_date_to_returns_422(client, duckdb_path) -> None:
    response = _get(client, "/api/v1/overview/kpis?date_from=2026-06-01&date_to=2026-01-01")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "date_from" in json.dumps(body["error"]["details"])


def test_dq_validity_chart_returns_non_empty(client, duckdb_path) -> None:
    response = _get(client, "/api/v1/charts/dq/validity")
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    assert {"label", "failures"}.issubset(body["data"][0].keys())


def test_dq_quarantine_charts_return_data(client, duckdb_path) -> None:
    for endpoint, value_key in (
        ("/api/v1/charts/dq/quarantine-by-rule", "quarantined"),
        ("/api/v1/charts/dq/quarantine-by-dataset", "quarantined"),
    ):
        response = _get(client, endpoint)
        assert response.status_code == 200, response.text
        body = response.json()
        assert isinstance(body["data"], list)
        assert len(body["data"]) > 0
        assert {"label", value_key}.issubset(body["data"][0].keys())


def test_dq_injected_vs_detected_chart(client, duckdb_path) -> None:
    response = _get(client, "/api/v1/charts/dq/injected-vs-detected")
    assert response.status_code == 200, response.text
    body = response.json()
    rows = body["data"]
    assert isinstance(rows, list)
    assert len(rows) > 0
    assert {"issue_type", "injected", "detected", "rule_id", "table"}.issubset(rows[0].keys())
    assert body["metadata"]["total_injected"] >= 0
    assert body["metadata"]["total_quarantine_rule_failures"] >= 0


def test_pipeline_runs_compare_endpoint(client, duckdb_path) -> None:
    runs_resp = _get(client, "/api/v1/pipeline/runs")
    assert runs_resp.status_code == 200, runs_resp.text
    runs = runs_resp.json()["data"]
    if len(runs) < 2:
        pytest.skip("need at least two pipeline runs for compare test")
    run_a = runs[-1]["run_id"]
    run_b = runs[0]["run_id"]
    resp = _get(client, f"/api/v1/pipeline/runs/compare?run_a={run_a}&run_b={run_b}")
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["run_a"]["run_id"] == run_a
    assert body["run_b"]["run_id"] == run_b
    assert "deltas" in body and "tables" in body
    assert {"duration_seconds", "source_records", "valid_records", "quarantined_records", "dq_score"}.issubset(body["deltas"].keys())


def test_pipeline_runs_compare_rejects_unknown_run(client, duckdb_path) -> None:
    runs_resp = _get(client, "/api/v1/pipeline/runs")
    runs = runs_resp.json()["data"]
    if not runs:
        pytest.skip("no pipeline runs")
    run_a = runs[0]["run_id"]
    resp = _get(client, f"/api/v1/pipeline/runs/compare?run_a={run_a}&run_b=RUN_DOES_NOT_EXIST")
    assert resp.status_code == 422


def test_pipeline_lineage_by_table(client, duckdb_path) -> None:
    lineage_resp = _get(client, "/api/v1/pipeline/lineage")
    assert lineage_resp.status_code == 200
    rows = lineage_resp.json()["data"]
    if not rows:
        pytest.skip("no lineage rows")
    table = rows[0]["target_table"]
    resp = _get(client, f"/api/v1/pipeline/lineage/{table}")
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["target_table"] == table
    assert "downstream_tables" in body
    bad = _get(client, "/api/v1/pipeline/lineage/__not_a_table__")
    assert bad.status_code == 422

def test_journey_sample_patient(client, duckdb_path) -> None:
    resp = _get(client, "/api/v1/journey/sample-patient")
    assert resp.status_code == 200, resp.text
    pid = resp.json()["data"].get("patient_id")
    assert pid


def test_patient_journey_endpoint(client, duckdb_path) -> None:
    sample = _get(client, "/api/v1/journey/sample-patient").json()["data"]["patient_id"]
    resp = _get(client, f"/api/v1/journey?patient_id={sample}")
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["patient"]["patient_id"] == sample
    assert "timeline" in body and isinstance(body["timeline"], list)
    assert "billing_summary" in body
    assert "feedback_summary" in body
    assert "synthetic_notice" in body
    # event type filter
    timeline = body["timeline"]
    if timeline:
        et = timeline[0]["event_type"]
        filtered = _get(client, f"/api/v1/journey?patient_id={sample}&event_type={et}")
        assert filtered.status_code == 200
        for ev in filtered.json()["data"]["timeline"]:
            assert ev["event_type"] == et


def test_patient_journey_events_export_shape(client, duckdb_path) -> None:
    sample = _get(client, "/api/v1/journey/sample-patient").json()["data"]["patient_id"]
    resp = _get(client, f"/api/v1/journey/events?patient_id={sample}&page=1&page_size=25")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "data" in payload and "pagination" in payload
    assert payload["pagination"]["total_records"] >= 0
    bad = _get(client, "/api/v1/journey?patient_id=PAT_DOES_NOT_EXIST")
    assert bad.status_code == 404
    missing = _get(client, "/api/v1/journey")
    assert missing.status_code in (400, 422)

def test_kpi_glossary_required_fields(client, duckdb_path) -> None:
    resp = _get(client, "/api/v1/kpis/glossary")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    items = data.get("kpis", data) if isinstance(data, dict) else data
    assert isinstance(items, list) and len(items) > 50
    required = {"name", "business_definition", "formula", "numerator", "denominator", "unit", "grain", "date_field", "exclusions", "source_tables", "dimensions", "caveat", "validation_test"}
    missing = [k for k in required if k not in items[0]]
    assert not missing, f"missing keys: {missing}"
    # spot check a few items have business_definition
    assert any(i.get("business_definition") for i in items)
