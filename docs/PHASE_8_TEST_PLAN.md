# Sri Lanka Live Early Flood Risk Prediction & Notification System
## Phase 8: Full System Integration, QA, Regression Testing & End-to-End Test Plan

**Document Version:** 1.0.0  
**Phase:** 8 — Full System Integration & Production Readiness  
**Target:** Complete End-to-End Verification across all 7 Subsystems  

---

## 1. System Architecture & Information Flow Under Test

```
USER / OPERATOR
  │
  ▼
[ FRONTEND LAYER ]
  ├── Live Dashboard (index.html)
  ├── Flood Monitoring Map (map.html)
  ├── Location Details (district.html)
  └── Alerts & History (alerts.html)
  │
  ▼ (HTTP / REST API via frontend/js/api.js)
[ FASTAPI BACKEND LAYER ] (api/main.py, api/routes/*)
  ├── /api/v1/health
  ├── /api/v1/locations
  ├── /api/v1/weather/{id}
  ├── /api/v1/predict/{id}
  ├── /api/v1/predictions/{id}
  └── /api/v1/alerts/*
  │
  ▼
[ DATA INGESTION & SYNTHESIS ]
  ├── Static GIS Location Service (data/locations.json, services/location_service.py)
  └── Live Weather Telemetry (weather/weather_processor.py, services/openmeteo_service.py)
  │
  ▼
[ 64-FEATURE PIPELINE ] (services/feature_builder.py)
  ├── Schema Mapping & Categorical Encoders
  └── Quality Assurance & Leakage Baseline Derivations
  │
  ▼
[ MACHINE LEARNING PREDICTOR ] (services/predictor.py)
  ├── StandardScaler (model/preprocessor.pkl)
  └── RandomForestClassifier (model/flood_model.pkl - 500 trees, max_depth=10)
  │
  ▼
[ OPERATIONAL ALERT & NOTIFICATION ENGINE ] (config/alert_config.py, services/alert_service.py)
  ├── Policy Threshold Evaluation (LOW, MODERATE, HIGH, CRITICAL)
  ├── Deduplication & Sentry Lifecycle State Machine
  └── Multi-Channel Dispatcher (services/notification_service.py)
  │
  ▼
[ PERSISTENCE LAYER ] (database/schema.sql, services/supabase_service.py)
  ├── Remote Supabase PostgreSQL (when credentials configured)
  └── High-Fidelity Local In-Memory Fallback Store
```

---

## 2. Test Execution Matrix

### Section A: ML Model & Artifact Regression Tests
| Test ID | Test Name | Purpose | Input / Target | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ML-01** | Artifact Files Existence | Verify existence of all 4 required ML artifacts | `model/` directory | `flood_model.pkl`, `preprocessor.pkl`, `feature_columns.json`, `model_metadata.json` all exist | PASS |
| **ML-02** | Model Deserialization | Ensure model unpickles and verifies architecture | `flood_model.pkl` | `RandomForestClassifier` with 500 estimators, max_depth=10 | PASS |
| **ML-03** | Scaler Deserialization | Verify StandardScaler loads and expects 64 features | `preprocessor.pkl` | `StandardScaler` with `n_features_in_ == 64` | PASS |
| **ML-04** | Feature Columns Contract | Verify feature list integrity and length | `feature_columns.json` | Exact list of 64 columns in strict canonical order | PASS |
| **ML-05** | Predict Proba Output Bounds | Verify inference output probabilities | Scaled feature vector | $P(\text{Flood}) \in [0.0, 1.0]$, $P(\text{Non-Flood}) = 1 - P(\text{Flood})$ | PASS |

---

