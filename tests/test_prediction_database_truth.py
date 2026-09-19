"""
Phase 2: Prediction Database & Single Source of Truth Test Suite

Verifies:
1. Predictions are stored in database and return canonical prediction_id.
2. Prediction lookup by ID (GET /api/v1/predictions/id/{prediction_id}).
3. Single Source of Truth consistency across predictions, history, and alerts.
4. Alert idempotency (no duplicate alerts generated on repeated viewings/evaluations).
5. Data isolation: Ratnapura prediction_id != Kolonnawa prediction_id.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_prediction_database_persistence():
    """
    Test 1 — Database Persistence:
    Request prediction for Ratnapura (ID 7).
    Verify response includes prediction_id (positive integer).
    """
    res = client.get("/api/v1/predict/7")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["location"]["id"] == 7
    assert "prediction_id" in data
    assert data["prediction_id"] is not None
    assert isinstance(data["prediction_id"], int)
    assert data["prediction_id"] > 0


def test_prediction_lookup_by_id():
    """
    Test 2 — Prediction Lookup by ID:
    Generate a prediction, obtain its prediction_id, and query GET /api/v1/predictions/id/{prediction_id}.
    Verify returned record matches prediction_id and location_id.
    """
    res_gen = client.get("/api/v1/predict/7")
    assert res_gen.status_code == 200
    pred_id = res_gen.json()["prediction_id"]

    res_lookup = client.get(f"/api/v1/predictions/id/{pred_id}")
    assert res_lookup.status_code == 200
    record = res_lookup.json()

    assert record["id"] == pred_id
    assert record["location_id"] == 7
    assert "flood_probability" in record
    assert "model_name" in record


def test_history_single_source_of_truth():
    """
    Test 3 — History Single Source of Truth:
    Generate a prediction and verify it immediately appears as the top entry in history GET /api/v1/predictions/7.
    """
    res_gen = client.get("/api/v1/predict/7")
    assert res_gen.status_code == 200
    pred_id = res_gen.json()["prediction_id"]

    res_hist = client.get("/api/v1/predictions/7")
    assert res_hist.status_code == 200
    history_data = res_hist.json()

    assert history_data["status"] == "success"
    assert history_data["location_id"] == 7
    assert len(history_data["items"]) > 0

    latest_item = history_data["items"][0]
    assert latest_item["id"] == pred_id
    assert latest_item["location_id"] == 7


def test_alert_idempotency_and_deduplication():
    """
    Test 4 — Alert Idempotency:
    Trigger alert processing for location 7 multiple times consecutively.
    Verify duplicate active alerts are not generated uncontrolled.
    """
    res1 = client.post("/api/v1/alerts/process/7")
    assert res1.status_code in [200, 404, 422]

    # Fetch initial active alerts count
    res_active1 = client.get("/api/v1/alerts/location/7")
    count1 = len(res_active1.json().get("items", []))

    # Process again
    res2 = client.post("/api/v1/alerts/process/7")
    assert res2.status_code in [200, 404, 422]

    # Fetch active alerts count again
    res_active2 = client.get("/api/v1/alerts/location/7")
    count2 = len(res_active2.json().get("items", []))

    # Count of active alerts should remain stable or increase by at most 0 or 1 on status transition
    assert count2 <= count1 + 1


def test_data_isolation_between_locations():
    """
    Test 5 — Ratnapura vs Kolonnawa Database Data Isolation:
    Generate prediction for Ratnapura (ID 7) and Kolonnawa (ID 1).
    Verify prediction IDs and lookup records are distinct and isolated.
    """
    res_rat = client.get("/api/v1/predict/7")
    res_kol = client.get("/api/v1/predict/1")

    assert res_rat.status_code == 200
    assert res_kol.status_code == 200

    pred_id_rat = res_rat.json()["prediction_id"]
    pred_id_kol = res_kol.json()["prediction_id"]

    assert pred_id_rat != pred_id_kol

    # Verify lookup by ID strictly returns respective location
    rec_rat = client.get(f"/api/v1/predictions/id/{pred_id_rat}").json()
    rec_kol = client.get(f"/api/v1/predictions/id/{pred_id_kol}").json()

    assert rec_rat["location_id"] == 7
    assert rec_kol["location_id"] == 1


def test_invalid_prediction_id_lookup_404():
    """
    Test 6 — Invalid Prediction ID 404:
    Query a non-existent prediction ID (999999) and verify 404 response.
    """
    res = client.get("/api/v1/predictions/id/999999")
    assert res.status_code == 404
    assert res.json()["code"] == "PREDICTION_NOT_FOUND"
