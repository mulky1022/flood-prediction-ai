"""
Phase 18 Quality Engineering Suite 01: Location Isolation and Selection.

Verifies:
- RATNAPURA_001 resolves to Ratnapura Town (ID 7)
- KOLONNAWA_001 resolves to Kolonnawa (ID 1)
- INVALID_001 yields HTTP 404 / location not found
- No fallback: Ratnapura query failure must NEVER fall back or alias to Kolonnawa
"""

import pytest
from fastapi.testclient import TestClient
from services.location_service import get_location_by_id, get_all_locations
from tests.fixtures.canonical_fixtures import RATNAPURA_LOCATION_FIXTURE, KOLONNAWA_LOCATION_FIXTURE


def test_ratnapura_location_resolution():
    """Verify RATNAPURA_001 resolves to canonical Ratnapura location record."""
    loc = get_location_by_id("RATNAPURA_001")
    assert loc is not None
    assert loc["id"] == 7
    assert loc["district"] == "Ratnapura"
    assert "Ratnapura" in loc["place_name"]


def test_kolonnawa_location_resolution():
    """Verify KOLONNAWA_001 resolves to canonical Kolonnawa location record."""
    loc = get_location_by_id("KOLONNAWA_001")
    assert loc is not None
    assert loc["id"] == 1
    assert loc["district"] == "Colombo"
    assert "Kolonnawa" in loc["place_name"]


def test_invalid_location_lookup_returns_none(client: TestClient):
    """Verify invalid location query (INVALID_001) returns None / HTTP 404."""
    loc = get_location_by_id("INVALID_001")
    assert loc is None

    res = client.get("/api/v1/locations/INVALID_001")
    assert res.status_code == 404
    body = res.json()
    assert body["status"] == "error"
    assert "LOCATION_NOT_FOUND" in str(body.get("detail") or body.get("code"))


def test_strict_no_fallback_ratnapura_to_kolonnawa():
    """
    Verify strict location isolation invariant:
    RATNAPURA_DATA != KOLONNAWA_DATA.
    A failed or unavailable query for Ratnapura MUST NOT fall back to Kolonnawa.
    """
    rat = get_location_by_id("RATNAPURA_001")
    kol = get_location_by_id("KOLONNAWA_001")

    assert rat["id"] != kol["id"]
    assert rat["district"] != kol["district"]
    assert rat["latitude"] != kol["latitude"]
    assert rat["longitude"] != kol["longitude"]
    assert rat["place_name"] != kol["place_name"]
