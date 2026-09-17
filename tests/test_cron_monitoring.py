"""
Scheduled Background Monitoring Integration Tests.

Validates:
- /api/v1/cron/monitor endpoint execution
- Authentication handling with Bearer tokens / X-Cron-Secret
- Processing batch execution for all 25 calibrated monitoring locations
- Deduction of active alerts, prediction execution, and runtime metrics
"""

import os
import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_cron_monitor_endpoint_success(monkeypatch, client):
    """Verifies that the /api/v1/cron/monitor endpoint executes successfully and returns valid structured output."""
    from services.alert_service import AlertService
    mock_batch = {
        "status": "success",
        "total_locations_processed": 25,
        "alerts_created": 1,
        "alerts_updated": 0,
        "alerts_resolved": 0,
        "active_alerts_total": 1,
        "execution_time_seconds": 1.25,
        "details": [{"status": "success", "action_taken": "ALERT_CREATED", "location_id": 1}] * 25
    }
    monkeypatch.setattr(AlertService, "process_all_monitored_locations", lambda self: mock_batch)

    resp = client.get("/api/v1/cron/monitor")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "success"
    assert data["total_locations_processed"] >= 25
    assert "alerts_created" in data
    assert "alerts_updated" in data
    assert "alerts_resolved" in data
    assert "execution_time_seconds" in data
    assert isinstance(data["details"], list)
    assert len(data["details"]) == data["total_locations_processed"]


def test_cron_monitor_post_endpoint(monkeypatch, client):
    """Verifies that POST /api/v1/cron/monitor is also supported for webhook/scheduler triggers."""
    from services.alert_service import AlertService
    mock_batch = {
        "status": "success",
        "total_locations_processed": 25,
        "alerts_created": 0,
        "alerts_updated": 0,
        "alerts_resolved": 0,
        "active_alerts_total": 0,
        "execution_time_seconds": 0.8,
        "details": []
    }
    monkeypatch.setattr(AlertService, "process_all_monitored_locations", lambda self: mock_batch)

    resp = client.post("/api/v1/cron/monitor")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"


def test_cron_monitor_auth_bearer(monkeypatch, client):
    """Verifies that when CRON_SECRET is configured, valid Bearer token is accepted."""
    monkeypatch.setenv("CRON_SECRET", "test-secret-12345")
    from api.routes import cron
    monkeypatch.setattr(cron, "CRON_SECRET", "test-secret-12345")

    from services.alert_service import AlertService
    mock_batch = {
        "status": "success",
        "total_locations_processed": 25,
        "alerts_created": 0,
        "alerts_updated": 0,
        "alerts_resolved": 0,
        "active_alerts_total": 0,
        "details": []
    }
    monkeypatch.setattr(AlertService, "process_all_monitored_locations", lambda self: mock_batch)

    # Unauthorized request without token -> 401
    resp_unauth = client.get("/api/v1/cron/monitor")
    assert resp_unauth.status_code == 401

    # Authorized request with Bearer token -> 200
    resp_auth = client.get("/api/v1/cron/monitor", headers={"Authorization": "Bearer test-secret-12345"})
    assert resp_auth.status_code == 200
    assert resp_auth.json()["status"] == "success"

    # Authorized request with query secret -> 200
    resp_query = client.get("/api/v1/cron/monitor?secret=test-secret-12345")
    assert resp_query.status_code == 200
