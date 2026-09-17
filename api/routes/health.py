"""
Health Check Routes.
"""

from fastapi import APIRouter, Depends
from api.schemas.common import HealthResponse
from api.dependencies import get_db, get_prediction_engine, SupabaseService, PredictorService

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health(
    db: SupabaseService = Depends(get_db),
    predictor: PredictorService = Depends(get_prediction_engine)
):
    """
    Returns system operational health status.
    """
    model_ok = predictor.model is not None and predictor.scaler is not None
    db_ok = db.is_connected

    return HealthResponse(
        status="ok",
        service="Sri Lanka FloodWatch API",
        version=predictor.metadata.get("model_version", "1.0.0"),
        model_loaded=model_ok,
        database_connected=db_ok
    )
