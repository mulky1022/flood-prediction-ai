"""
End-to-end tests for the Notification & Alert System:
1. Alert Preferences CRUD
2. Station-specific vs All Stations preferences
3. Threshold crossing on inference -> triggered_alerts logging
4. Transition state deduplication
5. Triggered alerts API queries, read, and dismissal
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from services.supabase_service import get_supabase_service
from services.alert_service import get_alert_service
from services.predictor import get_predictor

client = TestClient(app)


def test_01_create_and_get_alert_preference():
    db = get_supabase_service()
    device_id = "test_device_qa_101"

    # 1. Create a station-specific preference (Location 1: Kolonnawa, 50% threshold)
    payload = {
        "device_id": device_id,
        "location_id": 1,
        "risk_threshold": 50.0,
        "notification_channels": ["in_app"],
        "is_active": True
    }
    resp = client.post("/api/v1/preferences", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    pref = data["preference"]
    assert pref["device_id"] == device_id
    assert pref["location_id"] == 1
    assert pref["risk_threshold"] == 50.0
    assert pref["location_name"] == "Kolonnawa (Kelani River Lower)"
    assert pref["district"] == "Colombo"

    # 2. Get preferences for device
    get_resp = client.get(f"/api/v1/preferences/{device_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["total"] >= 1
    assert any(p["device_id"] == device_id and p["location_id"] == 1 for p in get_data["items"])


def test_02_all_stations_preference():
    db = get_supabase_service()
    device_id = "test_device_island_wide"

    # Global preference: location_id = None (All stations), 65% threshold
    payload = {
        "device_id": device_id,
        "location_id": None,
        "risk_threshold": 65.0,
        "notification_channels": ["in_app"],
        "is_active": True
    }
    resp = client.post("/api/v1/preferences", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    pref = data["preference"]
    assert pref["location_id"] is None
    assert pref["location_name"] == "All Monitored Stations"
    assert pref["district"] == "Island-wide"


def test_03_inference_threshold_crossing_triggers_alert():
    db = get_supabase_service()
    alert_service = get_alert_service()
    device_id = "test_device_trigger_flow"

    # Set preference for Location 1 at 40% threshold
    client.post("/api/v1/preferences", json={
        "device_id": device_id,
        "location_id": 1,
        "risk_threshold": 40.0,
        "notification_channels": ["in_app"],
        "is_active": True
    })

    # Simulate an inference with 76% flood probability (exceeds 40%)
    mock_prediction = {
        "id": 9991,
        "prediction_id": 9991,
        "location": {"id": 1, "place_name": "Kolonnawa (Kelani River Lower)", "district": "Colombo"},
        "prediction": {
            "class": 1,
            "flood_probability": 0.765,
            "flood_probability_percent": 76.5,
            "non_flood_probability": 0.235,
            "risk_level": "HIGH"
        },
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }

    # First inference: transition from 0.0 -> 76.5% crosses threshold -> triggers alert
    prev_prediction = {"flood_probability": 0.20} # previously below 40%
    triggered = alert_service.evaluate_and_trigger_user_preferences(1, mock_prediction, prev_prediction)
    assert len(triggered) >= 1
    match = [t for t in triggered if t.get("device_id") == device_id][0]
    assert match["location_id"] == 1
    assert match["risk_level"] == "HIGH"
    assert match["threshold_crossed"] == 40.0
    assert "Kolonnawa" in match["title"]

    # Verify triggered alerts endpoint returns it
    trig_resp = client.get(f"/api/v1/alerts/triggered?device_id={device_id}")
    assert trig_resp.status_code == 200
    trig_data = trig_resp.json()
    assert trig_data["total"] >= 1
    assert trig_data["unread_count"] >= 1


def test_04_transition_deduplication_prevents_spam():
    db = get_supabase_service()
    alert_service = get_alert_service()
    device_id = "test_device_anti_spam"

    # Set preference at 50%
    client.post("/api/v1/preferences", json={
        "device_id": device_id,
        "location_id": 2,
        "risk_threshold": 50.0,
        "notification_channels": ["in_app"],
        "is_active": True
    })

    # High prediction
    high_pred = {
        "id": 9992,
        "prediction_id": 9992,
        "location": {"id": 2, "place_name": "Colombo Fort", "district": "Colombo"},
        "prediction": {
            "class": 1,
            "flood_probability": 0.70,
            "flood_probability_percent": 70.0,
            "risk_level": "HIGH"
        }
    }

    # Case A: Transition from below threshold (30% -> 70%) -> SHOULD ALERT
    prev_low = {"flood_probability": 0.30}
    first_run = alert_service.evaluate_and_trigger_user_preferences(2, high_pred, prev_low)
    assert any(t.get("device_id") == device_id for t in first_run)

    # Case B: Consecutive run while already above threshold (70% -> 71%) -> SHOULD NOT SPAM
    prev_high = {"flood_probability": 0.70}
    second_run = alert_service.evaluate_and_trigger_user_preferences(2, high_pred, prev_high)
    assert not any(t.get("device_id") == device_id for t in second_run)


def test_05_delete_preference_and_mark_alert_read():
    db = get_supabase_service()
    device_id = "test_device_delete_flow"

    # Create preference
    pref_res = client.post("/api/v1/preferences", json={
        "device_id": device_id,
        "location_id": 3,
        "risk_threshold": 30.0,
        "is_active": True
    }).json()
    pref_id = pref_res["preference"]["id"]

    # Trigger alert
    saved_alert = db.save_triggered_alert({
        "preference_id": pref_id,
        "device_id": device_id,
        "location_id": 3,
        "flood_probability": 0.75,
        "risk_level": "HIGH",
        "threshold_crossed": 30.0,
        "title": "High Flood Risk: Kelaniya",
        "message": "Flood threshold exceeded",
        "status": "UNREAD"
    })
    alert_id = saved_alert["data"]["id"]

    # Mark as READ
    read_resp = client.post(f"/api/v1/alerts/triggered/{alert_id}/read")
    assert read_resp.status_code == 200
    assert read_resp.json()["status"] == "success"

    # Dismiss alert
    dismiss_resp = client.post(f"/api/v1/alerts/triggered/{alert_id}/dismiss")
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json()["status"] == "success"

    # Delete preference by ID
    del_resp = client.delete(f"/api/v1/preferences/{pref_id}")
    assert del_resp.status_code == 200

    # Verify no active preferences remain for this device
    active_prefs = client.get(f"/api/v1/preferences/{device_id}").json()
    assert active_prefs["total"] == 0
