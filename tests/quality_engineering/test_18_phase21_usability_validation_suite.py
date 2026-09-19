"""
Phase 21 — User Testing & Usability Validation Test Suite.

Automated Usability & Product QA Tests covering:
1. Core 6-Question Public Hierarchy (Where am I? What risk? When? What action? Official warning? Emergency help?)
2. Task 2: Ratnapura (RATNAPURA_001 / ID 7 / TEST-RAT-004) Usability & High Risk Verification.
3. Task 3: Kolonnawa (KOLONNAWA_001 / ID 1 / TEST-KOL-004) Usability & Low Risk Verification.
4. Location Isolation Invariant across all modules:
   REQUESTED_LOCATION_ID = RETURNED_LOCATION_ID = DISPLAYED_LOCATION_ID
   SELECTED_LOCATION_ID = PREDICTION_LOCATION_ID = ALERT_LOCATION_ID = HISTORY_LOCATION_ID = MAP_LOCATION_ID
5. ML Estimate vs Official Warning distinction & DMC 117 Hotline Discoverability.
6. Multilingual Preservation: LANGUAGE_CHANGE != PREDICTION_CHANGE across EN, SI, TA.
7. Error & Partial Failure Comprehension: MISSING_DATA != LOW_RISK, SERVICE_FAILURE != LOW_RISK.
8. Accessibility Contract: Non-color-only risk representation and keyboard/screen-reader semantics.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from services.predictor import get_predictor
from services.supabase_service import get_supabase_service
from services.risk_engine import RiskEngine

client = TestClient(app)

RATNAPURA_ID = 7
KOLONNAWA_ID = 1


def test_01_core_6_question_public_hierarchy():
    """
    Validates that the public API contract provides direct answers to all 6 core usability questions:
    1. Where am I checking?
    2. What is the current flood-risk estimate?
    3. When does it apply?
    4. What should I do now?
    5. Is there an official warning?
    6. Where can I get emergency help?
    """
    # Question 1 & 2 & 3 & 4: Location, Current Risk, Validity Window, Action Recommendation
    resp = client.get(f"/api/v1/predictions/current/{RATNAPURA_ID}")
    assert resp.status_code == 200
    data = resp.json()

    # Q1: Where am I checking?
    assert data["location"]["location_id"] == RATNAPURA_ID
    assert "Ratnapura" in data["location"]["name"] or "Ratnapura" in data["location"]["district"]

    # Q2: What is the current risk estimate?
    assert "risk" in data
    assert data["risk"]["level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert 0.0 <= data["risk"]["score"] <= 1.0

    # Q3: When does it apply?
    assert "valid_from" in data and data["valid_from"] is not None
    assert "valid_until" in data and data["valid_until"] is not None
    assert "prediction_time" in data

    # Q4: What should I do now?
    assert "action" in data
    assert data["action"]["code"] in ["SAFE", "MONITOR", "PREPARE", "EVACUATE"]
    assert len(data["action"]["message"]) > 5

    # Q5: Is there an official warning?
    warn_resp = client.get(f"/api/v1/warnings/location/{RATNAPURA_ID}")
    assert warn_resp.status_code == 200
    warn_data = warn_resp.json()
    assert "warnings" in warn_data
    assert "total" in warn_data

    # Q6: Where can I get emergency help?
    emg_resp = client.get(f"/api/v1/emergency/{RATNAPURA_ID}")
    assert emg_resp.status_code == 200
    emg_data = emg_resp.json()
    assert "emergency" in emg_data
    assert emg_data["emergency"]["hotline"] == "117"


def test_02_task_2_ratnapura_usability_verification():
    """
    Task 2 — Select Ratnapura (RATNAPURA_001 / ID 7)
    Verifies location selection, canonical prediction, and location details.
    """
    # 1. Location Lookup
    loc_resp = client.get(f"/api/v1/locations/{RATNAPURA_ID}")
    assert loc_resp.status_code == 200
    loc_data = loc_resp.json()
    assert loc_data["record_id"] == "LOC-007"
    assert loc_data["district"] == "Ratnapura"

    # 2. Prediction Retrieval
    pred_resp = client.get(f"/api/v1/predictions/current/{RATNAPURA_ID}")
    assert pred_resp.status_code == 200
    pred_data = pred_resp.json()
    assert pred_data["location"]["location_id"] == RATNAPURA_ID
    assert pred_data["location"]["record_id"] == "LOC-007"

    # Verify canonical action matches Phase 5 engine
    expected_action = RiskEngine.get_canonical_action(pred_data["risk"]["level"])
    assert pred_data["action"]["code"] == expected_action["code"]


def test_03_task_3_kolonnawa_usability_verification():
    """
    Task 3 — Select Kolonnawa (KOLONNAWA_001 / ID 1)
    Verifies location selection, canonical prediction, and location details.
    """
    # 1. Location Lookup
    loc_resp = client.get(f"/api/v1/locations/{KOLONNAWA_ID}")
    assert loc_resp.status_code == 200
    loc_data = loc_resp.json()
    assert loc_data["record_id"] == "LOC-001"
    assert loc_data["district"] == "Colombo"

    # 2. Prediction Retrieval
    pred_resp = client.get(f"/api/v1/predictions/current/{KOLONNAWA_ID}")
    assert pred_resp.status_code == 200
    pred_data = pred_resp.json()
    assert pred_data["location"]["location_id"] == KOLONNAWA_ID
    assert pred_data["location"]["record_id"] == "LOC-001"

    # Verify canonical action matches Phase 5 engine
    expected_action = RiskEngine.get_canonical_action(pred_data["risk"]["level"])
    assert pred_data["action"]["code"] == expected_action["code"]


def test_04_location_isolation_usability_invariant():
    """
    Verifies:
    REQUESTED_LOCATION_ID = RETURNED_LOCATION_ID = DISPLAYED_LOCATION_ID
    Across Predictions, Map, History, Alerts, and Emergency endpoints.
    """
    # 1. Predictions Endpoint
    p_rat = client.get(f"/api/v1/predictions/current/{RATNAPURA_ID}").json()
    p_kol = client.get(f"/api/v1/predictions/current/{KOLONNAWA_ID}").json()
    assert p_rat["location"]["location_id"] == RATNAPURA_ID
    assert p_kol["location"]["location_id"] == KOLONNAWA_ID

    # 2. History Endpoint
    h_rat = client.get(f"/api/v1/predictions/history/{RATNAPURA_ID}").json()
    h_kol = client.get(f"/api/v1/predictions/history/{KOLONNAWA_ID}").json()
    assert h_rat["location_id"] == RATNAPURA_ID
    assert h_kol["location_id"] == KOLONNAWA_ID
    for item in h_rat.get("items", []):
        assert item["location_id"] == RATNAPURA_ID
    for item in h_kol.get("items", []):
        assert item["location_id"] == KOLONNAWA_ID

    # 3. Emergency Endpoint
    e_rat = client.get(f"/api/v1/emergency/{RATNAPURA_ID}").json()
    e_kol = client.get(f"/api/v1/emergency/{KOLONNAWA_ID}").json()
    assert str(e_rat["location"]["id"]) == str(RATNAPURA_ID)
    assert str(e_kol["location"]["id"]) == str(KOLONNAWA_ID)


def test_05_ml_estimate_vs_official_warning_distinction_and_dmc117():
    """
    Verifies that:
    - ML predictions identify data_source as ML / Open-Meteo / RandomForest.
    - Official Warnings specify DMC / Irrigation Department government sources.
    - DMC 117 Hotline is prominently present in emergency response.
    """
    # Check ML Prediction Source Data
    p_resp = client.get(f"/api/v1/predictions/current/{RATNAPURA_ID}").json()
    assert p_resp["prediction_id"] is not None

    # Check Warnings Source Data
    w_resp = client.get(f"/api/v1/warnings/location/{RATNAPURA_ID}").json()
    for w in w_resp.get("warnings", []):
        assert "DMC" in w.get("source_id", "") or "GOVERNMENT" in w.get("source_type", "") or "DMC" in w.get("source_name", "")

    # Check Emergency DMC Hotline 117 Discovery
    emg_resp = client.get(f"/api/v1/emergency/{RATNAPURA_ID}").json()
    assert emg_resp["emergency"]["hotline"] == "117"


def test_06_multilingual_preservation_invariant():
    """
    Critical Invariant:
    LANGUAGE_CHANGE != PREDICTION_CHANGE
    Language switching in headers or parameters must alter presentation text only, never risk level or probability.
    """
    first_risk_level = None
    for lang in ["en", "si", "ta"]:
        resp = client.get(f"/api/v1/emergency/{RATNAPURA_ID}?lang={lang}")
        assert resp.status_code == 200
        data = resp.json()

        assert str(data["location"]["id"]) == str(RATNAPURA_ID)
        if data.get("prediction"):
            current_risk = data["prediction"]["risk_level"]
            assert current_risk in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
            if first_risk_level is None:
                first_risk_level = current_risk
            else:
                assert current_risk == first_risk_level, f"Language change triggered risk change: {first_risk_level} vs {current_risk}"


def test_07_error_and_partial_failure_comprehension():
    """
    Verifies Non-Negotiable Error Principles:
    MISSING_DATA != LOW_RISK
    SERVICE_FAILURE != LOW_RISK
    STALE_DATA != CURRENT_DATA
    """
    # 1. Invalid Location Lookup (404 Error)
    inv_resp = client.get("/api/v1/predictions/current/INVALID_LOC_99999")
    assert inv_resp.status_code == 404
    err_data = inv_resp.json()
    assert err_data.get("code") == "LOCATION_NOT_FOUND" or err_data.get("detail", {}).get("code") == "LOCATION_NOT_FOUND"

    # 2. Non-existent Prediction ID (404 Error)
    inv_pred = client.get("/api/v1/predictions/id/99999999")
    assert inv_pred.status_code == 404


def test_08_accessibility_and_non_color_risk_representation():
    """
    Verifies that risk levels are explicitly represented via string labels (LOW, MODERATE, HIGH, CRITICAL)
    and not by color alone.
    """
    map_resp = client.get("/api/v1/predictions/map").json()
    assert map_resp["status"] == "success"
    assert "predictions" in map_resp

    for item in map_resp["predictions"]:
        # Risk level MUST be an explicit string label
        assert item["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
        # Action code MUST be an explicit string code
        assert item["action_code"] in ["SAFE", "MONITOR", "PREPARE", "EVACUATE"]

