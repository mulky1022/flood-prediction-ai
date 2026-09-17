"""
Phase 7: Alert Service Unit Tests.

Covers:
- Policy evaluation for LOW, MODERATE, HIGH, CRITICAL predictions
- Duplicate prevention for repeated high risk predictions
- Updating existing alerts on probability change
- Auto-resolution on risk decrease (HIGH -> LOW)
- Manual acknowledge and resolve transitions
"""

import pytest
from unittest.mock import MagicMock
from services.alert_service import AlertService
from services.supabase_service import SupabaseService
from services.predictor import PredictorService
from services.notification_service import NotificationService
from config.alert_config import (
    RISK_LEVEL_LOW,
    RISK_LEVEL_MODERATE,
    RISK_LEVEL_HIGH,
    RISK_LEVEL_CRITICAL,
    ALERT_STATUS_ACTIVE,
    ALERT_STATUS_ACKNOWLEDGED,
    ALERT_STATUS_RESOLVED,
)


@pytest.fixture
def mock_db():
    db = MagicMock(spec=SupabaseService)
    db.get_location.return_value = {
        "id": 7,
        "record_id": "LK-RAT-07",
        "place_name": "Ratnapura Town (Kalu Ganga Upper)",
        "district": "Ratnapura",
        "latitude": 6.6828,
        "longitude": 80.4014
    }
    db.save_alert.side_effect = lambda x: {"status": "success", "data": {**x, "id": 101}}
    db.update_alert.side_effect = lambda aid, upd: {**upd, "id": aid, "location_id": 7}
    db.resolve_alert.side_effect = lambda aid: {"id": aid, "status": "RESOLVED", "location_id": 7}
    db.acknowledge_alert.side_effect = lambda aid: {"id": aid, "status": "ACKNOWLEDGED", "location_id": 7}
    return db


@pytest.fixture
def mock_notification_service():
    notif = MagicMock(spec=NotificationService)
    notif.send_notification.return_value = {
        "overall_status": "NOT_REQUIRED",
        "channels": {"web_dashboard": {"status": "SENT"}}
    }
    return notif


def test_1_low_prediction_no_alert(mock_db, mock_notification_service):
    """TEST 1: LOW prediction -> No alert created."""
    mock_db.get_active_alert_for_location.return_value = None
    service = AlertService(db=mock_db, notification_service=mock_notification_service)

    pred_payload = {
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {"class": 0, "flood_probability": 0.15, "non_flood_probability": 0.85},
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }

    res = service.process_location_alert(7, pred_payload)
    assert res["status"] == "success"
    assert res["action_taken"] == "NO_ALERT_REQUIRED"
    assert res["alert"] is None
    mock_db.save_alert.assert_not_called()


def test_2_moderate_prediction_policy(mock_db, mock_notification_service):
    """TEST 2: MODERATE prediction -> Matches configured advisory policy."""
    mock_db.get_active_alert_for_location.return_value = None
    service = AlertService(db=mock_db, notification_service=mock_notification_service)

    pred_payload = {
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {"class": 0, "flood_probability": 0.45, "non_flood_probability": 0.55},
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }

    res = service.process_location_alert(7, pred_payload)
    assert res["status"] == "success"
    assert res["action_taken"] == "NO_ALERT_REQUIRED"


def test_3_high_prediction_alert_created(mock_db, mock_notification_service):
    """TEST 3: HIGH prediction -> Alert created."""
    mock_db.get_active_alert_for_location.return_value = None
    service = AlertService(db=mock_db, notification_service=mock_notification_service)

    pred_payload = {
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {"class": 1, "flood_probability": 0.72, "non_flood_probability": 0.28},
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }

    res = service.process_location_alert(7, pred_payload)
    assert res["status"] == "success"
    assert res["action_taken"] == "ALERT_CREATED"
    assert res["alert"] is not None
    assert res["alert"]["risk_level"] == RISK_LEVEL_HIGH
    assert res["alert"]["status"] == ALERT_STATUS_ACTIVE
    mock_db.save_alert.assert_called_once()


