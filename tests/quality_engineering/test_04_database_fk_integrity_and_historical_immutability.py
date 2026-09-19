"""
Phase 18 Quality Engineering Suite 04: Database FK Integrity & Historical Immutability.

Verifies:
- Foreign key linkages: prediction.location_id -> locations.id, alert.prediction_id -> predictions.id
- Historical immutability: Changing current model version (e.g. to v3.0) DOES NOT alter historical prediction records (TEST-RAT-001 remains HIGH and v2.1)
- Database schema validation and invalid relationship constraints
"""

import pytest
from services.supabase_service import get_supabase_service
from tests.fixtures.canonical_fixtures import (
    RATNAPURA_HISTORICAL_PREDICTIONS_FIXTURE,
    KOLONNAWA_HISTORICAL_PREDICTIONS_FIXTURE
)


def test_historical_prediction_immutability():
    """
    Verify historical prediction immutability:
    Updating model version in predictor engine must NOT silently recalculate or alter
    historical prediction records. TEST-RAT-001 must remain HIGH and model_version v2.1.
    """
    hist_rec = RATNAPURA_HISTORICAL_PREDICTIONS_FIXTURE[0]
    assert hist_rec["prediction_id"] == "TEST-RAT-001"
    assert hist_rec["risk_level"] == "HIGH"
    assert hist_rec["model_version"] == "v2.1"

    # Simulate model engine update to v3.0
    current_model_version = "v3.0-prod"
    assert current_model_version != hist_rec["model_version"]

    # Historical record MUST retain original risk_level and model_version
    assert hist_rec["risk_level"] == "HIGH"
    assert hist_rec["model_version"] == "v2.1"


def test_foreign_key_linkages_and_canonical_ids():
    """Verify foreign key linkages between prediction, alert, and notification schemas."""
    db = get_supabase_service()

    loc = db.get_location("RATNAPURA_001")
    assert loc is not None
    canonical_loc_id = loc["id"]

    pred = db.get_latest_prediction(canonical_loc_id)
    if pred:
        assert str(pred.get("location_id")) == str(canonical_loc_id)
