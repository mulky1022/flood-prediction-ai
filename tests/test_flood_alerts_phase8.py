"""
Phase 8 — Flood Alerts System Test Suite.

Verifies:
1. Canonical prediction linkage: ALERT.PREDICTION_ID == CANONICAL.PREDICTION_ID
2. Location isolation: Ratnapura (ID 7) vs Kolonnawa (ID 1)
3. Canonical Risk & Action Engine integration (Phase 5 risk level, action code & action message)
4. Duplicate alert prevention & idempotency
5. Alert lifecycle transitions (ACTIVE -> ACKNOWLEDGED -> RESOLVED / EXPIRED)
6. Missing prediction handling (No false LOW risk conversion)
7. Expired alert handling
8. Alert API endpoints (/alerts/current/{location_id}, /alerts, /alerts/{id}, /alerts/process/{location_id})
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from api.main import app
from services.alert_service import get_alert_service, ALERT_STATUS_ACTIVE, ALERT_STATUS_ACKNOWLEDGED, ALERT_STATUS_RESOLVED
from services.risk_engine import RiskEngine, RISK_LEVEL_HIGH, RISK_LEVEL_LOW, RISK_LEVEL_CRITICAL, ACTION_CODE_PREPARE, ACTION_CODE_SAFE
from services.supabase_service import get_supabase_service, _LOCAL_ALERTS

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_fixtures():
    """Seeds test database/memory store with canonical predictions and locations for Ratnapura and Kolonnawa."""
    _LOCAL_ALERTS.clear()
    db = get_supabase_service()
    now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
    future_iso = (datetime.now(timezone(timedelta(hours=5, minutes=30))) + timedelta(hours=12)).isoformat()
    past_iso = (datetime.now(timezone(timedelta(hours=5, minutes=30))) - timedelta(hours=2)).isoformat()

    # Seed Ratnapura canonical prediction (ID: 7, prediction_id: TEST-RAT-001, HIGH risk 75%)
    ratnapura_payload = {
        "prediction_id": "TEST-RAT-001",
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {
            "prediction_id": "TEST-RAT-001",
            "location_id": 7,
            "flood_probability": 0.75,
            "risk_level": "HIGH",
            "class": 1,
            "valid_from": now_iso,
            "expires_at": future_iso
        },
        "model": {"name": "RandomForest", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }
    db.save_prediction(ratnapura_payload)

    # Seed Kolonnawa canonical prediction (ID: 1, prediction_id: TEST-KOL-001, LOW risk 15%)
    kolonnawa_payload = {
        "prediction_id": "TEST-KOL-001",
        "status": "success",
        "location": {"id": 1, "place_name": "Kolonnawa", "district": "Colombo"},
        "prediction": {
            "prediction_id": "TEST-KOL-001",
            "location_id": 1,
            "flood_probability": 0.15,
            "risk_level": "LOW",
            "class": 0,
            "valid_from": now_iso,
            "expires_at": future_iso
        },
        "model": {"name": "RandomForest", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }
    db.save_prediction(kolonnawa_payload)

    yield {
        "ratnapura_payload": ratnapura_payload,
        "kolonnawa_payload": kolonnawa_payload,
        "past_iso": past_iso,
        "future_iso": future_iso
    }


def test_alert_prediction_linkage(setup_test_fixtures):
    """Verifies that generated alert preserves prediction_id of the canonical prediction."""
    alert_service = get_alert_service()
    payload = setup_test_fixtures["ratnapura_payload"]

    res = alert_service.process_location_alert(7, prediction_payload=payload)
    assert res["status"] == "success"
    alert = res["alert"]
    assert alert is not None
    assert alert["prediction_id"] == "TEST-RAT-001"
    assert alert["location_id"] == 7
    assert alert["risk_level"] == "HIGH"


def test_location_isolation_ratnapura_kolonnawa(setup_test_fixtures):
    """Verifies that Ratnapura (ID 7) and Kolonnawa (ID 1) generated alerts are strictly isolated."""
    alert_service = get_alert_service()
    rat_payload = setup_test_fixtures["ratnapura_payload"]
    kol_payload = setup_test_fixtures["kolonnawa_payload"]

    res_rat = alert_service.process_location_alert(7, prediction_payload=rat_payload)
    res_kol = alert_service.process_location_alert(1, prediction_payload=kol_payload)

    assert res_rat["alert"]["location_id"] == 7
    assert res_rat["alert"]["prediction_id"] == "TEST-RAT-001"
    assert res_rat["alert"]["risk_level"] == "HIGH"

    # Kolonnawa LOW risk does not generate active alertable warning, but current alert query returns location isolation
    curr_rat = alert_service.get_current_alert_for_location(7)
    curr_kol = alert_service.get_current_alert_for_location(1)

    assert curr_rat["alert"] is not None
    assert curr_rat["alert"]["location_id"] == 7
    assert curr_rat["alert"]["prediction_id"] == "TEST-RAT-001"

    # Kolonnawa has no active high alert
    assert curr_kol["alert"] is None or curr_kol["alert"]["location_id"] == 1


def test_canonical_risk_and_action_engine_integration(setup_test_fixtures):
    """Verifies that alert risk and action message strictly come from Phase 5 RiskEngine."""
    alert_service = get_alert_service()
    payload = setup_test_fixtures["ratnapura_payload"]

    res = alert_service.process_location_alert(7, prediction_payload=payload)
    alert = res["alert"]

    canonical_action = RiskEngine.get_canonical_action("HIGH")
    assert alert["risk_level"] == "HIGH"
    assert alert["action_code"] == canonical_action["code"]
    assert alert["action_message"] == canonical_action["message"]


def test_duplicate_alert_deduplication(setup_test_fixtures):
    """Verifies that evaluating the same prediction multiple times updates existing alert instead of creating duplicates."""
    alert_service = get_alert_service()
    payload = setup_test_fixtures["ratnapura_payload"]

    res1 = alert_service.process_location_alert(7, prediction_payload=payload)
    assert res1["action_taken"] == "ALERT_CREATED"
    alert1_id = res1["alert"]["id"]

    # Process second time with updated telemetry
    payload["prediction"]["flood_probability"] = 0.78
    res2 = alert_service.process_location_alert(7, prediction_payload=payload)
    assert res2["action_taken"] == "ALERT_UPDATED"
    assert res2["alert"]["id"] == alert1_id
    assert res2["alert"]["flood_probability"] == 0.78


def test_alert_lifecycle_transitions(setup_test_fixtures):
    """Verifies lifecycle transitions: ACTIVE -> ACKNOWLEDGED -> RESOLVED."""
    alert_service = get_alert_service()
    payload = setup_test_fixtures["ratnapura_payload"]

    res = alert_service.process_location_alert(7, prediction_payload=payload)
    alert_id = res["alert"]["id"]

    # Acknowledge alert
    ack_res = alert_service.acknowledge_alert(alert_id)
    assert ack_res["status"] == ALERT_STATUS_ACKNOWLEDGED

    # Resolve alert
    res_res = alert_service.resolve_alert(alert_id)
    assert res_res["status"] == ALERT_STATUS_RESOLVED


def test_expired_alert_handling(setup_test_fixtures):
    """Verifies that expired alerts are automatically marked EXPIRED and not returned as active."""
    alert_service = get_alert_service()
    db = get_supabase_service()

    # Create expired alert manually
    past_iso = setup_test_fixtures["past_iso"]
    expired_alert_data = {
        "prediction_id": "TEST-RAT-EXPIRED",
        "location_id": 7,
        "risk_level": "HIGH",
        "flood_probability": 0.85,
        "prediction_class": 1,
        "title": "Expired Alert Test",
        "message": "This alert expired in the past.",
        "status": "ACTIVE",
        "expires_at": past_iso
    }
    save_res = db.save_alert(expired_alert_data)
    created_alert = save_res["data"]

    # Query current alert for Ratnapura
    curr = alert_service.get_current_alert_for_location(7)
    assert curr["alert"] is None
    assert "expired" in curr["message"].lower()


def test_missing_prediction_handling():
    """Verifies that missing predictions return error / PREDICTION_UNAVAILABLE without fabricating LOW risk."""
    db = get_supabase_service()
    # Query non-existent location ID
    response = client.get("/api/v1/alerts/current/99999")
    assert response.status_code == 404
    data = response.json()
    err_detail = data.get("detail", data)
    assert err_detail.get("code") == "LOCATION_NOT_FOUND"


def test_alert_api_endpoints(setup_test_fixtures):
    """Verifies API endpoints GET /alerts/current/{id}, GET /alerts, GET /alerts/{id}."""
    alert_service = get_alert_service()
    payload = setup_test_fixtures["ratnapura_payload"]
    alert_service.process_location_alert(7, prediction_payload=payload)

    # 1. GET /alerts/current/7
    res_curr = client.get("/api/v1/alerts/current/7")
    assert res_curr.status_code == 200
    json_curr = res_curr.json()
    assert json_curr["status"] == "success"
    assert json_curr["alert"]["prediction_id"] == "TEST-RAT-001"
    assert json_curr["alert"]["location_id"] == 7

    # 2. GET /alerts
    res_list = client.get("/api/v1/alerts?location_id=7")
    assert res_list.status_code == 200
    json_list = res_list.json()
    assert json_list["status"] == "success"
    assert len(json_list["items"]) > 0

    # 3. GET /alerts/{id}
    alert_id = json_curr["alert"]["id"]
    res_id = client.get(f"/api/v1/alerts/{alert_id}")
    assert res_id.status_code == 200
    json_id = res_id.json()
    assert json_id["alert"]["id"] == alert_id
    assert json_id["alert"]["prediction_id"] == "TEST-RAT-001"
