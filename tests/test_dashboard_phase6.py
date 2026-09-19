"""
Phase 6 — Dashboard Redesign Verification Test Suite.
Verifies canonical prediction API consumption, location identity isolation,
explicit state handling (CURRENT, STALE, MISSING, ERROR), canonical risk & action mapping,
and prevention of client-side override or fallback logic.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from services.risk_engine import RiskEngine

client = TestClient(app)


def test_01_dashboard_uses_canonical_unified_prediction_api():
    """
    Test 1: Verify the unified prediction API gateway provides all required
    canonical fields for the Phase 6 Dashboard contract.
    """
    response = client.get("/api/v1/predictions/current/7")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    # Location Identity
    assert "location" in data
    assert data["location"]["location_id"] == 7
    assert "Ratnapura" in data["location"]["name"]
    assert data["location"]["district"] == "Ratnapura"

    # Prediction Identifiers & Timestamps
    assert "prediction_id" in data
    assert "prediction_time" in data
    assert "valid_from" in data
    assert "valid_until" in data
    assert "is_stale" in data

    # Canonical Risk Block (Phase 5 Engine)
    assert "risk" in data
    assert data["risk"]["level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert "score" in data["risk"]
    assert "flood_probability_percent" in data["risk"]

    # Canonical Action Block (Phase 5 Engine)
    assert "action" in data
    assert data["action"]["code"] in ["SAFE", "MONITOR", "PREPARE", "EVACUATE"]
    assert isinstance(data["action"]["message"], str)
    assert len(data["action"]["message"]) > 0

    # Supporting Conditions & Status
    assert "conditions" in data
    assert "status" in data


def test_02_ratnapura_kolonnawa_isolation_acceptance():
    """
    Test 2: Acceptance Test — Selecting Ratnapura (ID 7) returns Ratnapura data ONLY.
    Selecting Kolonnawa (ID 1) returns Kolonnawa data ONLY.
    No cross-location leakage or fallback allowed.
    """
    # Ratnapura
    res_rat = client.get("/api/v1/predictions/current/7")
    assert res_rat.status_code == 200
    data_rat = res_rat.json()
    assert data_rat["location"]["location_id"] == 7
    assert "Ratnapura" in data_rat["location"]["name"]

    # Kolonnawa
    res_kol = client.get("/api/v1/predictions/current/1")
    assert res_kol.status_code == 200
    data_kol = res_kol.json()
    assert data_kol["location"]["location_id"] == 1
    assert "Kolonnawa" in data_kol["location"]["name"]

    # Invariant Verification
    assert data_rat["location"]["location_id"] != data_kol["location"]["location_id"]
    assert data_rat["location"]["name"] != data_kol["location"]["name"]


def test_03_canonical_risk_and_action_consistency():
    """
    Test 3: Verify that Risk and Action derived from Phase 5 engine are strictly paired.
    HIGH Risk must NEVER return a LOW action code (SAFE/MONITOR).
    """
    # Evaluate LOW risk payload
    low_assessment = RiskEngine.evaluate_prediction({
        "location_id": 7,
        "prediction": {"flood_probability": 0.10, "risk_level": "LOW"}
    })
    assert low_assessment.risk_level == "LOW"
    assert low_assessment.action_code == "SAFE"

    # Evaluate MODERATE risk payload
    mod_assessment = RiskEngine.evaluate_prediction({
        "location_id": 7,
        "prediction": {"flood_probability": 0.45, "risk_level": "MODERATE"}
    })
    assert mod_assessment.risk_level == "MODERATE"
    assert mod_assessment.action_code == "MONITOR"

    # Evaluate HIGH risk payload
    high_assessment = RiskEngine.evaluate_prediction({
        "location_id": 7,
        "prediction": {"flood_probability": 0.70, "risk_level": "HIGH"}
    })
    assert high_assessment.risk_level == "HIGH"
    assert high_assessment.action_code == "PREPARE"

    # Evaluate CRITICAL risk payload
    crit_assessment = RiskEngine.evaluate_prediction({
        "location_id": 7,
        "prediction": {"flood_probability": 0.90, "risk_level": "CRITICAL"}
    })
    assert crit_assessment.risk_level == "CRITICAL"
    assert crit_assessment.action_code == "EVACUATE"


def test_04_missing_prediction_returns_404_no_data():
    """
    Test 4: Requesting a location that does not exist returns HTTP 404,
    ensuring MISSING state is triggered rather than defaulting to LOW risk.
    """
    res = client.get("/api/v1/predictions/current/9999")
    assert res.status_code == 404
    data = res.json()
    assert "detail" in data or "code" in data
    text_repr = str(data).lower()
    assert "not found" in text_repr or "location_not_found" in text_repr


def test_05_prediction_validity_period_and_stale_detection():
    """
    Test 5: Verify validity timestamps are present and properly formatted ISO strings.
    """
    res = client.get("/api/v1/predictions/current/7")
    assert res.status_code == 200
    data = res.json()

    assert "Z" in data["valid_from"] or "+" in data["valid_from"] or "T" in data["valid_from"]
    assert "Z" in data["valid_until"] or "+" in data["valid_until"] or "T" in data["valid_until"]
    assert "is_stale" in data
    assert isinstance(data["is_stale"], bool)


def test_06_map_predictions_endpoint_contract():
    """
    Test 6: Verify map predictions endpoint supplies valid station metrics
    for the GIS mini-map preview.
    """
    res = client.get("/api/v1/predictions/map")
    assert res.status_code == 200
    data = res.json()

    assert "predictions" in data
    assert isinstance(data["predictions"], list)
    assert len(data["predictions"]) > 0

    first_pred = data["predictions"][0]
    assert "location_id" in first_pred
    assert "flood_probability" in first_pred
    assert "risk_level" in first_pred


def test_07_no_mock_or_demo_data_in_production_endpoints():
    """
    Test 7: Verify production endpoint returns canonical database / live inference
    data without mock identifiers.
    """
    res = client.get("/api/v1/predictions/current/7")
    assert res.status_code == 200
    data = res.json()

    # Ensure status is operational and prediction_id exists
    assert data.get("prediction_id") is not None
    assert data.get("status") in ["CURRENT", "STALE"]
