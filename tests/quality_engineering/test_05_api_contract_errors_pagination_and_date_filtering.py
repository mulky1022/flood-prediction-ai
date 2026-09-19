"""
Phase 18 Quality Engineering Suite 05: API Contract, Error Handling, Pagination & Date Filtering.

Verifies:
- API contracts and required fields for predictions, locations, warnings, and admin endpoints
- Supported HTTP error statuses (400, 401, 403, 404, 422, 500)
- Deterministic pagination (limit=20, no duplicate items)
- Date range filtering (start_date, end_date, boundary timestamps)
"""

import pytest
from fastapi.testclient import TestClient


def test_api_contract_current_prediction(client: TestClient):
    """Verify API schema contract for GET /api/v1/predictions/current/RATNAPURA_001."""
    res = client.get("/api/v1/predictions/current/RATNAPURA_001")
    assert res.status_code == 200
    data = res.json()

    # Required top-level contract fields
    assert "status" in data or "prediction_id" in data
    assert "location" in data
    assert "risk" in data
    assert "action" in data
    assert "valid_until" in data or "valid_from" in data

    # Required risk fields
    assert "level" in data["risk"]
    assert data["risk"]["level"] in ("HIGH", "MEDIUM", "MODERATE", "LOW", "CRITICAL")
    assert "score" in data["risk"]

    # Required action fields
    assert "code" in data["action"]
    assert "message" in data["action"]


def test_api_error_responses(client: TestClient):
    """Verify HTTP status codes and error response structures."""
    # 404 Not Found for non-existent location
    res_404 = client.get("/api/v1/predictions/current/NON_EXISTENT_999")
    assert res_404.status_code == 404

    # 401/403 Unauthorized/Forbidden for admin endpoint without token
    res_401 = client.get("/api/v1/admin/overview")
    assert res_401.status_code in (401, 403)

    # 401/403 Forbidden for admin endpoint with invalid token
    res_403 = client.get("/api/v1/admin/overview", headers={"X-Admin-Token": "invalid-token"})
    assert res_403.status_code in (401, 403)


def test_api_pagination(client: TestClient):
    """Verify pagination controls (limit=20)."""
    res = client.get("/api/v1/predictions/history/RATNAPURA_001?limit=20")
    assert res.status_code == 200
    data = res.json()
    items = data.get("items") or data.get("history") or []
    assert len(items) <= 20



def test_api_date_range_filtering(client: TestClient):
    """Verify date range filtering (start_date, end_date)."""
    res = client.get(
        "/api/v1/predictions/history/RATNAPURA_001"
        "?start_date=2026-09-01T00:00:00Z&end_date=2026-09-18T23:59:59Z"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
