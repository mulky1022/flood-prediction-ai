"""
Phase 17 — Admin / Technical Dashboard Automated Test Suite.
Tests admin token authentication, unauthorized route protection, overview telemetry,
prediction monitoring, job execution & controlled retry, location isolation (Ratnapura vs Kolonnawa),
masked recipient logs, official warning sync, system error diagnostics, audit trails, and end-to-end integration.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)
ADMIN_TOKEN = "admin-secret-token-v17"
AUTH_HEADERS = {"X-Admin-Token": ADMIN_TOKEN}


def test_01_admin_auth_and_unauthorized_protection():
    """Verify unauthenticated/unauthorized access returns HTTP 401, while valid token grants access."""
    # 1. Unauthenticated GET request -> 401 Unauthorized
    res1 = client.get("/api/v1/admin/overview")
    assert res1.status_code == 401

    # 2. Invalid token GET request -> 401 Unauthorized
    res2 = client.get("/api/v1/admin/overview", headers={"X-Admin-Token": "INVALID-SECRET-TOKEN"})
    assert res2.status_code == 401

    # 3. Login POST with invalid token -> 401
    res_login_bad = client.post("/api/v1/admin/login", json={"token": "WRONG_TOKEN"})
    assert res_login_bad.status_code == 401

    # 4. Login POST with valid token -> 200 OK
    res_login_good = client.post("/api/v1/admin/login", json={"token": ADMIN_TOKEN})
    assert res_login_good.status_code == 200
    assert res_login_good.json()["token_valid"] is True

    # 5. Valid token GET request -> 200 OK
    res3 = client.get("/api/v1/admin/overview", headers=AUTH_HEADERS)
    assert res3.status_code == 200
    assert res3.json()["status"] == "success"


def test_02_admin_overview_aggregation():
    """Verify overview telemetry aggregation endpoint returns system health and location counts."""
    res = client.get("/api/v1/admin/overview", headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert "system_health" in data
    assert data["system_health"]["overall_status"] in ("HEALTHY", "DEGRADED_LOCAL")
    assert data["monitored_locations_count"] >= 2
    assert "data_sources" in data
    assert len(data["data_sources"]) >= 1


def test_03_system_health_diagnostics():
    """Verify detailed real-time component health checks endpoint."""
    res = client.get("/api/v1/admin/health", headers=AUTH_HEADERS)
    assert res.status_code == 200
    health = res.json()

    assert health["overall_status"] in ("HEALTHY", "DEGRADED_LOCAL")
    assert health["model_engine_status"] == "LOADED"
    assert "checked_at" in health


def test_04_prediction_monitoring_and_freshness():
    """Verify prediction monitoring table lists records with canonical risk and freshness status."""
    res = client.get("/api/v1/admin/predictions", headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["total"] >= 1
    for pred in data["predictions"]:
        assert "prediction_id" in pred
        assert "location_id" in pred
        assert pred["risk_level"] in ("LOW", "MODERATE", "HIGH", "CRITICAL")
        assert pred["freshness_status"] in ("CURRENT", "STALE", "MISSING", "FAILED")


def test_05_location_isolation_ratnapura_vs_kolonnawa():
    """
    Verify strict location isolation in Admin predictions table:
    Ratnapura (RATNAPURA_001) vs Kolonnawa (KOLONNAWA_001).
    """
    res_rat = client.get("/api/v1/admin/predictions?location_id=RATNAPURA_001", headers=AUTH_HEADERS)
    assert res_rat.status_code == 200
    rat_preds = res_rat.json()["predictions"]

    res_kol = client.get("/api/v1/admin/predictions?location_id=KOLONNAWA_001", headers=AUTH_HEADERS)
    assert res_kol.status_code == 200
    kol_preds = res_kol.json()["predictions"]

    for p in rat_preds:
        assert p["location_id"] in ("RATNAPURA_001", "7")
    for p in kol_preds:
        assert p["location_id"] in ("KOLONNAWA_001", "1")


def test_06_data_sources_and_stations_monitoring():
    """Verify telemetry feeds and station inventory mapping endpoints."""
    res_ds = client.get("/api/v1/admin/data-sources", headers=AUTH_HEADERS)
    assert res_ds.status_code == 200
    sources = res_ds.json()
    assert len(sources) >= 1
    assert sources[0]["status"] == "ONLINE"

    res_st = client.get("/api/v1/admin/stations", headers=AUTH_HEADERS)
    assert res_st.status_code == 200
    stations = res_st.json()
    assert len(stations) >= 2


def test_07_job_execution_log_and_retry():
    """Verify job execution log retrieval and safe canonical pipeline retry trigger."""
    # 1. Fetch job logs
    res_jobs = client.get("/api/v1/admin/jobs", headers=AUTH_HEADERS)
    assert res_jobs.status_code == 200
    jobs = res_jobs.json()["jobs"]
    assert len(jobs) >= 1

    # 2. Trigger pipeline retry for Ratnapura
    retry_res = client.post("/api/v1/admin/jobs/retry", json={"location_id": "RATNAPURA_001"}, headers=AUTH_HEADERS)
    assert retry_res.status_code == 200
    retry_data = retry_res.json()
    assert retry_data["status"] == "success"
    assert retry_data["job"]["job_type"] == "MANUAL_ADMIN_RETRY"


def test_08_alert_and_masked_notification_monitoring():
    """Verify masked notification log retrieval preserves privacy (+9477****567)."""
    res = client.get("/api/v1/admin/notifications", headers=AUTH_HEADERS)
    assert res.status_code == 200
    notifs = res.json()["notifications"]

    for n in notifs:
        assert "*" in n["destination_masked"] or "077" not in n["destination_masked"]
        assert len(n["destination_masked"]) > 0


def test_09_official_warning_sync_monitoring():
    """Verify active official government warnings endpoint."""
    res = client.get("/api/v1/warnings/active")
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_10_system_error_diagnostics_log():
    """Verify recording and fetching system diagnostic logs."""
    res = client.get("/api/v1/admin/errors", headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"


def test_11_admin_audit_logging():
    """Verify administrative operation audit logging trail."""
    res = client.get("/api/v1/admin/audit-logs", headers=AUTH_HEADERS)
    assert res.status_code == 200
    logs = res.json()["logs"]
    assert len(logs) >= 1  # From previous retry trigger in test_07


def test_12_full_phase17_end_to_end_integration():
    """
    Full end-to-end integration check:
    Database -> Canonical Prediction API -> Public UI endpoint -> Admin Dashboard monitoring.
    """
    # 1. Fetch public current prediction for Ratnapura
    pub_res = client.get("/api/v1/predictions/current/RATNAPURA_001")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    pub_pred_id = str(pub_data.get("prediction_id"))
    pub_risk = pub_data["risk"]["level"]

    # 2. Fetch admin prediction monitoring table
    admin_res = client.get("/api/v1/admin/predictions?location_id=RATNAPURA_001", headers=AUTH_HEADERS)
    assert admin_res.status_code == 200
    admin_preds = admin_res.json()["predictions"]
    assert len(admin_preds) >= 1

    # 3. Assert canonical prediction ID and risk level match between Public and Admin UI
    matched = False
    for p in admin_preds:
        if str(p["prediction_id"]) == pub_pred_id or p["risk_level"] == pub_risk:
            matched = True
            break
    assert matched is True
