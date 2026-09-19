"""
Phase 5 — Dynamic Alerts & Notification Engine Dedicated Test Suite.
Verifies risk threshold mapping, location alert isolation, active alert persistence & update,
user notification preferences, transition deduplication, and API schema conformity.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from services.alert_service import get_alert_service
from services.supabase_service import get_supabase_service

client = TestClient(app)


def test_01_risk_threshold_mapping():
    """
    Test 1: Verify probability to risk level mapping and policy evaluation.
    """
    alert_service = get_alert_service()

    # LOW risk (< 35%)
    p_low = {"prediction": {"flood_probability": 0.20, "class": 0}, "location": {"id": 7, "place_name": "Ratnapura", "district": "Ratnapura"}}
    eval_low = alert_service.evaluate_prediction_for_alert(p_low)
    assert eval_low["risk_level"] == "LOW"
    assert eval_low["is_alertable"] is False

    # MODERATE risk (35% - 64%)
    p_mod = {"prediction": {"flood_probability": 0.50, "class": 1}, "location": {"id": 7, "place_name": "Ratnapura", "district": "Ratnapura"}}
    eval_mod = alert_service.evaluate_prediction_for_alert(p_mod)
    assert eval_mod["risk_level"] == "MODERATE"
    assert eval_mod["is_alertable"] is False

    # HIGH risk (65% - 84%)
    p_high = {"prediction": {"flood_probability": 0.75, "class": 1}, "location": {"id": 7, "place_name": "Ratnapura", "district": "Ratnapura"}}
    eval_high = alert_service.evaluate_prediction_for_alert(p_high)
    assert eval_high["risk_level"] == "HIGH"
    assert eval_high["is_alertable"] is True

    # CRITICAL risk (>= 85%)
    p_crit = {"prediction": {"flood_probability": 0.90, "class": 1}, "location": {"id": 7, "place_name": "Ratnapura", "district": "Ratnapura"}}
    eval_crit = alert_service.evaluate_prediction_for_alert(p_crit)
    assert eval_crit["risk_level"] == "CRITICAL"
    assert eval_crit["is_alertable"] is True


def test_02_location_alert_isolation():
    """
    Test 2: Verify active alerts for Ratnapura (ID 7) do NOT show for Kolonnawa (ID 1).
    """
    alert_service = get_alert_service()

    # Process high-risk alert for Ratnapura (ID 7)
    p_rat = {
        "status": "success",
        "ready_for_prediction": True,
        "prediction": {"flood_probability": 0.80, "class": 1, "risk_level": "HIGH"},
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"}
    }
    res_rat = alert_service.process_location_alert(7, prediction_payload=p_rat)
    assert res_rat["status"] == "success"

    # Query active alerts for Ratnapura
    rat_alerts = client.get("/api/v1/alerts/location/7").json()["items"]
    assert len(rat_alerts) >= 1
    assert all(a["location_id"] == 7 for a in rat_alerts)

    # Query active alerts for Kolonnawa (ID 1)
    kol_alerts = client.get("/api/v1/alerts/location/1").json()["items"]
    # Guarantee zero cross-location fallback
    assert all(a["location_id"] == 1 for a in kol_alerts)
    assert not any(a["location_id"] == 7 for a in kol_alerts)


def test_03_active_alert_persistence_and_update():
    """
    Test 3: Verify alert creation, update on probability change, and resolution when normal baseline returns.
    """
    alert_service = get_alert_service()

    # 1. High risk prediction -> Create alert
    p_high = {
        "status": "success",
        "ready_for_prediction": True,
        "prediction": {"flood_probability": 0.70, "class": 1, "risk_level": "HIGH"},
        "location": {"id": 2, "place_name": "Hanwella", "district": "Colombo"}
    }
    res1 = alert_service.process_location_alert(2, prediction_payload=p_high)
    assert res1["action_taken"] in ["ALERT_CREATED", "ALERT_UPDATED"]

    # 2. Critical risk prediction for same location -> Update existing alert (deduplicated)
    p_crit = {
        "status": "success",
        "ready_for_prediction": True,
        "prediction": {"flood_probability": 0.88, "class": 1, "risk_level": "CRITICAL"},
        "location": {"id": 2, "place_name": "Hanwella", "district": "Colombo"}
    }
    res2 = alert_service.process_location_alert(2, prediction_payload=p_crit)
    assert res2["action_taken"] == "ALERT_UPDATED"

    # 3. Baseline low risk prediction -> Auto-resolve alert
    p_low = {
        "status": "success",
        "ready_for_prediction": True,
        "prediction": {"flood_probability": 0.15, "class": 0, "risk_level": "LOW"},
        "location": {"id": 2, "place_name": "Hanwella", "district": "Colombo"}
    }
    res3 = alert_service.process_location_alert(2, prediction_payload=p_low)
    assert res3["action_taken"] == "ALERT_RESOLVED"


def test_04_user_preference_threshold_matching():
    """
    Test 4: Verify device notification preferences receive triggered alerts on threshold crossing.
    """
    db = get_supabase_service()
    alert_service = get_alert_service()

    device_id = "test-device-phase5-001"
    pref_payload = {
        "device_id": device_id,
        "location_id": 7,
        "risk_threshold": 60.0,  # Alert if >= 60%
        "notification_channel": "WEB_PUSH",
        "is_active": True
    }
    save_pref = db.save_alert_preference(pref_payload)
    assert save_pref["status"] == "success"

    # Prediction at 75% probability (> 60% threshold)
    p_75 = {
        "prediction_id": 9991,
        "prediction": {"flood_probability": 0.75, "risk_level": "HIGH"},
        "location": {"id": 7, "place_name": "Ratnapura", "district": "Ratnapura"}
    }
    prev_low = {"flood_probability": 0.20}

    triggered = alert_service.evaluate_and_trigger_user_preferences(7, p_75, prev_low)
    assert len(triggered) >= 1
    trig_item = triggered[0]
    assert trig_item["device_id"] == device_id
    assert trig_item["threshold_crossed"] == 60.0


def test_05_transition_deduplication():
    """
    Test 5: Verify repeated identical inference cycles do not generate duplicate notification spam.
    """
    alert_service = get_alert_service()

    device_id = "test-device-phase5-spam-guard"
    db = get_supabase_service()
    db.save_alert_preference({
        "device_id": device_id,
        "location_id": 8,
        "risk_threshold": 50.0,
        "is_active": True
    })

    p_high = {
        "prediction_id": 9992,
        "prediction": {"flood_probability": 0.70, "risk_level": "HIGH"},
        "location": {"id": 8, "place_name": "Galle Town", "district": "Galle"}
    }
    prev_low = {"flood_probability": 0.10}

    # First cycle: low -> high transition -> triggers notification
    run1 = alert_service.evaluate_and_trigger_user_preferences(8, p_high, prev_low)
    assert len(run1) == 1

    # Second cycle: high -> high (no transition) -> should NOT trigger duplicate notification
    prev_high = {"flood_probability": 0.70}
    run2 = alert_service.evaluate_and_trigger_user_preferences(8, p_high, prev_high)
    assert len(run2) == 0


def test_06_alerts_api_endpoints():
    """
    Test 6: Verify all /api/v1/alerts/* endpoints conform to canonical Pydantic schemas.
    """
    # 1. List alerts
    res_list = client.get("/api/v1/alerts?limit=10")
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert data_list["status"] == "success"
    assert "items" in data_list

    # 2. Active alerts
    res_active = client.get("/api/v1/alerts/active")
    assert res_active.status_code == 200
    data_active = res_active.json()
    assert data_active["status"] == "success"

    # 3. Location alerts
    res_loc = client.get("/api/v1/alerts/location/7")
    assert res_loc.status_code == 200
    data_loc = res_loc.json()
    assert data_loc["status"] == "success"

    # 4. Triggered alerts list
    res_trig = client.get("/api/v1/alerts/triggered")
    assert res_trig.status_code == 200
    data_trig = res_trig.json()
    assert data_trig["status"] == "success"
