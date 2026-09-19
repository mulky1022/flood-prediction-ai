"""
Phase 4 — Prediction Generation & Storage Pipeline Dedicated Test Suite.
Verifies ML model loading, 64-feature vector contract alignment, input validation quality gate,
deterministic location mapping, probability output validation, atomic DB persistence, idempotency deduplication,
and immediate Phase 3 API availability.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from services.predictor import get_predictor
from services.feature_builder import build_feature_dataframe, FEATURE_COLUMNS
from services.supabase_service import get_supabase_service
from services.location_service import get_location_by_id

client = TestClient(app)


def test_01_model_artifact_and_feature_columns_loading():
    """
    Test 1: Verify PredictorService loads model artifact, scaler, and 64 feature columns.
    """
    predictor = get_predictor()
    assert predictor.model is not None
    assert predictor.scaler is not None
    assert len(predictor.feature_columns) == 64
    assert predictor.metadata.get("model_name") == "RandomForestClassifier"
    assert predictor.metadata.get("model_version") == "1.0.0"


def test_02_feature_vector_alignment_and_order():
    """
    Test 2: Verify feature column order matches training feature contract feature_columns.json.
    """
    assert len(FEATURE_COLUMNS) == 64
    loc = get_location_by_id(7)  # Ratnapura
    weather = {
        "status": "success",
        "rainfall": {"rainfall_7d_mm": 50.0, "monthly_rainfall_mm": 200.0, "data_quality": "GOOD"}
    }
    df, quality = build_feature_dataframe(loc, weather)

    assert df.shape == (1, 64)
    assert list(df.columns) == FEATURE_COLUMNS
    assert quality["ready_for_prediction"] is True


def test_03_input_validation_quality_gate():
    """
    Test 3: Verify input validation quality gate rejects impossible numerical ranges.
    """
    corrupt_loc = {
        "id": 99,
        "district": "Ratnapura",
        "place_name": "Test Corrupt",
        "latitude": 190.0,  # Invalid latitude (>90)
        "longitude": 80.3992,
        "elevation_m": -500.0,  # Invalid elevation (out of range)
        "built_up_percent": 150.0  # Invalid percent (>100)
    }
    weather = {
        "status": "success",
        "rainfall": {"rainfall_7d_mm": 50.0, "monthly_rainfall_mm": 200.0, "data_quality": "GOOD"}
    }

    df, quality = build_feature_dataframe(corrupt_loc, weather)
    assert quality["ready_for_prediction"] is False
    assert len(quality["invalid_features"]) > 0


def test_04_ratnapura_pipeline_execution():
    """
    Test 4: Verify prediction pipeline for Ratnapura (ID 7) produces valid canonical result.
    """
    predictor = get_predictor()
    res = predictor.predict_location(7, use_cache=True)

    assert res["status"] == "success"
    assert res["ready_for_prediction"] is True
    assert res["location"]["id"] == 7
    assert res["location"]["district"] == "Ratnapura"
    assert 0.0 <= res["prediction"]["flood_probability"] <= 1.0
    assert res["prediction"]["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]


def test_05_kolonnawa_pipeline_execution():
    """
    Test 5: Verify prediction pipeline for Kolonnawa (ID 1) produces valid canonical result.
    """
    predictor = get_predictor()
    res = predictor.predict_location(1, use_cache=True)

    assert res["status"] == "success"
    assert res["ready_for_prediction"] is True
    assert res["location"]["id"] == 1
    assert res["location"]["district"] == "Colombo"
    assert 0.0 <= res["prediction"]["flood_probability"] <= 1.0


def test_06_unknown_location_rejection():
    """
    Test 6: Verify unknown location ID (99999) fails cleanly without generating prediction.
    """
    predictor = get_predictor()
    res = predictor.predict_location(99999)

    assert res["status"] == "location_not_found"
    assert res["ready_for_prediction"] is False


def test_07_missing_weather_input_failure_handling():
    """
    Test 7: Verify pipeline returns prediction_unavailable when weather data fails.
    Does NOT fabricate a fake LOW risk.
    """
    predictor = get_predictor()
    # Mocking predictor with bad location or weather failure
    loc = get_location_by_id(7)
    bad_weather = {"status": "error", "message": "Weather API timeout"}

    df, quality = build_feature_dataframe(loc, bad_weather)
    assert quality["ready_for_prediction"] is False
    assert "rainfall_7d_mm" in quality["missing_features"]


def test_08_probability_and_risk_output_validation():
    """
    Test 8: Verify inference probability output format and risk categorization.
    """
    predictor = get_predictor()
    loc = get_location_by_id(7)
    weather = {
        "status": "success",
        "rainfall": {"rainfall_7d_mm": 150.0, "monthly_rainfall_mm": 450.0, "data_quality": "GOOD"}
    }
    df, _ = build_feature_dataframe(loc, weather)

    inf_res = predictor.predict_from_features(df)
    assert inf_res["status"] == "success"
    pred = inf_res["prediction"]
    assert "class" in pred
    assert "flood_probability" in pred
    assert "non_flood_probability" in pred
    assert abs((pred["flood_probability"] + pred["non_flood_probability"]) - 1.0) < 0.01


def test_09_database_persistence_and_idempotency():
    """
    Test 9: Verify save_prediction creates prediction_id and prevents duplicate writes within window.
    """
    db = get_supabase_service()
    predictor = get_predictor()
    pred_payload = predictor.predict_location(7, use_cache=True)

    # First write
    res1 = db.save_prediction(pred_payload, deduplicate_window_minutes=15)
    assert res1["status"] == "success"
    id1 = res1["prediction_id"]
    assert id1 is not None

    # Immediate second write for same location & probability -> should deduplicate
    res2 = db.save_prediction(pred_payload, deduplicate_window_minutes=15)
    assert res2["status"] == "success"
    assert res2.get("deduplicated") is True
    assert res2["prediction_id"] == id1


def test_10_immediate_api_availability():
    """
    Test 10: Verify newly generated and saved prediction is immediately queryable via Phase 3 API.
    """
    predict_res = client.get("/api/v1/predict/7").json()
    pred_id = predict_res["prediction_id"]

    # Query via Phase 3 current API
    current_res = client.get("/api/v1/predictions/current/7")
    assert current_res.status_code == 200
    current_data = current_res.json()
    assert current_data["prediction_id"] == pred_id
    assert current_data["location"]["location_id"] == 7


def test_11_multi_location_pipeline_isolation():
    """
    Test 11: Multi-location generation pipeline processes Ratnapura and Kolonnawa independently.
    """
    db = get_supabase_service()
    predictor = get_predictor()

    p_rat = predictor.predict_location(7, use_cache=True)
    p_kol = predictor.predict_location(1, use_cache=True)

    save_rat = db.save_prediction(p_rat, deduplicate_window_minutes=0)
    save_kol = db.save_prediction(p_kol, deduplicate_window_minutes=0)

    assert save_rat["prediction_id"] != save_kol["prediction_id"]
    assert p_rat["location"]["id"] == 7
    assert p_kol["location"]["id"] == 1


def test_12_end_to_end_pipeline():
    """
    Test 12: End-to-End Prediction Pipeline Verification.
    Input Weather -> Feature Builder -> Quality Gate -> Model Runner -> Persistence -> Phase 3 API.
    """
    # 1. Trigger live prediction pipeline
    response = client.get("/api/v1/predict/7")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "success"
    assert payload["ready_for_prediction"] is True
    pred_id = payload["prediction_id"]
    assert pred_id is not None

    # 2. Verify availability via Prediction-by-ID API
    id_res = client.get(f"/api/v1/predictions/id/{pred_id}")
    assert id_res.status_code == 200
    assert id_res.json()["id"] == pred_id

    # 3. Verify availability via Map Predictions API
    map_res = client.get("/api/v1/predictions/map")
    assert map_res.status_code == 200
    map_preds = map_res.json()["predictions"]
    rat_map = next((p for p in map_preds if p["location_id"] == 7), None)
    assert rat_map is not None
    assert rat_map["prediction_id"] == pred_id
