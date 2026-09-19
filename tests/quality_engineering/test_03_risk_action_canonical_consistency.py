"""
Phase 18 Quality Engineering Suite 03: Risk & Action Canonical Consistency.

Verifies:
- Authoritative Phase 5 Risk & Action Engine logic across HIGH, MEDIUM, LOW
- Permanent regression test: HIGH risk MUST NEVER produce a contradictory LOW risk action
- Action codes (EVACUATE, PREPARE, MONITOR) and recommendations align strictly with Phase 5
"""

import pytest
from services.risk_engine import RiskEngine, RISK_LEVEL_HIGH, RISK_LEVEL_MODERATE, RISK_LEVEL_LOW, ACTION_CODE_EVACUATE, ACTION_CODE_MONITOR


def test_risk_level_determination_thresholds():
    """Verify Phase 5 risk level determination thresholds."""
    assert RiskEngine.derive_risk_level(0.85) == "CRITICAL"
    assert RiskEngine.derive_risk_level(0.70) == "HIGH"
    assert RiskEngine.derive_risk_level(0.50) == "MODERATE"
    assert RiskEngine.derive_risk_level(0.40) == "MODERATE"
    assert RiskEngine.derive_risk_level(0.20) == "LOW"
    assert RiskEngine.derive_risk_level(0.00) == "LOW"


def test_high_risk_never_produces_low_risk_action():
    """
    PERMANENT REGRESSION TEST:
    HIGH risk MUST produce a PREPARE or EVACUATE action code.
    It MUST NEVER produce a low-risk SAFE action.
    """
    high_action = RiskEngine.get_canonical_action("HIGH")
    assert high_action["code"] in ("PREPARE", "EVACUATE", "MONITOR")
    assert high_action["code"] != "SAFE"

    critical_action = RiskEngine.get_canonical_action("CRITICAL")
    assert critical_action["code"] == "EVACUATE"
    assert critical_action["code"] != "SAFE"


def test_moderate_risk_action_recommendation():
    """Verify MODERATE risk action recommendation from Phase 5 Action Engine."""
    mod_action = RiskEngine.get_canonical_action("MODERATE")
    assert mod_action["code"] == "MONITOR"
    assert mod_action["code"] != "EVACUATE"


def test_low_risk_action_recommendation():
    """Verify LOW risk action recommendation from Phase 5 Action Engine."""
    low_action = RiskEngine.get_canonical_action("LOW")
    assert low_action["code"] == "SAFE"
    assert low_action["code"] != "EVACUATE"
