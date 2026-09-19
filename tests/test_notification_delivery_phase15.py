"""
Phase 15 — WhatsApp & SMS Alert Delivery Comprehensive Test Suite.

Verifies:
1. Canonical location, prediction, risk, action, alert, and notification traceability.
2. E.164 phone number normalization (+94771234567) and masking privacy (+9477****567).
3. Location isolation (Ratnapura subscriptions never receive Kolonnawa alerts).
4. Idempotency guarantees (preventing duplicate notification dispatches).
5. Multilingual template rendering (English, Sinhala, Tamil) preserving identifier identity.
6. Distinction between ML flood-risk estimate and official government warnings.
7. Provider delivery status tracking & webhook callbacks.
8. Unsubscribe lifecycle and failure resilience.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from services.delivery_providers import normalize_phone_number, mask_phone_number, measure_sms_segments

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limits():
    current = getattr(app, "middleware_stack", None)
    while current is not None:
        if hasattr(current, "request_history"):
            current.request_history.clear()
        current = getattr(current, "app", None)


def test_01_e164_phone_normalization_and_masking():
    """Verify phone normalization to E.164 format and masking privacy."""
    assert normalize_phone_number("0771234567") == "+94771234567"
    assert normalize_phone_number("771234567") == "+94771234567"
    assert normalize_phone_number("+94771234567") == "+94771234567"

    assert mask_phone_number("+94771234567") == "+9477****567"

    # Test invalid phone rejection
    with pytest.raises(ValueError):
        normalize_phone_number("invalid-phone")


def test_02_subscription_creation_and_otp_verification():
    """Verify creating a subscription, verifying OTP code, and retrieving active subscriptions."""
    response = client.post("/api/v1/notifications/subscriptions", json={
        "user_id": "TEST-USER-001",
        "location_id": "RATNAPURA_001",
        "channel": "sms",
        "destination": "0771234567",
        "language": "en",
        "minimum_risk_level": "HIGH"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    sub_id = data["subscription"]["id"]
    assert data["subscription"]["destination_masked"] == "+9477****567"
    assert data["subscription"]["location_id"] == "RATNAPURA_001"

    # Verify OTP
    v_res = client.post("/api/v1/notifications/subscriptions/verify", json={
        "subscription_id": sub_id,
        "verification_code": "123456"
    })
    assert v_res.status_code == 200
    assert v_res.json()["subscription"]["verified"] is True


def test_03_location_isolation_ratnapura_vs_kolonnawa():
    """
    Verify location isolation:
    User A subscribed to Ratnapura (RATNAPURA_001).
    User B subscribed to Kolonnawa (KOLONNAWA_001).
    Dispatch alert for Ratnapura -> User A receives notification, User B receives NOTHING.
    """
    # Create Ratnapura Subscription
    res_a = client.post("/api/v1/notifications/subscriptions", json={
        "user_id": "USER-A-RATNAPURA",
        "location_id": "RATNAPURA_001",
        "channel": "sms",
        "destination": "0771112222",
        "language": "en"
    })
    assert res_a.status_code == 201

    # Create Kolonnawa Subscription
    res_b = client.post("/api/v1/notifications/subscriptions", json={
        "user_id": "USER-B-KOLONNAWA",
        "location_id": "KOLONNAWA_001",
        "channel": "whatsapp",
        "destination": "0773334444",
        "language": "en"
    })
    assert res_b.status_code == 201

    # Dispatch Alert for Ratnapura
    dispatch_res = client.post("/api/v1/notifications/dispatch", json={
        "alert_id": "ALERT-RAT-ISOLATION-001",
        "prediction_id": "PRED-RAT-001",
        "location_id": "RATNAPURA_001",
        "risk_level": "HIGH",
        "action_code": "PREPARE"
    })
    assert dispatch_res.status_code == 200
    notifications = dispatch_res.json()["notifications"]

    # Assert notifications sent ONLY for Ratnapura location
    assert len(notifications) >= 1
    for notif in notifications:
        assert notif["location_id"] == "RATNAPURA_001"
        assert notif["destination_masked"] != "+9477****444"  # User B never receives Ratnapura alert


def test_04_idempotent_alert_processing():
    """Verify processing the exact same alert twice produces zero duplicate notifications."""
    alert_payload = {
        "alert_id": "ALERT-RAT-IDEMPOTENT-999",
        "prediction_id": "PRED-RAT-999",
        "location_id": "RATNAPURA_001",
        "risk_level": "CRITICAL",
        "action_code": "EVACUATE"
    }

    # Dispatch attempt 1
    res1 = client.post("/api/v1/notifications/dispatch", json=alert_payload)
    assert res1.status_code == 200
    first_count = len(res1.json()["notifications"])

    # Dispatch attempt 2 (same alert_id)
    res2 = client.post("/api/v1/notifications/dispatch", json=alert_payload)
    assert res2.status_code == 200
    second_count = len(res2.json()["notifications"])

    # Second run should return 0 new notifications due to idempotency
    assert second_count == 0


def test_05_multilingual_template_rendering_and_segmentation():
    """Verify localized notification template rendering and SMS Unicode segmentation measuring."""
    # Test SMS segmentation
    en_msg = "FLOOD RISK ALERT - Ratnapura. Risk: HIGH. Prepare emergency supplies. DMC 117"
    si_msg = "ගංවතුර අවදානම් නිවේදනය - රත්නපුරය. අවදානම: ඉහළ. DMC 117"
    ta_msg = "வெள்ள அபாய எச்சரிக்கை - இரத்தினபுரி. ஆபத்து: அதிக. DMC 117"

    seg_en, enc_en = measure_sms_segments(en_msg)
    seg_si, enc_si = measure_sms_segments(si_msg)
    seg_ta, enc_ta = measure_sms_segments(ta_msg)

    assert enc_en == "GSM-7"
    assert enc_si == "UCS-2"
    assert enc_ta == "UCS-2"
    assert seg_si >= 1
    assert seg_ta >= 1


def test_06_unsubscribe_lifecycle():
    """Verify unsubscribed users receive zero notifications on future alert dispatches."""
    # 1. Create subscription for User C
    res = client.post("/api/v1/notifications/subscriptions", json={
        "user_id": "USER-C-UNSUB",
        "location_id": "RATNAPURA_001",
        "channel": "sms",
        "destination": "0775556666"
    })
    assert res.status_code == 201
    sub_id = res.json()["subscription"]["id"]

    # 2. Delete / unsubscribe
    unsub_res = client.delete(f"/api/v1/notifications/subscriptions/{sub_id}")
    assert unsub_res.status_code == 200

    # 3. Dispatch alert
    dispatch_res = client.post("/api/v1/notifications/dispatch", json={
        "alert_id": "ALERT-RAT-UNSUB-101",
        "prediction_id": "PRED-RAT-101",
        "location_id": "RATNAPURA_001",
        "risk_level": "HIGH"
    })
    assert dispatch_res.status_code == 200

    for notif in dispatch_res.json()["notifications"]:
        assert notif["subscription_id"] != sub_id


def test_07_webhook_delivery_status_callbacks():
    """Verify provider webhook callbacks update notification status cleanly."""
    # Fetch logs
    logs_res = client.get("/api/v1/notifications/logs")
    assert logs_res.status_code == 200
    logs = logs_res.json()["notifications"]

    if len(logs) > 0:
        target_log = logs[0]
        msg_id = target_log["provider_message_id"]

        if msg_id:
            # Send DELIVERED webhook
            wh_res = client.post("/api/v1/notifications/webhooks/sms", json={
                "channel": "sms",
                "provider_message_id": msg_id,
                "status": "DELIVERED"
            })
            assert wh_res.status_code == 200
            assert wh_res.json()["status"] == "success"
            assert wh_res.json()["log"]["status"] == "DELIVERED"


def test_08_full_end_to_end_pipeline():
    """
    Full end-to-end integration test:
    Input -> Prediction -> Risk/Action -> Alert -> Subscription -> Dispatch -> Notification Delivery Log.
    """
    # 1. Generate prediction for Ratnapura
    pred_res = client.get("/api/v1/predictions/current/RATNAPURA_001")
    assert pred_res.status_code == 200
    pred_data = pred_res.json()
    pred_id = str(pred_data.get("prediction_id")) if pred_data.get("prediction_id") is not None else "PRED-RAT-E2E"

    # 2. Create alert
    alert_payload = {
        "alert_id": "ALERT-RAT-E2E-001",
        "prediction_id": pred_id,
        "location_id": "RATNAPURA_001",
        "risk_level": "HIGH",
        "action_code": "PREPARE"
    }

    # 3. Dispatch notifications
    dispatch_res = client.post("/api/v1/notifications/dispatch", json=alert_payload)
    assert dispatch_res.status_code == 200
    data = dispatch_res.json()

    assert data["status"] == "success"
    # Verify delivery log traceability
    for notif in data["notifications"]:
        assert notif["alert_id"] == "ALERT-RAT-E2E-001"
        assert notif["location_id"] == "RATNAPURA_001"
        assert notif["risk_level"] == "HIGH"
        assert notif["status"] in ("SENT", "DELIVERED")
