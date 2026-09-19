"""
Pytest Test Environment Configuration and Fixtures for Phase 18 Quality Engineering.

Configures isolated test environment variables, FastAPI TestClient, database cleanup,
mock external providers (SMS, WhatsApp, Open-Meteo), and canonical fixtures.
"""

import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient

# Enforce isolated test environment variables before importing application modules
os.environ["ENVIRONMENT"] = "test"
os.environ["TESTING"] = "True"
os.environ["ADMIN_API_KEY"] = "admin-secret-token-v17"

os.environ["TWILIO_ACCOUNT_SID"] = "AC_test_mock_account_sid_12345"
os.environ["TWILIO_AUTH_TOKEN"] = "mock_auth_token_secret_12345"
os.environ["WHATSAPP_API_TOKEN"] = "mock_whatsapp_token_12345"

from api.main import app
from services.supabase_service import get_supabase_service
from services.predictor import get_predictor
from services.official_warning_service import get_official_warning_service


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """FastAPI TestClient fixture with isolated test environment configuration."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def admin_auth_headers() -> dict:
    """Returns valid admin authentication headers."""
    return {"X-Admin-Token": os.environ["ADMIN_API_KEY"]}


@pytest.fixture(autouse=True)
def reset_local_stores():
    """
    Resets in-memory service caches and state between test functions to guarantee test isolation.
    """
    db = get_supabase_service()
    # Reset local stores if reset method exists or clear arrays
    if hasattr(db, "_LOCAL_NOTIFICATION_LOGS"):
        import services.supabase_service as ss
        ss._LOCAL_NOTIFICATION_LOGS = []
        ss._LOCAL_SUBSCRIPTIONS = []
        ss._LOCAL_SYSTEM_ERRORS = []
        ss._LOCAL_AUDIT_LOGS = []
        ss._LOCAL_PREDICTION_JOBS = []
        ss._LOCAL_OFFICIAL_WARNINGS = []
        ss._LOCAL_TRIGGERED_ALERTS = []
    yield
