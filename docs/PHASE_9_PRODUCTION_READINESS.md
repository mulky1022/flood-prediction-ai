# PHASE 9 PRODUCTION READINESS & DEPLOYMENT ARCHITECTURE

**Project:** Sri Lanka Live Early Flood Risk Prediction & Notification System  
**Phase:** 9 — Deployment & Production Setup  
**Date:** 2026-09-17  
**Status:** READY FOR PRODUCTION PROVISIONING  

---

## 1. System Architecture & Topology

The production architecture decouples the static Google Stitch frontend from the FastAPI machine learning backend and external dependencies:

```
                            ┌────────────────────────┐
                            │       CITIZENS &       │
                            │   EMERGENCY OPERATORS  │
                            └───────────┬────────────┘
                                        │ HTTPS
                                        ▼
             ┌──────────────────────────────────────────────────────┐
             │            VERCEL STATIC FRONTEND HOSTING            │
             │  - Live Dashboard (index.html)                       │
             │  - Flood Monitoring Map (map.html)                   │
             │  - Location Details (district.html)                  │
             │  - Alerts & History (alerts.html)                    │
             │  - Static Assets (css/, js/) via Edge CDN            │
             └──────────────────────────┬───────────────────────────┘
                                        │ HTTPS REST / JSON
                                        ▼
             ┌──────────────────────────────────────────────────────┐
             │        PRODUCTION FASTAPI BACKEND (DOCKER / CLOUD)   │
             │  - Health, Telemetry, and Spatial APIs               │
             │  - 64-Feature ML Pipeline (RandomForestClassifier)   │
             │  - Operational Alert Policy & Cooldown Deduplication │
             │  - Notification Dispatcher (Web / Email / SMS)       │
             └───────────┬──────────────────────────────┬───────────┘
                         │                              │
                         ▼                              ▼
             ┌────────────────────────┐    ┌────────────────────────┐
             │       OPEN-METEO       │    │   SUPABASE POSTGRESQL  │
             │  - Live Meteorological │    │  - Locations Table     │
             │    Telemetry & Forecast│    │  - Weather History     │
             │  - 7d/30d Precipitation│    │  - Predictions Table   │
             │    Aggregation Engine  │    │  - Alerts & Audits     │
             └────────────────────────┘    └────────────────────────┘
```

---

## 2. Selected Hosting Platforms

| Tier | Selected Platform | Rationale |
|---|---|---|
| **Frontend** | **Vercel** | High-performance Global Edge CDN, automated HTTPS, zero cold-start latency for static Stitch HTML/CSS/JS assets, native `vercel.json` routing and headers. |
| **Backend** | **Dockerized Cloud Container (Cloud Run / Railway / Render)** | Full support for Python 3.11, Scikit-Learn 1.6+, native multi-worker Uvicorn execution, automated HTTPS, environment variable secret management, container health checks. |
| **Database** | **Supabase (Managed PostgreSQL)** | Managed ACID persistence, low latency, connection pooling, Row Level Security (RLS) support, automated backups, and DDL compatibility via `database/schema.sql`. |
| **Telemetry** | **Open-Meteo REST APIs** | Reliable high-resolution meteorological forecast & archive data with zero API key requirement and built-in server-side TTL caching. |

---

## 3. Production Environment Variables & Secrets

All secrets and credentials remain strictly on the backend server. The frontend never accesses privileged keys:

| Variable Name | Required / Optional | Scope | Description |
|---|---|---|---|
| `ENVIRONMENT` | Required | Backend | `production` or `staging` |
| `FRONTEND_ORIGIN` | Required | Backend | Allowed CORS origins (e.g. `https://sri-lanka-floodwatch.vercel.app`) |
| `CORS_ORIGIN_REGEX` | Optional | Backend | Regex for preview branches (e.g. `https://.*\.vercel\.app`) |
| `SUPABASE_URL` | Required (Prod) | Backend | Live Supabase Project URL (`https://<project>.supabase.co`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Required (Prod) | Backend | Server-side privileged key for persistence operations |
| `ALERT_COOLDOWN_SECONDS` | Optional | Backend | Cooldown between alert telemetry updates (default: `1800`s) |
| `ALERT_EMAIL_ENABLED` | Optional | Backend | `true` to enable external email delivery |
| `SMTP_HOST`, `SMTP_PORT` | Optional | Backend | SMTP configuration for email alerts |
| `ALERT_EMAIL_SENDER` | Optional | Backend | Authorized sender email address |
| `ALERT_SMS_ENABLED` | Optional | Backend | `true` to enable SMS gateway notifications |
| `SMS_API_KEY` | Optional | Backend | SMS Gateway API Key |

---

## 4. Operational Alert & Background Scheduling

The system includes automated batch evaluation across all 33 stations:
- **Batch Processing Script:** `scripts/process_alerts_cron.py`
- **Execution Interval:** Every 15–30 minutes via Cloud Scheduler or cron.
- **Duplicate Protection:** Active alerts are updated in-place without spawning duplicates; resolved automatically when flood probability subsides below 35%.

---

## 5. Security & Isolation Controls

1. **Zero Secret Leakage:** Checked and verified across all frontend `.js`, `.html`, and `.css` files.
2. **CORS Hardening:** Configured in `api/main.py` to allow only designated production frontend origins and verified Vercel preview domains.
3. **Non-Root Container Runtime:** `Dockerfile` configures a dedicated `appuser` non-root security context.
4. **Deterministic Dependencies:** Fixed in `requirements.txt` with strict scikit-learn versioning.
