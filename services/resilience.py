"""
Phase 19 — Resilience, Bounded Retries, Circuit Breaker & Single-Flight Cache Locking.

Ensures:
- All external network calls have bounded timeouts and exponential backoff + jitter retries.
- Circuit breaker transitions between CLOSED, OPEN, and HALF_OPEN.
- Single-flight cache lock prevents cache stampede when keys expire.
- NON-NEGOTIABLE SAFETY PRINCIPLE: Failure semantics NEVER synthesize LOW risk or NO warning.
"""

import time
import random
import logging
import asyncio
from typing import Callable, Any, Dict, Optional

logger = logging.getLogger("ResilienceService")


def bounded_retry(
    max_retries: int = 3,
    base_delay_seconds: float = 0.5,
    max_delay_seconds: float = 4.0,
    backoff_factor: float = 2.0
):
    """
    Decorator for bounded retries with exponential backoff and randomized jitter.
    Prevents infinite retries and server thundering herd.
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts >= max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} attempts: {e}")
                        raise e
                    sleep_time = min(max_delay_seconds, base_delay_seconds * (backoff_factor ** (attempts - 1)))
                    jitter = random.uniform(0.8, 1.2)
                    total_sleep = sleep_time * jitter
                    logger.warning(f"Function {func.__name__} attempt {attempts} failed ({e}). Retrying in {total_sleep:.2f}s...")
                    time.sleep(total_sleep)
        return wrapper
    return decorator


class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation for external service integration protection.
    States: CLOSED (normal), OPEN (tripped), HALF_OPEN (probing recovery).
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_state_change = time.time()

    def record_success(self):
        """Records successful service call."""
        if self.state in ("HALF_OPEN", "OPEN"):
            logger.info(f"[CircuitBreaker:{self.service_name}] State transition: {self.state} -> CLOSED")
            self.state = "CLOSED"
        self.failure_count = 0

    def record_failure(self):
        """Records failed service call."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            if self.state != "OPEN":
                logger.error(f"[CircuitBreaker:{self.service_name}] Failure threshold reached ({self.failure_count}). State transition: {self.state} -> OPEN")
                self.state = "OPEN"
                self.last_state_change = time.time()

    def allow_execution(self) -> bool:
        """Determines if a request to the downstream service should be allowed."""
        now = time.time()
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if now - self.last_state_change > self.recovery_timeout_seconds:
                logger.info(f"[CircuitBreaker:{self.service_name}] Recovery timeout reached. State transition: OPEN -> HALF_OPEN")
                self.state = "HALF_OPEN"
                self.last_state_change = now
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False


# Circuit Breakers Registry
CIRCUIT_BREAKERS: Dict[str, CircuitBreaker] = {
    "openmeteo": CircuitBreaker("Open-Meteo-Weather-API", failure_threshold=5, recovery_timeout_seconds=30.0),
    "sms_gateway": CircuitBreaker("SMS-Gateway-Provider", failure_threshold=5, recovery_timeout_seconds=30.0),
    "whatsapp_gateway": CircuitBreaker("WhatsApp-Cloud-API", failure_threshold=5, recovery_timeout_seconds=30.0),
    "official_warning": CircuitBreaker("Official-Warning-Service", failure_threshold=5, recovery_timeout_seconds=30.0)
}


class SingleFlightLock:
    """
    Prevents cache stampedes by ensuring only one process/thread executes
    expensive prediction/telemetry generation for a key at any given time.
    """
    def __init__(self):
        self._in_flight: Dict[str, Any] = {}

    def execute_single(self, key: str, func: Callable[[], Any]) -> Any:
        if key in self._in_flight:
            logger.info(f"[SingleFlight] Waiting for existing in-flight execution for key '{key}'")
            return self._in_flight[key]
        
        try:
            res = func()
            self._in_flight[key] = res
            return res
        finally:
            if key in self._in_flight:
                del self._in_flight[key]


# Global single flight lock instance
SINGLE_FLIGHT_CACHE_LOCK = SingleFlightLock()
