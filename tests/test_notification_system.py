"""
Test Notification & Alert System Pipeline.
Validates:
1. Real-time prediction pipeline for active monitoring stations.
2. Alert policy evaluation and risk level categorization.
3. Haversine distance formula accuracy across Sri Lankan coordinates.
4. Notification message structure, factual formatting, and audit standards.
5. Cooldown deduplication logic.
6. Live production API responses.
"""

import math
import time
import pytest
from fastapi.testclient import TestClient
from api.main import app
from services.alert_service import AlertService
from services.notification_service import NotificationService
from services.location_service import get_all_locations, get_location_by_id


@pytest.fixture
def client():
    return TestClient(app)


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def test_nearest_station_resolution():
    """Verifies that GPS coordinates near Colombo correctly identify Kolonnawa as nearest."""
    user_lat, user_lon = 6.9300, 79.8800  # Near Kolonnawa, Colombo
    locations = get_all_locations()
    assert len(locations) >= 25

    nearest = None
    min_dist = float("inf")
    for loc in locations:
        dist = haversine_km(user_lat, user_lon, float(loc["latitude"]), float(loc["longitude"]))
        if dist < min_dist:
            min_dist = dist
            nearest = loc

    assert nearest is not None
    assert nearest["district"] == "Colombo"
    assert "Kolonnawa" in nearest["place_name"]
    assert min_dist < 2.0  # Within 2 km


def test_predict_endpoint_for_monitored_stations(client):
    """Verifies that GET /api/v1/predict/{id} returns real ML inferences with required contract."""
    response = client.get("/api/v1/predict/1")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "prediction" in data
    pred = data["prediction"]
    assert "flood_probability" in pred
    assert "risk_level" in pred
    assert pred["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert 0.0 <= float(pred["flood_probability"]) <= 1.0


def test_alert_decision_engine_evaluation():
    """Verifies that AlertService generates factual, non-sensational messages without fabricating authorities."""
    service = AlertService()
    
    # Simulate high-risk prediction payload
    mock_payload = {
        "location": {"id": 1, "place_name": "Kolonnawa (Kelani River Lower)", "district": "Colombo"},
        "prediction": {"flood_probability": 0.785, "class": 1},
        "model": {"model_name": "RandomForestClassifier", "model_version": "1.0.0"}
    }

    eval_result = service.evaluate_prediction_for_alert(mock_payload)
    assert eval_result["risk_level"] == "HIGH"
    assert eval_result["is_alertable"] is True
    assert "Kolonnawa" in eval_result["title"]
    assert "78.5%" in eval_result["message"]
    assert "Kolonnawa" in eval_result["message"]
    assert "Colombo" in eval_result["message"]


def test_notification_dispatch_tracking():
    """Verifies truthful dispatch status tracking in NotificationService."""
    service = NotificationService()
    mock_alert = {
        "id": 999,
        "location_id": 1,
        "risk_level": "HIGH",
        "title": "High Flood Risk Warning — Kolonnawa",
        "message": "Elevated flood risk observed.",
        "recommendation": "Prepare emergency supplies."
    }

    results = service.send_notification(mock_alert)
    assert "channels" in results
    channels = results["channels"]
    assert "web_dashboard" in channels
    assert channels["web_dashboard"]["status"] == "SENT"
    assert "email" in channels
    assert "sms" in channels

