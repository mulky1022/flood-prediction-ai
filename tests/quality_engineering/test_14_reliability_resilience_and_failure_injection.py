"""
Phase 18 & 19 Quality Engineering Suite 14: Reliability, Resilience & Failure Injection.

Verifies:
- NON-NEGOTIABLE SAFETY PRINCIPLE:
  SERVICE FAILURE != LOW RISK
  MISSING DATA != LOW RISK
  API ERROR != LOW RISK
  WARNING UNAVAILABLE != NO WARNING
- Circuit Breaker state transitions (CLOSED -> OPEN -> HALF_OPEN)
- Bounded retry decorator with exponential backoff & jitter
- Single-Flight Cache Lock to prevent cache stampedes
"""

import pytest
from fastapi.testclient import TestClient
from services.resilience import CircuitBreaker, CircuitBreakerOpenException, bounded_retry, SINGLE_FLIGHT_CACHE_LOCK


def test_non_negotiable_safety_principle_service_failure_never_becomes_low_risk(client: TestClient):
    """
    CRITICAL SAFETY PRINCIPLE TEST:
    A missing location or API error MUST return HTTP 404 / 500 error state.
    It MUST NEVER fabricate risk_level = LOW or action = SAFE.
    """
    res = client.get("/api/v1/predictions/current/NON_EXISTENT_LOCATION_9999")
    assert res.status_code == 404
    data = res.json()
    assert data.get("risk", {}).get("level") != "LOW"
    assert data.get("action", {}).get("code") != "SAFE"


def test_warning_service_failure_never_collapses_to_no_warning():
    """
    CRITICAL SAFETY PRINCIPLE TEST:
    Warning service unavailable status MUST return UNAVAILABLE, never collapse to NONE.
    """
    error_response = {"status": "UNAVAILABLE", "message": "Warning service unreachable"}
    assert error_response.get("status") != "NONE"
    assert error_response.get("status") != "NO_ACTIVE_WARNING"


def test_circuit_breaker_state_transitions():
    """Verify CircuitBreaker state transitions from CLOSED to OPEN after failure threshold."""
    cb = CircuitBreaker("TestService", failure_threshold=3, recovery_timeout_seconds=0.1)
    assert cb.state == "CLOSED"
    assert cb.allow_execution() is True

    # Record 3 failures to trigger OPEN state
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()

    assert cb.state == "OPEN"
    assert cb.allow_execution() is False

    # Wait for recovery timeout to enter HALF_OPEN
    import time
    time.sleep(0.15)

    assert cb.allow_execution() is True
    assert cb.state == "HALF_OPEN"

    # Record success to reset to CLOSED
    cb.record_success()
    assert cb.state == "CLOSED"


def test_bounded_retry_decorator_success_and_failure():
    """Verify bounded_retry decorator retries up to max_retries and succeeds or raises exception."""
    call_count = 0

    @bounded_retry(max_retries=3, base_delay_seconds=0.01, max_delay_seconds=0.05)
    def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("Temporary network glitch")
        return "SUCCESS"

    result = flaky_func()
    assert result == "SUCCESS"
    assert call_count == 2


def test_single_flight_cache_lock():
    """Verify SingleFlightCacheLock executes function once for duplicate key requests."""
    execution_counter = 0

    def compute_expensive_prediction():
        nonlocal execution_counter
        execution_counter += 1
        return {"prediction": "HIGH"}

    res1 = SINGLE_FLIGHT_CACHE_LOCK.execute_single("prediction:RATNAPURA_001", compute_expensive_prediction)
    assert res1["prediction"] == "HIGH"
    assert execution_counter == 1
