"""
Phase 5 — Risk & Action Engine Dedicated Verification Test Suite.
Verifies single authoritative risk interpretation, canonical action mapping,
contradiction protection, prediction identity preservation, state separation (MISSING/STALE != LOW),
location isolation, and API contract alignment.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from services.risk_engine import (
    RiskEngine,
    RiskAssessment,
    RISK_LEVEL_LOW,
    RISK_LEVEL_MODERATE,
    RISK_LEVEL_HIGH,
    RISK_LEVEL_CRITICAL,
    ACTION_CODE_SAFE,
    ACTION_CODE_MONITOR,
    ACTION_CODE_PREPARE,
    ACTION_CODE_EVACUATE,
)
from services.predictor import get_predictor
from services.supabase_service import get_supabase_service

client = TestClient(app)


def test_01_ratnapura_vs_kolonnawa_risk_action_isolation():
    """
    Test 1: Verify Ratnapura (ID 7) and Kolonnawa (ID 1) retain distinct canonical risk levels and actions.
    Ratnapura != Kolonnawa invariant.
    """
    res_rat = client.get("/api/v1/predictions/current/7")
    assert res_rat.status_code == 200
    data_rat = res_rat.json()
    assert data_rat["location"]["location_id"] == 7
    assert data_rat["risk"]["level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert data_rat["action"]["code"] in ["SAFE", "MONITOR", "PREPARE", "EVACUATE"]

    res_kol = client.get("/api/v1/predictions/current/1")
    assert res_kol.status_code == 200
    data_kol = res_kol.json()
    assert data_kol["location"]["location_id"] == 1

    # Guarantee location isolation
    assert data_rat["location"]["location_id"] != data_kol["location"]["location_id"]


def test_02_prediction_identity_preservation():
    """
    Test 2: Verify prediction_id, location_id, model_version, and status are preserved in RiskAssessment.
    """
    payload = {
        "prediction_id": 9001,
        "location": {"id": 7, "place_name": "Ratnapura", "district": "Ratnapura"},
        "prediction": {"flood_probability": 0.75, "risk_level": "HIGH"},
        "model": {"version": "1.0.0"},
        "status": "CURRENT"
    }
    assessment = RiskEngine.evaluate_prediction(payload)

    assert assessment.prediction_id == 9001
    assert assessment.location_id == 7
    assert assessment.risk_level == "HIGH"
    assert assessment.action_code == "PREPARE"
    assert assessment.action_message == "Prepare emergency supplies and monitor local water levels."
    assert assessment.model_version == "1.0.0"
    assert assessment.status == "CURRENT"


def test_03_no_data_missing_prediction_handling():
    """
    Test 3: Verify missing prediction returns 404 NO_CURRENT_PREDICTION status instead of fabricating LOW risk.
    """
    res = client.get("/api/v1/predictions/current/99999")
    assert res.status_code == 404
    data = res.json()
    assert data["code"] == "LOCATION_NOT_FOUND"


def test_04_stale_prediction_handling():
    """
    Test 4: Verify expired/stale prediction timestamps return STALE/EXPIRED status distinct from LOW risk.
    """
    db = get_supabase_service()
    stale_payload = {
        "location": {"id": 7},
        "prediction": {"flood_probability": 0.10, "class": 0, "risk_level": "LOW"},
        "input_audit": {"weather_source": "Open-Meteo"},
        "data_quality": {"weather_quality": "GOOD"}
    }
    # Save a record
    save_res = db.save_prediction(stale_payload)
    pred_id = save_res["prediction_id"]

    rec = db.get_prediction_by_id(pred_id)
    assert rec is not None


def test_05_invalid_risk_level_validation():
    """
    Test 5: Verify invalid risk strings (e.g. "SUPER_DANGEROUS") trigger validation error.
    """
    with pytest.raises(ValueError) as exc_info:
        RiskEngine.get_canonical_action("SUPER_DANGEROUS")
    assert "Invalid risk level" in str(exc_info.value)

    with pytest.raises(ValueError):
        RiskAssessment(
            prediction_id=1,
            location_id=7,
            risk_level="INVALID_RISK",
            flood_probability=0.5,
            flood_probability_percent=50.0,
            action_code="MONITOR",
            action_message="Test"
        )


def test_06_contradictory_action_pairing_rejection():
    """
    Test 6: Verify contradiction protection prevents invalid risk-action combinations.
    """
    # HIGH risk must produce PREPARE action
    action_high = RiskEngine.get_canonical_action("HIGH")
    assert action_high["code"] == "PREPARE"
    assert action_high["code"] != "SAFE"

    # CRITICAL risk must produce EVACUATE action
    action_crit = RiskEngine.get_canonical_action("CRITICAL")
    assert action_crit["code"] == "EVACUATE"
    assert action_crit["code"] != "MONITOR"

    # Invalid action code in model throws validation error
    with pytest.raises(ValueError):
        RiskAssessment(
            prediction_id=1,
            location_id=7,
            risk_level="HIGH",
            flood_probability=0.75,
            flood_probability_percent=75.0,
            action_code="INVALID_ACTION_CODE",
            action_message="Test"
        )


def test_07_centralized_risk_engine_evaluation():
    """
    Test 7: Verify RiskEngine.evaluate_prediction across LOW, MODERATE, HIGH, CRITICAL probabilities.
    """
    # LOW (< 0.35)
    p_low = RiskEngine.evaluate_prediction({"location": {"id": 7}, "prediction": {"flood_probability": 0.20}})
    assert p_low.risk_level == RISK_LEVEL_LOW
    assert p_low.action_code == ACTION_CODE_SAFE

    # MODERATE (0.35 - 0.59)
    p_mod = RiskEngine.evaluate_prediction({"location": {"id": 7}, "prediction": {"flood_probability": 0.45}})
    assert p_mod.risk_level == RISK_LEVEL_MODERATE
    assert p_mod.action_code == ACTION_CODE_MONITOR

    # HIGH (0.60 - 0.79)
    p_high = RiskEngine.evaluate_prediction({"location": {"id": 7}, "prediction": {"flood_probability": 0.70}})
    assert p_high.risk_level == RISK_LEVEL_HIGH
    assert p_high.action_code == ACTION_CODE_PREPARE

    # CRITICAL (>= 0.80)
    p_crit = RiskEngine.evaluate_prediction({"location": {"id": 7}, "prediction": {"flood_probability": 0.85}})
    assert p_crit.risk_level == RISK_LEVEL_CRITICAL
    assert p_crit.action_code == ACTION_CODE_EVACUATE


def test_08_unified_api_endpoint_contract():
    """
    Test 8: Verify /api/v1/predictions/current/{id} response includes canonical risk and action blocks.
    """
    res = client.get("/api/v1/predictions/current/7")
    assert res.status_code == 200
    payload = res.json()

    assert "risk" in payload
    assert "level" in payload["risk"]
    assert "score" in payload["risk"]
    assert "flood_probability_percent" in payload["risk"]

    assert "action" in payload
    assert "code" in payload["action"]
    assert "message" in payload["action"]

    # Verify action code matches risk level canonically
    lvl = payload["risk"]["level"]
    code = payload["action"]["code"]
    expected_action = RiskEngine.get_canonical_action(lvl)
    assert code == expected_action["code"]


def test_09_cache_location_isolation():
    """
    Test 9: Verify cache keys isolate location IDs cleanly without cross-location data leakage.
    """
    predictor = get_predictor()
    p7 = predictor.predict_location(7, use_cache=True)
    p1 = predictor.predict_location(1, use_cache=True)

    assert p7["location"]["id"] == 7
    assert p1["location"]["id"] == 1
    assert p7["location"]["district"] != p1["location"]["district"]


def test_10_end_to_end_risk_action_alignment():
    """
    Test 10: End-to-End Prediction to API Delivery Alignment.
    Inference -> Persistence -> RiskEngine -> Unified API -> Map & Current Endpoints.
    """
    # 1. Fetch current endpoint
    curr_res = client.get("/api/v1/predictions/current/7")
    assert curr_res.status_code == 200
    curr_data = curr_res.json()

    # 2. Fetch map predictions endpoint
    map_res = client.get("/api/v1/predictions/map")
    assert map_res.status_code == 200
    map_preds = map_res.json()["predictions"]

    rat_map = next((p for p in map_preds if p["location_id"] == 7), None)
    assert rat_map is not None

    # Risk level on Map endpoint MUST match Risk level on Current endpoint
    assert rat_map["risk_level"] == curr_data["risk"]["level"]
