"""
Phase 3 — Unified Prediction API Dedicated Test Suite.
Verifies location safety, canonical schema compliance, status calculation, map predictions, history isolation, and zero cross-location fallback.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from services.supabase_service import get_supabase_service

client = TestClient(app)


def test_01_ratnapura_current_prediction():
    """
    Test A — GET current prediction for Ratnapura (ID 7 / LOC-007).
    Must return location_id = 7 and valid canonical fields.
    """
    response = client.get("/api/v1/predictions/current/7")
    assert response.status_code == 200
    data = response.json()

    assert "location" in data
    assert data["location"]["location_id"] == 7
    assert data["location"]["district"] == "Ratnapura"
    assert "prediction_id" in data
    assert "risk" in data
    assert "level" in data["risk"]
    assert "score" in data["risk"]
    assert data["status"] in ["CURRENT", "STALE", "EXPIRED"]


def test_02_kolonnawa_current_prediction():
    """
    Test B — GET current prediction for Kolonnawa (ID 1 / LOC-001).
    Must return location_id = 1 and valid canonical fields.
    """
    response = client.get("/api/v1/predictions/current/1")
    assert response.status_code == 200
    data = response.json()

    assert "location" in data
    assert data["location"]["location_id"] == 1
    assert data["location"]["district"] == "Colombo"
    assert "prediction_id" in data
    assert "risk" in data
    assert "level" in data["risk"]
    assert data["status"] in ["CURRENT", "STALE", "EXPIRED"]


def test_03_prediction_isolation_ratnapura_vs_kolonnawa():
    """
    Test C — Isolation: Ensure Ratnapura and Kolonnawa predictions are distinct.
    """
    res_rat = client.get("/api/v1/predictions/current/7").json()
    res_kol = client.get("/api/v1/predictions/current/1").json()

    assert res_rat["location"]["location_id"] == 7
    assert res_kol["location"]["location_id"] == 1
    assert res_rat["location"]["name"] != res_kol["location"]["name"]


def test_04_unknown_location_error():
    """
    Test D — Request prediction for unknown location (ID 99999).
    Expects 404 LOCATION_NOT_FOUND.
    """
    response = client.get("/api/v1/predictions/current/99999")
    assert response.status_code == 404
    data = response.json()
    err_code = data.get("code") or (data.get("detail", {}).get("code") if isinstance(data.get("detail"), dict) else None)
    assert err_code == "LOCATION_NOT_FOUND"


def test_05_prediction_by_id():
    """
    Test F — Retrieve prediction record by database prediction_id.
    """
    # 1. Run live prediction to generate & store record
    predict_res = client.get("/api/v1/predict/7").json()
    pred_id = predict_res["prediction_id"]

    # 2. Lookup prediction by ID
    response = client.get(f"/api/v1/predictions/id/{pred_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == pred_id
    assert data["location_id"] == 7
    assert "flood_probability" in data


def test_06_prediction_by_id_not_found():
    """
    Test F2 — Lookup non-existent prediction ID.
    Expects 404 PREDICTION_NOT_FOUND.
    """
    response = client.get("/api/v1/predictions/id/99999999")
    assert response.status_code == 404
    data = response.json()
    err_code = data.get("code") or (data.get("detail", {}).get("code") if isinstance(data.get("detail"), dict) else None)
    assert err_code == "PREDICTION_NOT_FOUND"


def test_07_history_isolation():
    """
    Test G — History isolation: Ratnapura history must contain ONLY location_id = 7.
    """
    response = client.get("/api/v1/predictions/history/7?limit=20")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["location_id"] == 7
    for item in data["items"]:
        assert item["location_id"] == 7


def test_08_map_predictions_endpoint():
    """
    Test H — Map Predictions: Verify batch response returns 33 stations with prediction metadata.
    """
    response = client.get("/api/v1/predictions/map")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["total"] == 33
    assert len(data["predictions"]) == 33

    # Verify first item structure
    item = data["predictions"][0]
    assert "location_id" in item
    assert "record_id" in item
    assert "name" in item
    assert "district" in item
    assert "risk_level" in item
    assert "flood_probability" in item
    assert "status" in item


def test_09_canonical_contract_structure():
    """
    Test I — Verify complete canonical prediction payload contract conformity.
    """
    response = client.get("/api/v1/predictions/current/7")
    assert response.status_code == 200
    data = response.json()

    # Top-level canonical keys
    required_keys = ["prediction_id", "location", "prediction_time", "valid_from", "valid_until", "risk", "status"]
    for key in required_keys:
        assert key in data, f"Missing canonical key: '{key}'"

    # Risk object keys
    assert "level" in data["risk"]
    assert "score" in data["risk"]

    # Location object keys
    assert "location_id" in data["location"]
    assert "name" in data["location"]
    assert "district" in data["location"]


def test_10_zero_cross_location_fallback():
    """
    Test J — Zero Cross-Location Fallback Invariant.
    When querying location 13 (Akuressa / Matara), it must NEVER return location 1 (Kolonnawa) or 7 (Ratnapura).
    """
    response = client.get("/api/v1/predictions/current/13")
    assert response.status_code == 200
    data = response.json()

    assert data["location"]["location_id"] == 13
    assert data["location"]["district"] == "Matara"
    assert data["location"]["location_id"] != 1
    assert data["location"]["location_id"] != 7