### Section B: Location Data Tests
| Test ID | Test Name | Purpose | Input / Target | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LOC-01** | Island-wide Station Coverage | Verify station count and district distribution | `data/locations.json` | 33 stations covering all 25 Sri Lankan administrative districts | PASS |
| **LOC-02** | GIS Coordinate Bounds | Validate Sri Lanka bounding box | All 33 coordinates | Lat $\in [5.85, 9.85]^\circ\text{N}$, Lon $\in [79.55, 81.95]^\circ\text{E}$ | PASS |
| **LOC-03** | Hydro-GIS Attributes | Verify topographic and river proximity attributes | Static dataset | `elevation_m`, `distance_to_river_m`, `drainage_index`, `population_density` valid | PASS |
| **LOC-04** | Single Location Resolution | Lookup station by ID and Record ID | ID `7` / `LK-RAT-07` | Ratnapura Town (Kalu Ganga Upper) correctly resolved | PASS |
| **LOC-05** | Missing Location Negative | Query non-existent station ID | ID `99999` | Handled with HTTP 404 / `LOCATION_NOT_FOUND` | PASS |

---

### Section C: Live Weather & Precipitation Telemetry Tests
| Test ID | Test Name | Purpose | Input / Target | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **WEA-01** | Open-Meteo Ingestion | Ingest current atmospheric parameters | Station coordinates | `temperature_c`, `humidity_percent`, `precipitation_mm`, `weather_code` populated | PASS |
| **WEA-02** | Rolling 7-Day Rainfall | Verify 168-hour antecedent rainfall aggregation | Historical hourly API | Cumulative 7d sum calculated correctly | PASS |
| **WEA-03** | Rolling 30-Day Rainfall | Verify monthly antecedent precipitation | Archive daily API | Cumulative 30d sum calculated correctly | PASS |
| **WEA-04** | Cache Expiration & Reuse | Ensure local file/memory cache avoids redundant hits | Repeated station requests | Hits cache when fresh; refreshes when TTL expires | PASS |
| **WEA-05** | Weather Outage Degradation | Verify behavior when Open-Meteo is unreachable | Simulated network timeout | Fails safely with HTTP 422/503; does not fabricate weather data | PASS |

---

### Section D: Feature Builder & Synthesis Pipeline Tests
| Test ID | Test Name | Purpose | Input / Target | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FEAT-01** | 64-Feature Dimensionality | Build feature DataFrame from Location + Weather | Ratnapura (ID 7) | Exactly 1 row, 64 columns matching `feature_columns.json` | PASS |
| **FEAT-02** | Multi-District Isolation | Verify feature isolation between distinct catchments | Colombo (ID 1) vs Kandy (ID 17) | No cross-contamination of static or meteorological features | PASS |
| **FEAT-03** | Categorical One-Hot Encoding | Verify soil, landcover, water presence encoding | Categorical attributes | Matches trained model categories; no missing dummy columns | PASS |
| **FEAT-04** | Data Quality Sentry Gate | Verify gate prevents inference on corrupt inputs | Corrupted feature vector | `ready_for_prediction == False` with audit error report | PASS |

---

### Section E: FastAPI Backend Route Tests
| Test ID | Test Name | Purpose | Input / Target | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **API-01** | Root & Versioned Health | Check service status and model loaded status | `/api/health`, `/api/v1/health` | HTTP 200 `{"status": "ok", "model_loaded": true}` | PASS |
| **API-02** | Locations Listing | Retrieve all stations | `/api/v1/locations` | HTTP 200 with 33 location objects | PASS |
| **API-03** | Weather Endpoint | Retrieve weather and rolling metrics | `/api/v1/weather/7` | HTTP 200 with `current` and `rolling_aggregations` | PASS |
| **API-04** | Prediction Endpoint | Run live ML inference for location | `/api/v1/predict/7` | HTTP 200 with probability, class, model info, data quality | PASS |
| **API-05** | Prediction History | Retrieve historical inference logs | `/api/v1/predictions/7` | HTTP 200 with historical records and pagination | PASS |
| **API-06** | Latest Prediction | Retrieve most recent prediction | `/api/v1/predictions/7/latest` | HTTP 200 with latest inference record | PASS |

---

