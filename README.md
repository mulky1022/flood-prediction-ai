# Sri Lanka Live Early Flood Risk Prediction & Notification System
### Young Computer Scientist (YCS) Competition Submission Entry

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-FastAPI-green)](https://fastapi.tiangolo.com/)
[![ML Model](https://img.shields.io/badge/ML%20Model-RandomForest%20v1.0.0-orange)](model/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)

---

## 🏆 Project Overview

Sri Lanka faces frequent monsoonal riverine flooding across major river basins including Kalu Ganga, Kelani River, Gin Ganga, and Nilwala Ganga.

This project delivers an end-to-end, machine-learning-powered early flood risk prediction and notification application specifically engineered for Sri Lanka's 25 administrative districts across 33 hydrological monitoring stations.

---

## ⚡ Quick Local Demo Instructions (For Judges)

You can launch the complete application on your local machine (`http://127.0.0.1:8000/`) with a single command:

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12 installed.

### 2. Launch Local Website & API
```bash
# Clone the repository
git clone https://github.com/mulky1022/flood-prediction-ai.git
cd "flood prediction"

# Install dependencies
pip install -r requirements.txt

# Run local launcher script (Boots FastAPI server & opens website in browser)
python scripts/run_local.py
```

- **Local Website**: `http://127.0.0.1:8000/`
- **Interactive Map**: `http://127.0.0.1:8000/map.html`
- **District Analytics**: `http://127.0.0.1:8000/district.html`
- **Active Alerts**: `http://127.0.0.1:8000/alerts.html`
- **Swagger API Docs**: `http://127.0.0.1:8000/docs`

---

## 🏗️ System Architecture

```text
       [ DATA TELEMETRY SOURCES ]
  Open-Meteo Live & Archive Weather API
                  │
                  ▼
       [ DATA VALIDATION LAYER ]
  Quality Checks, Range & Freshness Validation
                  │
                  ▼
      [ LOCATION / SPATIAL REGISTRY ]
    33 Monitoring Stations / 25 Districts
                  │
                  ▼
      [ FEATURE ENGINEERING PIPELINE ]
  64 Contract Features (32 Telemetry + 32 GIS)
                  │
                  ▼
         [ ML MODEL INFERENCE ]
  RandomForestClassifier v1.0.0 & StandardScaler
                  │
                  ▼
     [ CANONICAL RISK & ACTION ENGINE ]
    Risk Levels (LOW, MODERATE, HIGH, CRITICAL)
                  │
                  ▼
    [ DATABASE PERSISTENCE LAYER ]
  Supabase PostgreSQL + In-Memory Resilient Store
                  │
                  ▼
       [ UNIFIED PREDICTION API ]
  FastAPI Endpoints (/api/v1/health, /predictions, etc.)
                  │
                  ▼
     [ PUBLIC WEB APPLICATION ]
  Dashboard | Map | Alerts | History | Emergency Mode (117)
```

---

## 🤖 Machine Learning Model & Performance

- **Algorithm**: `RandomForestClassifier` (100 Estimators)
- **Feature Contract**: Exact 64 features (32 weather/temporal telemetry + 32 GIS/hydrography baselines)
- **Scaler**: `StandardScaler` (64 dimensions)
- **Accuracy**: **92.63%**
- **ROC-AUC Score**: **0.9632**

---

## 🛡️ Core Safety Invariants

1. **Location Isolation**: `RATNAPURA_DATA != KOLONNAWA_DATA` (Zero cross-location bleed).
2. **Master Location Invariant**: `REQUESTED_LOCATION_ID = AUTHORIZED_LOCATION_ID = RETURNED_LOCATION_ID = DISPLAYED_LOCATION_ID`.
3. **Multilingual Preservation**: Changing UI language (English, Sinhala, Tamil) preserves identical prediction data (`LANGUAGE_CHANGE != PREDICTION_CHANGE`).
4. **Safety Principles**: `MISSING_DATA != LOW_RISK` and `SERVICE_FAILURE != LOW_RISK`.
5. **Government Warning Distinction**: Clear visual separation between **ML Flood-Risk Probability Estimates** and **Official Government Warnings (DMC / Irrigation Dept)**.

---

## 📚 Competition Documentation Sitemap

Detailed documentation is available in the `docs/` directory:

- 📄 [`docs/project_overview.md`](docs/project_overview.md): Problem statement, motivation, and objectives.
- 📄 [`docs/system_architecture.md`](docs/system_architecture.md): Complete dataflow, component diagram, and invariants.
- 📄 [`docs/database_design.md`](docs/database_design.md): PostgreSQL schema DDL, indexes, and resilient fallback store.
- 📄 [`docs/ml_methodology.md`](docs/ml_methodology.md): 64-feature vector contract, RandomForest model, and evaluation metrics.
- 📄 [`docs/api_documentation.md`](docs/api_documentation.md): OpenAPI / FastAPI REST endpoints, schemas, and error codes.
- 📄 [`docs/testing.md`](docs/testing.md): Quality engineering test suites, invariant tests, and execution commands.
- 📄 [`docs/security.md`](docs/security.md): Zero secrets policy, CORS security, rate limiting, and privacy.
- 📄 [`docs/limitations.md`](docs/limitations.md): Technical limitations, hydrological assumptions, and future roadmap.
- 📄 [`docs/YCS_COMPETITION_AUDIT_REPORT.md`](docs/YCS_COMPETITION_AUDIT_REPORT.md): Official Competition Audit & Submission Report.

---

## 🧪 Running Automated Tests

```bash
# Master End-to-End System Validation Suite (Phase 22)
pytest -v tests/quality_engineering/test_19_phase22_master_e2e_validation_suite.py

# Production Readiness Audit (Phase 9)
python scripts/verify_production_readiness.py

# ML Model Pipeline Test
python scripts/test_prediction.py
```

---

## 🌐 Live Production Deployment
- **Public Website**: [https://flood-prediction-roan.vercel.app](https://flood-prediction-roan.vercel.app)
- **API Health**: [https://flood-prediction-roan.vercel.app/api/v1/health](https://flood-prediction-roan.vercel.app/api/v1/health)

---

## ⚖️ License & Disclaimer
This project is licensed under the MIT License. The ML flood probability predictions generated by this software are statistical estimates for decision-support purposes and must not replace official emergency evacuation directives issued by the Disaster Management Centre (DMC) or Irrigation Department of Sri Lanka.
