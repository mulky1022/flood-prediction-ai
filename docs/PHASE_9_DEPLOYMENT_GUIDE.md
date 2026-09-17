# PHASE 9 PRODUCTION DEPLOYMENT GUIDE

**Project:** Sri Lanka Live Early Flood Risk Prediction & Notification System  
**Phase:** 9 — Deployment & Production Setup  

---

## 1. Prerequisites & Dependencies

- **Python:** 3.11.x
- **Container Runtime:** Docker 24+ / Podman
- **Cloud Accounts:** Vercel (Frontend), Cloud Run / Railway / Render (Backend), Supabase (Database)
- **Repository Cleanliness:** `.env` and `cache/*.json` ignored by `.gitignore` and `.dockerignore`.

---

## 2. Step-by-Step Deployment Instructions

### Step 1: Database Provisioning (Supabase)
1. Create a new Supabase project in the nearest region (e.g. `ap-southeast-1` Singapore or `ap-south-1` Mumbai).
2. Open the **SQL Editor** in the Supabase Dashboard.
3. Paste and execute the DDL script located in [database/schema.sql](file:///c:/Users/dj/Desktop/project/flood%20prediction/database/schema.sql).
4. Verify table creation (`locations`, `weather_observations`, `predictions`, `alerts`).
5. Copy the **Project URL** and **service_role key** (Secret) from `Project Settings -> API`.

### Step 2: Backend Deployment (FastAPI on Container / PaaS)
#### Option A: Docker Container (Google Cloud Run / AWS ECS)
```bash
# Build production container image
docker build -t sri-lanka-floodwatch-api:v1.0.0 .

# Test locally with production settings
docker run -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e SUPABASE_URL=https://your-project.supabase.co \
  -e SUPABASE_SERVICE_ROLE_KEY=your-key \
  sri-lanka-floodwatch-api:v1.0.0
```

#### Option B: Cloud Deployment (Railway / Render / Cloud Run)
1. Connect GitHub repository.
2. Set Root Directory to repository root.
3. Configure Start Command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 2` (or use `Dockerfile`).
4. Set Environment Variables:
   - `ENVIRONMENT=production`
   - `FRONTEND_ORIGIN=https://sri-lanka-floodwatch.vercel.app`
   - `SUPABASE_URL=https://your-project.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY=your-service-role-key`
5. Deploy and verify health endpoint at `https://<backend-host>/api/v1/health`.

### Step 3: Frontend Deployment (Vercel)
1. In Vercel, import the project repository.
2. Configure settings:
   - **Framework Preset:** Other
   - **Root Directory:** `./`
   - **Output Directory:** `frontend`
3. Set Environment Variable:
   - `FLOODWATCH_API_BASE_URL=https://<your-backend-host>/api/v1`
4. Click **Deploy**.
5. Verify live routing across all 4 pages:
   - Live Dashboard: `https://<your-app>.vercel.app/`
   - Flood Map: `https://<your-app>.vercel.app/map`
   - Location Details: `https://<your-app>.vercel.app/district`
   - Alerts & History: `https://<your-app>.vercel.app/alerts`

### Step 4: Scheduled Background Processing
To ensure continuous early warnings without requiring active browser sessions:
- Configure a cron job or Google Cloud Scheduler to hit `/api/v1/alerts` or execute `python scripts/process_alerts_cron.py` every 15 minutes.

---

## 3. Verification & Smoke Testing

1. **Health Verification:** `curl -f https://<backend-host>/api/v1/health` $\to$ Returns HTTP 200 with `model_loaded: true`.
2. **Station Inference:** `curl -f https://<backend-host>/api/v1/predict/1` $\to$ Returns real-time probabilistic prediction for Kolonnawa.
3. **Frontend Integration:** Open the Vercel URL, change station, observe gauge update, and review active alert banners.

---

## 4. Rollback & Disaster Recovery

- **Frontend Rollback:** Instant 1-click rollback to prior deployment SHA in Vercel Deployment History.
- **Backend Rollback:** Re-deploy previous container image tag or rollback commit in PaaS dashboard.
- **Database Backup:** Automatic daily Supabase point-in-time recovery and schema re-application via `database/schema.sql`.
