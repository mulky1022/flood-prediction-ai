# Production Deployment & Local Operations Guide
## Sri Lanka Live Early Flood Risk Prediction & Notification System

**Version:** 1.0.0  
**Target Platform:** Vercel (Unified Architecture) + Supabase PostgreSQL + Open-Meteo API  

---

## 1. Prerequisites

- **Python:** 3.10, 3.11, or 3.12 (with `pip` and virtual environment support)
- **Node.js:** Node 18+ & `npm` (for Vercel CLI)
- **Vercel CLI:** Version 39+ (`npm install -g vercel`)
- **Git:** Git 2.30+
- **Supabase Account & Project:** PostgreSQL REST endpoint and API credentials
- **Internet Access:** Outbound HTTPS access to `api.open-meteo.com` and `archive-api.open-meteo.com`

---

## 2. Environment Variables Matrix

Create a `.env` file in the project root for local execution, and add these exact keys to the Vercel Dashboard (`Settings > Environment Variables`):

| Variable Name | Environment | Required | Example / Description |
| :--- | :--- | :---: | :--- |
| `SUPABASE_URL` | Production / Backend | **YES** | `https://heqwhyidkpyjuftvyecs.supabase.co/rest/v1/` |
| `SUPABASE_SERVICE_ROLE_KEY` | Production / Backend | **YES** | `eyJhbGciOiJIUzI1NiIsInR5cCI6...` (Backend only, never expose to frontend) |
| `SUPABASE_ANON_KEY` | Production / Backend | **YES** | `eyJhbGciOiJIUzI1NiIsInR5cCI6...` |
| `OPEN_METEO_BASE_URL` | Production / Backend | **YES** | `https://api.open-meteo.com/v1/forecast` |
| `OPEN_METEO_TIMEOUT` | Production / Backend | No | `20.0` (Seconds) |
| `OPEN_METEO_MAX_RETRIES` | Production / Backend | No | `2` |
| `FRONTEND_ORIGIN` | Production / Backend | **YES** | `http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000,http://localhost:8000,https://sri-lanka-floodwatch.vercel.app` |
| `APP_ENV` | Production / Backend | **YES** | `production` |
| `APP_VERSION` | Production / Backend | **YES** | `1.0.0` |
| `PORT` | Local Development | No | `8000` |
| `HOST` | Local Development | No | `0.0.0.0` |

> [!CAUTION]
> **Zero Secrets on Client:** Never expose `SUPABASE_SERVICE_ROLE_KEY` or database passwords to client-side scripts. All client communication routes through the same-origin `/api/v1/...` endpoints.

---

## 3. Local Development Guide

### Step 3.1: Clone and Setup Virtual Environment
```bash
# Clone the repository
git clone <repository_url>
cd "flood prediction"

# Create and activate Python virtual environment
python -m venv .venv

# Windows Powershell / CMD:
.venv\Scripts\activate

# macOS / Linux:
source .venv/bin/activate

# Install exact dependencies
pip install -r requirements.txt
```

### Step 3.2: Run FastAPI Server with Unified Static Frontend
```bash
uvicorn api.main:app --reload --port 8000
```

- **Live Application:** `http://127.0.0.1:8000/` (or `http://localhost:8000/`)
- **Flood Map:** `http://127.0.0.1:8000/map.html`
- **Location Details:** `http://127.0.0.1:8000/district.html`
- **Alerts & History:** `http://127.0.0.1:8000/alerts.html`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **OpenAPI JSON Schema:** `http://127.0.0.1:8000/openapi.json`

---

## 4. Local Vercel Development Guide

Run the full Vercel routing simulation locally:

```bash
# Ensure Vercel CLI is installed


# Run local Vercel server (serves frontend & serverless Python API together)
vercel dev
```

The application will launch on `http://localhost:3000` with direct same-origin `/api/...` serverless function execution.

---

## 5. Database Migration & Setup

Apply the production DDL to your Supabase PostgreSQL database:

### Option A: Via Supabase SQL Editor (Recommended)
1. Open your Supabase Dashboard: `https://app.supabase.com/project/<your-project-id>`
2. Navigate to **SQL Editor** on the left navigation panel.
3. Open `supabase/migrations/20260917000000_production_schema.sql` (or `database/schema.sql`).
4. Paste the script contents and click **Run**.
5. Verify tables created: `locations` (33 rows), `weather_observations`, `predictions`, `alerts`.

### Option B: Via Python Test Harness
```bash
python scripts/test_supabase.py
```

---

## 6. Vercel CLI Production Deployment

### Step 6.1: Vercel Authentication
```bash


### Step 6.2: Link Project
```bash
vercel link
```
- Select your Vercel team/scope (e.g. `mulky1022`).
- Link to an existing project or create `sri-lanka-floodwatch`.

### Step 6.3: Configure Production Environment Variables
```bash
vercel env add SUPABASE_URL production
vercel env add SUPABASE_SERVICE_ROLE_KEY production
vercel env add SUPABASE_ANON_KEY production
vercel env add OPEN_METEO_BASE_URL production
vercel env add APP_ENV production
```

### Step 6.4: Execute Production Deployment
```bash
vercel deploy --prod
```

---

## 7. Production Verification Checklist

Run these smoke tests immediately after deployment:

```bash
# 1. Verify Health Check
curl -s https://sri-lanka-floodwatch.vercel.app/api/v1/health | grep '"status":"ok"'

# 2. Verify Spatial Registry (33 Stations)
curl -s https://sri-lanka-floodwatch.vercel.app/api/v1/locations | grep '"total":33'

# 3. Verify Live Weather Ingestion (Kolonnawa)
curl -s https://sri-lanka-floodwatch.vercel.app/api/v1/weather/1 | grep '"status":"success"'

# 4. Verify Live ML Prediction (Kolonnawa)
curl -s https://sri-lanka-floodwatch.vercel.app/api/v1/predict/1 | grep '"status":"success"'

# 5. Verify Active Alerts
curl -s https://sri-lanka-floodwatch.vercel.app/api/v1/alerts/active | grep '"status":"success"'
```

---

## 8. Rollback & Troubleshooting

### Instant Rollback via Vercel CLI
```bash
# List previous deployments
vercel ls

# Rollback to specific deployment alias
vercel alias set <previous-deployment-url> sri-lanka-floodwatch.vercel.app
```

### Common Issues & Resolutions
1. **HTTP 503 Weather Unavailable:**
   - Verify server outbound network connectivity to `api.open-meteo.com`.
   - The built-in 30-minute caching layer mitigates rate limiting.
2. **Missing Prediction Features:**
   - Ensure `derive_leakage_baselines=True` is enabled in `services/predictor.py`.
   - All 64 features will synthesize automatically from static GIS + Open-Meteo feeds.
3. **Database Connection Dropped:**
   - The application automatically switches to in-memory fallback mode (`_LOCAL_PREDICTIONS`, `_LOCAL_ALERTS`) with zero user-facing HTTP 500 errors.
