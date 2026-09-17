# Sri Lanka Live Early Flood Risk Prediction System — Production Deployment

## Live Production Links

- **Main Dashboard**: [https://flood-prediction-roan.vercel.app/](https://flood-prediction-roan.vercel.app/)
- **Live Interactive Map**: [https://flood-prediction-roan.vercel.app/map](https://flood-prediction-roan.vercel.app/map)
- **District Analytics Console**: [https://flood-prediction-roan.vercel.app/district](https://flood-prediction-roan.vercel.app/district)
- **Real-Time Alerts**: [https://flood-prediction-roan.vercel.app/alerts](https://flood-prediction-roan.vercel.app/alerts)
- **API Health Check**: [https://flood-prediction-roan.vercel.app/api/v1/health](https://flood-prediction-roan.vercel.app/api/v1/health)
- **Interactive API Documentation (Swagger)**: [https://flood-prediction-roan.vercel.app/docs](https://flood-prediction-roan.vercel.app/docs)

---

## Deployment Architecture

- **Deployment Model**: Unified Single Project on Vercel
- **Frontend**: Static Web App (HTML5, Vanilla CSS3, Vanilla ES6 JavaScript, Leaflet.js) served directly via Vercel Edge CDN from `/public`
- **Backend**: Python ASGI Serverless Function (`api/index.py` wrapping FastAPI) running on Python 3.12
- **ML Engine**: Scikit-learn Random Forest Classifier + StandardScaler loaded in-memory
- **Database**: Remote PostgreSQL on Supabase with Row Level Security (RLS) policies
- **Weather Feed**: Live telemetry from Open-Meteo REST API
