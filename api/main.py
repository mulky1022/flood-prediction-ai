"""
Sri Lanka Live Early Flood Risk Prediction System - FastAPI Application.

Main entry point configuring routers, CORS middleware, exception handlers,
and startup lifecycle events.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Load environment
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

from api.routes.health import router as health_router
from api.routes.config import router as config_router
from api.routes.locations import router as locations_router
from api.routes.weather import router as weather_router
from api.routes.predictions import router as predictions_router
from api.routes.alerts import router as alerts_router
from services.predictor import get_predictor
from services.supabase_service import get_supabase_service


# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("FloodWatchAPI")

# Application Initialization
app = FastAPI(
    title="Sri Lanka Live Early Flood Risk Prediction & Notification System",
    description=(
        "Production-grade early warning API combining machine learning, "
        "Open-Meteo live rainfall telemetry, static geospatial infrastructure data, "
        "and Supabase PostgreSQL persistence."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
allowed_origins_env = os.getenv("FRONTEND_ORIGIN", "http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000,http://127.0.0.1:3000,https://sri-lanka-floodwatch.vercel.app")
allowed_origins = [orig.strip() for orig in allowed_origins_env.split(",") if orig.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Global Exception Handler
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "code": f"HTTP_{exc.status_code}", "message": str(detail)}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred. Please try again later."
        }
    )


# Lifecycle Events
@app.on_event("startup")
async def startup_event():
    logger.info("Initializing Sri Lanka FloodWatch API...")
    try:
        predictor = get_predictor()
        logger.info(f"Model {predictor.metadata.get('model_name')} v{predictor.metadata.get('model_version')} loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load ML artifacts during startup: {e}")

    try:
        db = get_supabase_service()
        if db.is_connected:
            logger.info("Connected to remote Supabase PostgreSQL.")
        else:
            logger.info("Operating in local database fallback mode.")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")


# Root Deployment Health Check
@app.get("/api/health", tags=["Health"])
def root_health():
    """Simple root health check endpoint for cloud deployment platforms."""
    return {"status": "ok", "service": "Sri Lanka FloodWatch API", "version": "1.0.0"}


# Mount Version 1 Application Routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(locations_router, prefix="/api/v1")
app.include_router(weather_router, prefix="/api/v1")
app.include_router(predictions_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")

# Mount Static Frontend for Unified Direct Access
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

