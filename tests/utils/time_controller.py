"""
Deterministic Time Controller Utility for Phase 18 Quality Engineering.

Provides timezone-aware (Asia/Colombo / UTC) timestamp generation, boundary testing helpers,
and stale/expired validity window calculations.
"""

from datetime import datetime, timezone, timedelta
from typing import Tuple


def get_current_utc_iso() -> str:
    """Returns current UTC ISO timestamp string."""
    return datetime.now(timezone.utc).isoformat()


def get_colombo_time() -> datetime:
    """Returns current datetime in Asia/Colombo timezone (+05:30)."""
    colombo_tz = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(colombo_tz)


def get_validity_window(hours_valid: int = 12) -> Tuple[str, str]:
    """
    Generates a valid_from and valid_until timestamp tuple for a given validity duration.
    """
    now = datetime.now(timezone.utc)
    until = now + timedelta(hours=hours_valid)
    return now.isoformat(), until.isoformat()


def get_expired_validity_window(hours_ago: int = 24) -> Tuple[str, str]:
    """
    Generates an expired valid_from and valid_until timestamp tuple.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours_ago)
    until = start + timedelta(hours=6)
    return start.isoformat(), until.isoformat()


def is_timestamp_stale(valid_until_iso: str) -> bool:
    """
    Checks if a valid_until ISO timestamp string is in the past.
    """
    if not valid_until_iso:
        return True
    try:
        dt = datetime.fromisoformat(valid_until_iso.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > dt
    except Exception:
        return True
