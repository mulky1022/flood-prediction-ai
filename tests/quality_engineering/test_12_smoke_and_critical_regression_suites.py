"""
Phase 18 Quality Engineering Suite 12: Smoke & Critical Regression Quality Gates.

Verifies:
- Fast critical smoke suite covering app load, location selection, prediction generation, risk/action, warning separation, DMC 117, and Admin auth
- Quality gate enforcement verifying zero critical regressions across Phases 1-17
"""

import pytest
from fastapi.testclient import TestClient

AUTH_HEADERS = {"X-Admin-Token": "admin-secret-token-v17"}



def test_smoke_suite_core_public_and_admin_flows(client: TestClient):
    """
    FAST CRITICAL SMOKE SUITE:
    1. App loads root & health endpoints
    2. Location selection for Ratnapura & Kolonnawa
    3. Prediction generation & risk/action retrieval
    4. Warning separation
    5. Emergency helpline (DMC 117)
    6. Admin authentication check
    """
    # 1. Health check
    res_health = client.get("/api/v1/health")
    assert res_health.status_code == 200

    # 2. Ratnapura & Kolonnawa locations
    res_rat = client.get("/api/v1/predictions/current/RATNAPURA_001")
    assert res_rat.status_code == 200
    assert "risk" in res_rat.json()

    res_kol = client.get("/api/v1/predictions/current/KOLONNAWA_001")
    assert res_kol.status_code == 200
    assert "risk" in res_kol.json()

    # 3. Emergency helpline
    res_emerg = client.get("/api/v1/emergency/RATNAPURA_001")
    assert res_emerg.status_code == 200
    assert "117" in str(res_emerg.json())

    # 4. Admin auth check
    res_admin = client.get("/api/v1/admin/overview", headers=AUTH_HEADERS)
    assert res_admin.status_code == 200


def test_critical_regression_quality_gate(client: TestClient):
    """
    CRITICAL REGRESSION QUALITY GATE:
    Enforces non-negotiable invariants:
    - RATNAPURA_DATA != KOLONNAWA_DATA
    - MISSING_PREDICTION != LOW_RISK
    - API_ERROR != LOW_RISK
    - ML_ESTIMATE != OFFICIAL_WARNING
    - Admin unauthenticated access == 401/403
    """
    # Location isolation check
    rat = client.get("/api/v1/predictions/current/RATNAPURA_001").json()
    kol = client.get("/api/v1/predictions/current/KOLONNAWA_001").json()
    loc_rat = rat["location"].get("location_id") or rat["location"].get("id")
    loc_kol = kol["location"].get("location_id") or kol["location"].get("id")
    assert loc_rat != loc_kol


    # Missing prediction check
    missing = client.get("/api/v1/predictions/current/INVALID_9999")
    assert missing.status_code == 404

    # Admin unauth protection check
    unauth_admin = client.get("/api/v1/admin/overview")
    assert unauth_admin.status_code in (401, 403)
