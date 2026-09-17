"""
Phase 7: Notification Service Unit Tests.

Covers:
- Notification success recording
- Notification failure recording
- Unconfigured provider fallback (truthful reporting)
"""

import pytest
from unittest.mock import patch, MagicMock
from services.notification_service import NotificationService
from config.alert_config import (
    NOTIFICATION_STATUS_SENT,
    NOTIFICATION_STATUS_FAILED,
    NOTIFICATION_STATUS_NOT_CONFIGURED,
    NOTIFICATION_STATUS_NOT_REQUIRED,
)


def test_9_notification_success():
    """TEST 9: Notification success -> notification_status = SENT."""
    custom_config = {
        "web_dashboard": {"enabled": True},
        "email": {
            "enabled": True,
            "smtp_host": "smtp.test.internal",
            "smtp_port": 587,
            "sender": "alerts@floodwatch.lk",
            "recipients": ["duty_officer@dmc.gov.lk"]
        },
        "sms": {"enabled": False}
    }
    service = NotificationService(config=custom_config)

    alert = {
        "id": 1,
        "location_id": 7,
        "risk_level": "HIGH",
        "title": "High Flood Risk",
        "message": "Elevated runoff",
        "recommendation": "Prepare channels"
    }

    with patch("smtplib.SMTP") as mock_smtp:
        mock_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_instance

        res = service.send_notification(alert)
        assert res["overall_status"] == NOTIFICATION_STATUS_SENT
        assert res["channels"]["email"]["status"] == NOTIFICATION_STATUS_SENT
        mock_instance.sendmail.assert_called_once()


def test_10_notification_failure():
    """TEST 10: Notification provider failure -> notification_status = FAILED."""
    custom_config = {
        "web_dashboard": {"enabled": True},
        "email": {
            "enabled": True,
            "smtp_host": "smtp.invalid.domain",
            "smtp_port": 587,
            "sender": "alerts@floodwatch.lk",
            "recipients": ["duty_officer@dmc.gov.lk"]
        },
        "sms": {"enabled": False}
    }
    service = NotificationService(config=custom_config)

    alert = {
        "id": 1,
        "location_id": 7,
        "risk_level": "HIGH",
        "title": "High Flood Risk",
        "message": "Elevated runoff"
    }

    with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("Connection refused")):
        res = service.send_notification(alert)
        assert res["overall_status"] == NOTIFICATION_STATUS_FAILED
        assert res["channels"]["email"]["status"] == NOTIFICATION_STATUS_FAILED
        assert "Connection refused" in res["channels"]["email"]["error"]


def test_unconfigured_notification_not_required():
    """Default local mode -> NOT_REQUIRED / NOT_CONFIGURED without fake success."""
    service = NotificationService()
    alert = {"id": 1, "location_id": 7, "risk_level": "HIGH", "title": "Test Alert"}

    res = service.send_notification(alert)
    assert res["overall_status"] == NOTIFICATION_STATUS_NOT_REQUIRED
    assert res["channels"]["email"]["status"] == NOTIFICATION_STATUS_NOT_CONFIGURED
    assert res["channels"]["sms"]["status"] == NOTIFICATION_STATUS_NOT_CONFIGURED
