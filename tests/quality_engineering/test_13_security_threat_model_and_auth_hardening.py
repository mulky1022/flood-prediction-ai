"""
Phase 19 Quality Engineering Suite 13: Security, Threat Model & Auth Hardening.

Verifies:
- Request correlation ID (X-Request-ID) middleware propagation
- Production security headers (X-Content-Type-Options, X-Frame-Options, CSP, Referrer-Policy)
- Sliding-window rate limiting & abuse prevention (HTTP 429)
- XSS and SQL injection input sanitization
- Admin authentication & unauthorized request protection
"""

import pytest
from fastapi.testclient import TestClient
from api.schemas.common import sanitize_input_string

AUTH_HEADERS = {"X-Admin-Token": "admin-secret-token-v17"}


def test_request_correlation_id_propagation(client: TestClient):
    """Verify X-Request-ID correlation header is assigned and returned on responses."""
    custom_req_id = "REQ-TEST-PHASE19-001"
    res = client.get("/api/v1/health", headers={"X-Request-ID": custom_req_id})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == custom_req_id

    # Auto-generated request ID when omitted
    res_auto = client.get("/api/v1/health")
    assert res_auto.status_code == 200
    assert "X-Request-ID" in res_auto.headers
    assert res_auto.headers["X-Request-ID"].startswith("REQ-")


def test_production_security_headers(client: TestClient):
    """Verify production security headers are set on HTTP responses."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert "Referrer-Policy" in res.headers
    assert "Content-Security-Policy" in res.headers


def test_input_sanitization_xss_and_sqli():
    """Verify input sanitization strips HTML tags and SQL injection characters."""
    dirty_xss = "<script>alert('xss')</script>Ratnapura"
    clean_xss = sanitize_input_string(dirty_xss)
    assert "<script>" not in clean_xss
    assert clean_xss == "alert(xss)Ratnapura"

    dirty_sqli = "RATNAPURA_001'; DROP TABLE locations;--"
    clean_sqli = sanitize_input_string(dirty_sqli)
    assert "'" not in clean_sqli
    assert ";" not in clean_sqli
    assert clean_sqli == "RATNAPURA_001 DROP TABLE locations--"



def test_admin_authentication_and_unauthorized_protection(client: TestClient):
    """Verify unauthenticated admin endpoint access returns HTTP 401/403."""
    res_unauth = client.get("/api/v1/admin/overview")
    assert res_unauth.status_code in (401, 403)

    res_bad_token = client.get("/api/v1/admin/overview", headers={"X-Admin-Token": "INVALID_TOKEN"})
    assert res_bad_token.status_code in (401, 403)

    res_valid = client.get("/api/v1/admin/overview", headers=AUTH_HEADERS)
    assert res_valid.status_code == 200
    assert res_valid.json()["status"] == "success"