def test_4_critical_prediction_alert_created(mock_db, mock_notification_service):
    """TEST 4: CRITICAL prediction -> Alert created with critical urgency."""
    mock_db.get_active_alert_for_location.return_value = None
    service = AlertService(db=mock_db, notification_service=mock_notification_service)

    pred_payload = {
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {"class": 1, "flood_probability": 0.88, "non_flood_probability": 0.12},
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }

    res = service.process_location_alert(7, pred_payload)
    assert res["status"] == "success"
    assert res["action_taken"] == "ALERT_CREATED"
    assert res["alert"]["risk_level"] == RISK_LEVEL_CRITICAL


def test_5_duplicate_alert_prevented(mock_db, mock_notification_service):
    """TEST 5: Repeat same HIGH prediction -> No duplicate active alert created."""
    existing_alert = {
        "id": 101,
        "location_id": 7,
        "risk_level": "HIGH",
        "flood_probability": 0.72,
        "status": "ACTIVE",
        "created_at": "2026-09-17T10:00:00+05:30"
    }
    mock_db.get_active_alert_for_location.return_value = existing_alert
    service = AlertService(db=mock_db, notification_service=mock_notification_service)

    pred_payload = {
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {"class": 1, "flood_probability": 0.72, "non_flood_probability": 0.28},
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }

    res = service.process_location_alert(7, pred_payload)
    assert res["status"] == "success"
    assert res["action_taken"] == "ALERT_UPDATED"
    # save_alert must NOT be called; update_alert should be called instead
    mock_db.save_alert.assert_not_called()
    mock_db.update_alert.assert_called_once()


def test_6_existing_alert_updated(mock_db, mock_notification_service):
    """TEST 6: Existing HIGH alert updated with changed probability."""
    existing_alert = {
        "id": 101,
        "location_id": 7,
        "risk_level": "HIGH",
        "flood_probability": 0.65,
        "status": "ACTIVE"
    }
    mock_db.get_active_alert_for_location.return_value = existing_alert
    service = AlertService(db=mock_db, notification_service=mock_notification_service)

    pred_payload = {
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {"class": 1, "flood_probability": 0.78, "non_flood_probability": 0.22},
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }

    res = service.process_location_alert(7, pred_payload)
    assert res["status"] == "success"
    assert res["action_taken"] == "ALERT_UPDATED"
    assert res["alert"]["flood_probability"] == 0.78


def test_7_high_to_low_auto_resolution(mock_db, mock_notification_service):
    """TEST 7: HIGH -> LOW prediction -> Active alert auto-resolved."""
    existing_alert = {
        "id": 101,
        "location_id": 7,
        "risk_level": "HIGH",
        "flood_probability": 0.75,
        "status": "ACTIVE"
    }
    mock_db.get_active_alert_for_location.return_value = existing_alert
    service = AlertService(db=mock_db, notification_service=mock_notification_service)

    pred_payload = {
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {"class": 0, "flood_probability": 0.20, "non_flood_probability": 0.80},
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }

    res = service.process_location_alert(7, pred_payload)
    assert res["status"] == "success"
    assert res["action_taken"] == "ALERT_RESOLVED"
    mock_db.resolve_alert.assert_called_once_with(101)


def test_8_acknowledge_alert(mock_db, mock_notification_service):
    """TEST 8: Acknowledge alert -> Status transitions to ACKNOWLEDGED."""
    mock_db.get_alert_by_id.return_value = {
        "id": 101,
        "location_id": 7,
        "risk_level": "HIGH",
        "status": "ACTIVE"
    }
    service = AlertService(db=mock_db, notification_service=mock_notification_service)

    res = service.acknowledge_alert(101)
    assert res is not None
    assert res["status"] == ALERT_STATUS_ACKNOWLEDGED
    mock_db.acknowledge_alert.assert_called_once_with(101)
