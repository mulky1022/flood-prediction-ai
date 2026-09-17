# PHASE 9 PRODUCTION DEPLOYMENT CHECKLIST

**Project:** Sri Lanka Live Early Flood Risk Prediction & Notification System  
**Phase:** 9 — Deployment & Production Setup  

---

## Production Verification Checklist

### 1. Pre-Deployment Governance & Artifacts
- [x] Phase 8 integration & QA test suites fully passed with zero blockers.
- [x] Machine Learning model `flood_model.pkl` and scaler `preprocessor.pkl` validated on 64 features.
- [x] All 33 monitoring stations validated across 25 administrative districts.
- [x] Live Open-Meteo telemetry and antecedent rainfall aggregations verified with caching.
- [x] Production DDL script ready in `database/schema.sql`.

### 2. Environment & Secrets Security
- [x] `.env` files and cache directories added to `.gitignore` and `.dockerignore`.
- [x] Static frontend scripts audited: Zero API keys, passwords, or Supabase service-role keys in client code.
- [x] CORS middleware restricted to production domain and verified preview patterns.
- [x] Non-root container execution configured in `Dockerfile`.

### 3. Deployment Manifests & Platform Configs
- [x] `vercel.json` configured for clean URL routing, security headers, and static asset caching.
- [x] Production `Dockerfile` with multi-worker Uvicorn and health check endpoint.
- [x] `docker-compose.yml` for unified local/production container orchestration.
- [x] `Procfile` configured for PaaS (Railway / Render / Heroku) deployment.
- [x] Dynamic backend URL resolution implemented in `frontend/js/api.js`.

### 4. Operational Alert & Notification Governance
- [x] Operational risk thresholds calibrated (`CRITICAL` $\ge 80\%$, `HIGH` $\ge 60\%$, `MODERATE` $\ge 35\%$, `LOW` $< 35\%$).
- [x] Duplicate alert prevention and 30-minute cooldown rules enforced.
- [x] Lifecycle state transitions (`ACTIVE` $\to$ `ACKNOWLEDGED` $\to$ `RESOLVED`) validated.
- [x] Automatic alert resolution on risk reduction verified.
- [x] Truthful notification delivery reporting (`SENT` for web broadcast; `NOT_CONFIGURED` for external SMS/Email).

### 5. Multi-Page Stitch UI Verification
- [x] Live Dashboard (`index.html`) tested with live station telemetry and alert banner.
- [x] Flood Monitoring Map (`map.html`) tested with Leaflet markers for all 33 stations.
- [x] Location Details (`district.html`) tested with full hydrological and weather attributes.
- [x] Alerts & Prediction History (`alerts.html`) tested with interactive triage, filters, search, and CSV export.
- [x] Full mobile, tablet, and desktop responsive layout integrity preserved.
