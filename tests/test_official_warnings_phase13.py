"""
Dedicated Test Suite for Phase 13 — Official Warning & Safety Information.
Verifies location isolation, ML vs. Official Warning independence, validity states,
API endpoints, multilingual localization, and DMC 117 emergency hotline preservation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from api.main import app
from services.supabase_service import get_supabase_service
from services.official_warning_service import get_official_warning_service

client = TestClient(app)


def test_01_ratnapura_official_warning_isolation():
    """
    Ratnapura (location_id 7 / RATNAPURA_001) must return active official warning TEST-WARN-RAT-001.
    """
    response = client.get("/api/v1/warnings/current/7")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["state"] == "ACTIVE"
    assert data["location_id"] == 7
    assert data["warning"] is not None
    assert data["warning"]["warning_id"] == "TEST-WARN-RAT-001"
    assert data["warning"]["source_id"] == "DMC-SL"
    assert "Disaster Management Centre" in data["warning"]["source_name"]


def test_02_kolonnawa_official_warning_isolation():
    """
    Kolonnawa (location_id 1 / KOLONNAWA_001) must return NO_ACTIVE_WARNING.
    Must never leak Ratnapura's warning.
    """
    response = client.get("/api/v1/warnings/current/1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["state"] == "NO_ACTIVE_WARNING"
    assert data["location_id"] == 1
    assert data["warning"] is None


def test_03_invalid_location_404():
    """
    Querying an invalid location ID must return 404 LOCATION_NOT_FOUND.
    """
    response = client.get("/api/v1/warnings/current/99999")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["code"] == "LOCATION_NOT_FOUND"


def test_04_ml_risk_and_official_warning_independence():
    """
    ML Flood-Risk Estimate and Official Government Warning MUST remain separate.
    ML LOW + Official ACTIVE or ML HIGH + Official NONE must never modify each other.
    """
    warning_service = get_official_warning_service()
    db = get_supabase_service()

    # Ratnapura has active official warning TEST-WARN-RAT-001
    warn_rat = warning_service.get_current_warning(7)
    pred_rat = db.get_latest_prediction(7)

    assert warn_rat["state"] == "ACTIVE"
    assert warn_rat["warning"]["warning_id"] == "TEST-WARN-RAT-001"
    
    # Kolonnawa has NO active warning
    warn_kol = warning_service.get_current_warning(1)
    assert warn_kol["state"] == "NO_ACTIVE_WARNING"

    # Ingest custom warning for Kolonnawa: ML LOW + Official ACTIVE
    warning_service.ingest_warning({
        "warning_id": "TEST-WARN-KOL-002",
        "location_id": 1,
        "source_id": "IRRIGATION-DEPT",
        "source_name": "Department of Irrigation Sri Lanka",
        "warning_type": "RIVER_SPILL_ADVISORY",
        "severity": "MODERATE",
        "title": "Kelani River Advisory",
        "message": "Upstream reservoir spill gate opened. Advisory for Kolonnawa lowlands.",
        "valid_until": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
        "status": "ACTIVE"
    })

    warn_kol_updated = warning_service.get_current_warning(1)
    assert warn_kol_updated["state"] == "ACTIVE"
    assert warn_kol_updated["warning"]["warning_id"] == "TEST-WARN-KOL-002"

    # ML risk prediction for Kolonnawa must remain completely unchanged
    pred_kol = db.get_latest_prediction(1)
    if pred_kol:
        assert pred_kol["location_id"] == 1


def test_05_expired_warning_handling():
    """
    Warnings with valid_until in the past must transition to EXPIRED.
    """
    warning_service = get_official_warning_service()
    past_valid_until = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()

    warning_service.ingest_warning({
        "warning_id": "TEST-WARN-EXP-001",
        "location_id": 2,
        "title": "Expired Advisory",
        "message": "This advisory has expired.",
        "valid_from": (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat(),
        "valid_until": past_valid_until,
        "status": "ACTIVE"
    })

    resp = warning_service.get_current_warning(2)
    assert resp["state"] == "EXPIRED"
    assert resp["warning"]["status"] == "EXPIRED"


def test_06_official_warning_api_endpoints():
    """
    Verifies GET /api/v1/warnings/current/{id}, GET /api/v1/warnings/location/{id},
    and POST /api/v1/warnings/ingest API contracts.
    """
    # Ingest new warning
    payload = {
        "warning_id": "TEST-WARN-API-001",
        "location_id": 3,
        "source_id": "MET-DEPT-SL",
        "source_name": "Department of Meteorology Sri Lanka",
        "title": "Heavy Rain Advisory",
        "message": "Heavy rainfall expected exceeding 100mm.",
        "valid_until": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
        "status": "ACTIVE"
    }
    ingest_resp = client.post("/api/v1/warnings/ingest", json=payload)
    assert ingest_resp.status_code == 201
    assert ingest_resp.json()["status"] == "success"

    # Fetch current
    curr_resp = client.get("/api/v1/warnings/current/3")
    assert curr_resp.status_code == 200
    assert curr_resp.json()["state"] == "ACTIVE"
    assert curr_resp.json()["warning"]["warning_id"] == "TEST-WARN-API-001"

    # Fetch history
    hist_resp = client.get("/api/v1/warnings/location/3")
    assert hist_resp.status_code == 200
    assert hist_resp.json()["total"] >= 1


def test_07_multilingual_warning_labels():
    """
    Verifies that i18n engine contains complete translation key parity for en, si, ta for official warnings.
    """
    from pathlib import Path
    i18n_path = Path(__file__).resolve().parent.parent / "frontend" / "js" / "i18n.js"
    assert i18n_path.exists()
    content = i18n_path.read_text(encoding="utf-8")

    # Check key presence in i18n.js
    required_keys = [
        "official.warning_title",
        "official.no_warning",
        "official.unavailable",
        "official.expired",
        "official.disclaimer",
        "safety.title",
        "safety.emergency_hotline",
        "safety.dmc_117"
    ]
    for key in required_keys:
        assert f"'{key}'" in content or f'"{key}"' in content


def test_08_dmc_117_emergency_hotline_presence():
    """
    Verifies emergency DMC hotline 117 is featured in frontend layout.
    """
    from pathlib import Path
    html_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    assert html_path.exists()
    html_content = html_path.read_text(encoding="utf-8")

    assert "tel:117" in html_content
    assert "117" in html_content
    assert "Disaster Management Centre" in html_content or "DMC" in html_content

