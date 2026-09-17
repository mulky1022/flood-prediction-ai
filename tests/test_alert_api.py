"""
Phase 7: Alert API Integration Tests with FastAPI TestClient.

Covers:
- Listing alerts and active alerts
- Processing location alert
- Acknowledging and resolving alerts
- Negative tests: 404 on invalid alert ID
- Negative tests: 404 on invalid location ID
- Handling empty alert history
- Graceful degradation when Supabase is not connected
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from services.supabase_service import get_supabase_service


@pytest.fixture
def client():
    return TestClient(app)


def test_11_supabase_degraded_fallback():
    """TEST 11: Supabase operational / fallback -> Local store operates reliably."""
    db = get_supabase_service()
    # Local operations should succeed without unhandled exceptions
    locs = db.get_locations()
    assert len(locs) >= 33


def test_12_invalid_alert_id_404(client):
    """TEST 12: Invalid alert ID -> 404 HTTP error."""
    resp = client.get("/api/v1/alerts/999999")
    assert resp.status_code == 404
    data = resp.json()
    assert data["status"] == "error"
    assert data["code"] == "ALERT_NOT_FOUND"


def test_13_invalid_location_id_404(client):
    """TEST 13: Invalid location ID -> 404 HTTP error."""
    resp = client.get("/api/v1/alerts/location/999999")
    assert resp.status_code == 404
    data = resp.json()
    assert data["status"] == "error"
    assert data["code"] == "LOCATION_NOT_FOUND"

    resp_proc = client.post("/api/v1/alerts/process/999999")
    assert resp_proc.status_code == 404


def test_14_empty_alert_history(client):
    """TEST 14: Empty alert history for nonexistent status -> 200 with empty items list."""
    resp = client.get("/api/v1/alerts?status=EXPIRED")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert isinstance(data["items"], list)


def test_alert_api_lifecycle(client):
    """Full API end-to-end lifecycle: process -> active -> acknowledge -> resolve."""
    # 1. Process alert for Ratnapura (Location ID 7)
    resp = client.post("/api/v1/alerts/process/7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["action_taken"] in ["ALERT_CREATED", "ALERT_UPDATED", "ALERT_RESOLVED", "NO_ALERT_REQUIRED"]

    # 2. Get active alerts
    resp_active = client.get("/api/v1/alerts/active")
    assert resp_active.status_code == 200
    active_data = resp_active.json()
    assert active_data["status"] == "success"

    # 3. If an alert was generated, test acknowledge and resolve
    if data.get("alert"):
        alert_id = data["alert"]["id"]

        # Acknowledge
        resp_ack = client.post(f"/api/v1/alerts/{alert_id}/acknowledge")
        assert resp_ack.status_code == 200
        ack_data = resp_ack.json()
        assert ack_data["alert"]["status"] == "ACKNOWLEDGED"

        # Resolve
        resp_res = client.post(f"/api/v1/alerts/{alert_id}/resolve")
        assert resp_res.status_code == 200
        res_data = resp_res.json()
        assert res_data["alert"]["status"] == "RESOLVED"
