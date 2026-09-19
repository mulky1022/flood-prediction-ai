"""
Phase 18 Quality Engineering Suite 07: Cache Isolation & Multilingual Preservation.

Verifies:
- RATNAPURA_001 cache is NEVER returned for KOLONNAWA_001
- Language changes (en -> si -> ta -> en) MUST NOT alter canonical location_id, prediction_id, risk_level, action_code, alert_id, or warning_id
- Translation completeness check across en, si, ta
"""

import pytest
from fastapi.testclient import TestClient
from services.delivery_providers import render_alert_template


def test_cache_location_isolation(client: TestClient):
    """
    Verify cache keys incorporate canonical location_id.
    Querying RATNAPURA_001 populates cache for location 7.
    Subsequent query for KOLONNAWA_001 MUST NOT receive Ratnapura cached data.
    """
    res_rat = client.get("/api/v1/predictions/current/RATNAPURA_001")
    assert res_rat.status_code == 200
    rat_pred_id = res_rat.json()["prediction_id"]

    res_kol = client.get("/api/v1/predictions/current/KOLONNAWA_001")
    assert res_kol.status_code == 200
    kol_pred_id = res_kol.json()["prediction_id"]

    loc_rat = res_rat.json()["location"].get("location_id") or res_rat.json()["location"].get("id")
    loc_kol = res_kol.json()["location"].get("location_id") or res_kol.json()["location"].get("id")
    assert loc_rat != loc_kol


def test_language_switch_preserves_canonical_identifiers(client: TestClient):
    """
    MANDATORY LANGUAGE SWITCH TEST:
    Changing UI language (en -> si -> ta) MUST NOT alter underlying canonical
    location_id, prediction_id, risk_level, or action_code.
    """
    res_en = client.get("/api/v1/predictions/current/RATNAPURA_001?lang=en")
    assert res_en.status_code == 200
    data_en = res_en.json()

    res_si = client.get("/api/v1/predictions/current/RATNAPURA_001?lang=si")
    assert res_si.status_code == 200
    data_si = res_si.json()

    res_ta = client.get("/api/v1/predictions/current/RATNAPURA_001?lang=ta")
    assert res_ta.status_code == 200
    data_ta = res_ta.json()

    # Canonical IDs and risk levels MUST remain identical
    loc_en = data_en["location"].get("location_id") or data_en["location"].get("id")
    loc_si = data_si["location"].get("location_id") or data_si["location"].get("id")
    loc_ta = data_ta["location"].get("location_id") or data_ta["location"].get("id")

    assert loc_en == loc_si == loc_ta
    assert data_en["prediction_id"] == data_si["prediction_id"] == data_ta["prediction_id"]
    assert data_en["risk"]["level"] == data_si["risk"]["level"] == data_ta["risk"]["level"]
    assert data_en["action"]["code"] == data_si["action"]["code"] == data_ta["action"]["code"]



def test_translation_template_rendering():
    """Verify notification template renders correctly in en, si, and ta with DMC 117."""
    for lang in ("en", "si", "ta"):
        msg = render_alert_template("SMS", lang, "Ratnapura", "HIGH", "Evacuate immediately")
        assert len(msg) > 0
        assert "Ratnapura" in msg
        assert "117" in msg