### Section F: Database & Persistence Layer Tests
| Test ID | Test Name | Purpose | Input / Target | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DB-01** | Connection Status Audit | Test Supabase client status | Environment configuration | Reports remote connection status truthfully (Fallback mode active) | PASS |
| **DB-02** | Schema Integrity | Verify DDL definitions | `database/schema.sql` | `locations`, `weather_observations`, `predictions`, `alerts` defined with indexes | PASS |
| **DB-03** | Prediction Audit Persistence | Save ML inference record | Prediction result | Successfully persisted to local store / Supabase | PASS |
| **DB-04** | Alert Record Persistence | Save operational alert record | Alert payload | Successfully persisted and queryable by status and location | PASS |
| **DB-05** | Persistence State Reporting | Verify truthful reporting across restart | Process restart | Report `DATABASE PERSISTENCE: BLOCKED (Remote unconfigured; Local fallback active)` | PASS |

---

### Section G: Alert Engine & Policy Tests
| Test ID | Test Name | Purpose | Input / Target | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ALT-01** | Low Risk Evaluation | Test $P < 0.35$ baseline | $P = 0.15$ | `NO_ALERT_REQUIRED` (No active alert created) | PASS |
| **ALT-02** | Moderate Risk Evaluation | Test $0.35 \le P < 0.60$ advisory | $P = 0.45$ | `NO_ALERT_REQUIRED` (Advisory monitoring maintained) | PASS |
| **ALT-03** | High Risk Generation | Test $0.60 \le P < 0.80$ alert trigger | $P = 0.72$ | `ALERT_CREATED` (`status = ACTIVE`, `risk_level = HIGH`) | PASS |
| **ALT-04** | Critical Risk Generation | Test $P \ge 0.80$ emergency trigger | $P = 0.88$ | `ALERT_CREATED` (`status = ACTIVE`, `risk_level = CRITICAL`) | PASS |
| **ALT-05** | Duplicate Alert Prevention | Repeated high risk prediction calls | Multiple cycles for same station | `ALERT_UPDATED` (Single active alert updated; no duplicate spawned) | PASS |
| **ALT-06** | Auto-Resolution on Decrease | Risk transition HIGH $\rightarrow$ LOW | $P = 0.75 \rightarrow P = 0.20$ | `ALERT_RESOLVED` (`status = RESOLVED`, `resolved_at` populated) | PASS |
| **ALT-07** | Manual Acknowledgment | Acknowledge active alert | `POST /alerts/{id}/acknowledge` | Status transitions to `ACKNOWLEDGED` | PASS |
| **ALT-08** | Manual Resolution | Resolve alert | `POST /alerts/{id}/resolve` | Status transitions to `RESOLVED` | PASS |

---

### Section H: Notification Dispatcher Tests
| Test ID | Test Name | Purpose | Input / Target | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NOT-01** | Web/Dashboard Channel | In-app telemetry dispatch | Alert trigger | `web_dashboard.status = SENT` (Immediate broadcast) | PASS |
| **NOT-02** | Email Provider Success | Mock SMTP dispatch | Valid SMTP config | `email.status = SENT`, `overall_status = SENT` | PASS |
| **NOT-03** | Email Provider Failure | Handle SMTP server unreachable | Connection error | `email.status = FAILED`, `overall_status = FAILED` | PASS |
| **NOT-04** | Unconfigured Provider | Default environment without credentials | Empty env | Truthfully reported as `NOT_CONFIGURED` / `NOT_REQUIRED` | PASS |

---

### Section I: Frontend Stitch-Based UI Integration Tests
| Test ID | Test Name | Purpose | Target Page | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UI-01** | Live Dashboard Page | Station selector, SVG gauge, weather cards | `frontend/index.html` | Real API data bound; gauge reflects exact $P(\text{Flood})$ | PASS |
| **UI-02** | Flood Monitoring Map | Geo-spatial station markers & risk badges | `frontend/map.html` | Markers plotted from real coordinates; risk colors match backend | PASS |
| **UI-03** | Location Details Page | Catchment telemetry, vulnerability matrix | `frontend/district.html` | Elevation, river proximity, rainfall analytics, active alert badge | PASS |
| **UI-04** | Alerts & History Page | Active alert stream, filter toolbar, table | `frontend/alerts.html` | Displays real active alerts with interactive Ack/Resolve actions | PASS |
| **UI-05** | Header Active Alert Badge | Live alert count indicator in navigation | `frontend/js/common.js` | Displays real active alert count with pulse indicator | PASS |

