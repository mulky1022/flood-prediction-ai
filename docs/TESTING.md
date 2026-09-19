# Quality Engineering & Testing Framework

## Overview
The Sri Lanka FloodWatch project contains automated test suites covering unit tests, API integration tests, location spatial isolation tests, ML pipeline tests, failure injection tests, and master end-to-end system validation suites.

---

## Running Test Suites

### 1. Master E2E Validation Suite (Phase 22)
```bash
pytest -v tests/quality_engineering/test_19_phase22_master_e2e_validation_suite.py
```

### 2. Production Readiness Audit (Phase 9)
```bash
python scripts/verify_production_readiness.py
```

### 3. ML Inference Engine Test
```bash
python scripts/test_prediction.py
```

### 4. FastAPI Endpoint Suite
```bash
python scripts/test_api.py
```

---

## Master Invariants Verified

1. **Master System Location Invariant**:
   `REQUESTED_LOCATION_ID = AUTHORIZED_LOCATION_ID = RETURNED_LOCATION_ID = DISPLAYED_LOCATION_ID`
   - Verified across Predictions, Locations, Details, Emergency Mode, Map, Warnings, and History APIs.

2. **Cross-Location Spatial Isolation**:
   `RATNAPURA_DATA != KOLONNAWA_DATA`
   - Sequential rapid switching (`Ratnapura` -> `Kolonnawa` -> `Ratnapura` -> `Kolonnawa`) produces 0% cross-location data leakage.

3. **Multilingual Preservation Invariant**:
   `LANGUAGE_CHANGE != PREDICTION_CHANGE`
   - Renders localized English, Sinhala, and Tamil strings while preserving identical `prediction_id` and `risk_level`.

4. **Non-Negotiable Safety Principles**:
   - `MISSING_DATA != LOW_RISK`
   - `SERVICE_FAILURE != LOW_RISK`
   - `STALE_DATA != CURRENT_DATA`
