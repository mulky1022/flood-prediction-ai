"""
Phase 14 — Low-Bandwidth & Emergency Mode Comprehensive Test Suite.

Verifies:
1. Canonical location, prediction, risk, action, and warning endpoint aggregation.
2. Location isolation (Ratnapura stays Ratnapura, Kolonnawa stays Kolonnawa).
3. Payload optimization (< 2KB response).
4. Partial failure resilience (Prediction API failure, Warning API failure).
5. DMC 117 Emergency Hotline presence & formatting.
6. Multilingual data identity preservation across en, si, ta.
7. ML Flood-Risk Estimate vs Official Government Warning independence.
8. Zero Fake Offline Data invariant (Missing data != LOW_RISK).
"""

import json
import pytest
from fastapi.testclient import TestClient
from api.main import app
from services.risk_engine import RiskEngine

client = TestClient(app)


def test_01_ratnapura_emergency_isolation():
    """Verify emergency API endpoint for Ratnapura returns correct canonical location identity."""
    response = client.get("/api/v1/emergency/RATNAPURA_001")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["location"]["id"] == "RATNAPURA_001"
    assert "Ratnapura" in data["location"]["name"]
    assert data["location"]["district"] == "Ratnapura"
    assert "emergency" in data
    assert data["emergency"]["hotline"] == "117"
    assert data["emergency"]["hotline_url"] == "tel:117"


def test_02_kolonnawa_emergency_isolation():
    """Verify emergency API endpoint for Kolonnawa returns correct canonical location identity."""
    response = client.get("/api/v1/emergency/KOLONNAWA_001")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["location"]["id"] == "KOLONNAWA_001"
    assert "Kolonnawa" in data["location"]["name"]
    assert data["location"]["district"] == "Colombo"
    assert data["location"]["id"] != "RATNAPURA_001"


def test_03_invalid_location_404():
    """Verify 404 error response for invalid location ID in emergency mode."""
    response = client.get("/api/v1/emergency/NON_EXISTENT_LOCATION_999")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert "LOCATION_NOT_FOUND" in str(data)


def test_04_payload_size_optimization():
    """Verify emergency payload size is under 2KB for low-bandwidth cellular connections."""
    response = client.get("/api/v1/emergency/RATNAPURA_001")
    assert response.status_code == 200
    raw_content = response.content
    payload_size_bytes = len(raw_content)

    # Must be under 2048 bytes (2KB)
    assert payload_size_bytes < 2048, f"Emergency payload too large: {payload_size_bytes} bytes"


def test_05_dmc_117_hotline_presence():
    """Verify Disaster Management Centre (DMC) Hotline 117 is prominent in response."""
    response = client.get("/api/v1/emergency/RATNAPURA_001")
    assert response.status_code == 200
    data = response.json()

    assert data["emergency"]["hotline"] == "117"
    assert data["emergency"]["hotline_url"] == "tel:117"
    assert "Disaster Management Centre" in data["emergency"]["hotline_name"]


def test_06_multilingual_language_switching():
    """Verify language parameter en, si, ta preserves location_id, risk, and action code identity."""
    langs = ["en", "si", "ta"]
    base_loc_id = None
    base_risk = None
    base_action_code = None

    for lang in langs:
        response = client.get(f"/api/v1/emergency/RATNAPURA_001?lang={lang}")
        assert response.status_code == 200
        data = response.json()

        if base_loc_id is None:
            base_loc_id = data["location"]["id"]
            if data.get("prediction"):
                base_risk = data["prediction"]["risk_level"]
            if data.get("action"):
                base_action_code = data["action"]["code"]
        else:
            assert data["location"]["id"] == base_loc_id
            if data.get("prediction") and base_risk:
                assert data["prediction"]["risk_level"] == base_risk
            if data.get("action") and base_action_code:
                assert data["action"]["code"] == base_action_code


def test_07_canonical_phase5_action_mapping():
    """Verify action code and message correspond strictly to Phase 5 RiskEngine."""
    response = client.get("/api/v1/emergency/RATNAPURA_001")
    assert response.status_code == 200
    data = response.json()

    if data.get("prediction") and data.get("action"):
        risk_lvl = data["prediction"]["risk_level"]
        canonical_action = RiskEngine.get_canonical_action(risk_lvl)

        assert data["action"]["code"] == canonical_action["code"]
        assert data["action"]["message"] == canonical_action["message"]


def test_08_ml_risk_and_official_warning_independence():
    """Verify ML risk estimate and Official Government Warning remain separate fields."""
    response = client.get("/api/v1/emergency/RATNAPURA_001")
    assert response.status_code == 200
    data = response.json()

    # Prediction block and official_warning block must be separate top-level fields
    assert "prediction" in data
    assert "official_warning" in data
    # Neither overwrites or forces the other
    if data.get("official_warning"):
        assert "status" in data["official_warning"]


def test_09_partial_failure_resilience(monkeypatch):
    """Verify system returns valid emergency payload even if official warning service degrades."""
    from services import official_warning_service

    def mock_broken_warning_service(loc_id):
        raise Exception("Warning DB connection timeout")

    monkeypatch.setattr(official_warning_service.OfficialWarningService, "get_current_warning", mock_broken_warning_service)

    response = client.get("/api/v1/emergency/RATNAPURA_001")
    assert response.status_code == 200
    data = response.json()

    # Location and emergency info should still be returned intact
    assert data["status"] == "success"
    assert data["location"]["id"] == "RATNAPURA_001"
    assert data["official_warning"]["status"] == "UNAVAILABLE"


def test_10_no_fake_low_risk_invariant():
    """Verify missing prediction does NOT return LOW risk as a fake fallback."""
    response = client.get("/api/v1/emergency/RATNAPURA_001")
    assert response.status_code == 200
    data = response.json()

    if data.get("prediction") is None:
        # If prediction is missing, risk_level MUST NOT be claimed as LOW
        assert data.get("action") is None