---

### Section J: Cross-Page Consistency Tests
| Test ID | Test Name | Purpose | Sample Location | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CPC-01** | Station Identity Consistency | Validate Name, District, Coordinates across pages | Ratnapura (ID 7) | Identical place name, district, and coordinates on all 4 pages | PASS |
| **CPC-02** | Metric & Risk Consistency | Validate Probability and Risk Badge across pages | Kolonnawa (ID 1) | Same $P(\text{Flood})$ and Risk Tier displayed across Dashboard, Map, Details, Alerts | PASS |

---

### Section K: Failure & Resilience Tests
| Test ID | Test Name | Purpose | Scenario | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FAIL-01** | Open-Meteo Outage | External API unavailable | 503 from weather provider | Returns clear degraded error; no fabricated data | PASS |
| **FAIL-02** | Database Disconnection | Supabase unreachable | No remote database | Local in-memory fallback operates cleanly without crashing | PASS |
| **FAIL-03** | Invalid Alert ID | Access non-existent alert | `/api/v1/alerts/999999` | HTTP 404 `ALERT_NOT_FOUND` | PASS |
| **FAIL-04** | Invalid Location ID | Access non-existent station | `/api/v1/locations/999999` | HTTP 404 `LOCATION_NOT_FOUND` | PASS |

---

### Section L: Security & Configuration Tests
| Test ID | Test Name | Purpose | Target | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | Secret Leakage Prevention | Ensure no API keys in frontend JS/HTML | `frontend/js/*.js` | Zero database passwords, service-role keys, or SMTP secrets exposed | PASS |
| **SEC-02** | CORS Configuration | Verify CORS headers allow configured origin | `api/main.py` | Allows specified frontend origins; blocks unauthorized origins | PASS |

---

### Section M: Performance & Scheduled Processing Tests
| Test ID | Test Name | Purpose | Target | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PERF-01** | Island-wide Batch Processing | Evaluate all 33 stations in single cycle | `scripts/process_alerts_cron.py --once` | Evaluates all 33 stations; deduplicates active alerts cleanly | PASS |
| **PERF-02** | Weather Ingestion Caching | Avoid rate-limiting on Open-Meteo | `weather/weather_processor.py` | In-memory and file caching reuse fresh weather forecasts | PASS |

---

### Section N: End-to-End Workflow Verification
| Test ID | Test Name | Purpose | Target Station | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **E2E-01** | Complete End-to-End Flow | Full lifecycle trace from location to UI | Kolonnawa (ID 1) / Ratnapura (ID 7) | Prediction $\rightarrow$ Alert $\rightarrow$ Database $\rightarrow$ API $\rightarrow$ Frontend UI verified | PASS |

---

### Section O: Regression Verification (Phases 1–7)
| Test ID | Phase Verified | Test Script | Target System | Result |
| :--- | :--- | :--- | :--- | :--- |
| **REG-01** | Phase 1 (ML Validation) | `scripts/test_model.py` | Model & Scaler Artifacts | PASS |
| **REG-02** | Phase 2 (Static Locations) | `scripts/test_locations.py` | 33 Location GIS Dataset | PASS |
| **REG-03** | Phase 3 (Weather Ingestion) | `scripts/test_weather_processing.py` | Open-Meteo Live Ingestion | PASS |
| **REG-04** | Phase 4 (ML Inference) | `scripts/test_inference.py` | 64-Feature Predictor | PASS |
| **REG-05** | Phase 5 (FastAPI & Supabase) | `scripts/test_api.py`, `scripts/test_prediction_api.py` | Backend API Routes | PASS |
| **REG-06** | Phase 6 (Stitch Frontend) | Frontend Verification | 4 Web Pages | PASS |
| **REG-07** | Phase 7 (Alerts & Notifications) | `scripts/test_alerts.py`, `tests/` | Alert Engine & Lifecycle | PASS |
