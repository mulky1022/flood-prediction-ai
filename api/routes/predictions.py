"""
Predictions API Routes.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from api.schemas.prediction import (
    PredictionResponse,
    PredictionHistoryResponse,
    PredictionHistoryItem,
)
from api.schemas.common import ErrorResponse
from api.dependencies import get_db, get_prediction_engine, get_alert_service, SupabaseService, PredictorService, AlertService

router = APIRouter(tags=["Predictions"])


@router.get(
    "/predict/{location_id}",
    response_model=PredictionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Location not found"},
        422: {"model": ErrorResponse, "description": "Prediction blocked or feature unavailable"},
        503: {"model": ErrorResponse, "description": "Weather service unavailable"}
    }
)
def predict_flood_risk(
    location_id: str,
    db: SupabaseService = Depends(get_db),
    predictor: PredictorService = Depends(get_prediction_engine),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    Executes live end-to-end flood risk prediction for a location.
    Combines static GIS features with live Open-Meteo precipitation, transforms via StandardScaler,
    evaluates Random Forest probabilities, and persists prediction audit record in database.
    """
    # Verify location exists
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    # Execute full prediction pipeline
    prediction_result = predictor.predict_location(loc.get("id"), use_cache=True, derive_leakage_baselines=True)

    if prediction_result.get("status") == "location_not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": prediction_result.get("message")}
        )
    elif prediction_result.get("status") == "prediction_unavailable":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "status": "error",
                "code": "PREDICTION_UNAVAILABLE",
                "message": prediction_result.get("message", "Prediction could not be generated."),
                "details": prediction_result.get("data_quality")
            }
        )
    elif prediction_result.get("status") != "success":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "code": "INFERENCE_ERROR", "message": prediction_result.get("message")}
        )

    # Retrieve previous prediction for state transition check (avoids duplicate alerts on consecutive high cycles)
    prev_pred = db.get_latest_prediction(loc.get("id"))

    # Persist prediction in Supabase database
    db.save_prediction(prediction_result)

    # Evaluate user alert preferences on threshold transitions
    try:
        alert_service.evaluate_and_trigger_user_preferences(loc.get("id"), prediction_result, prev_pred)
    except Exception as e:
        pass

    # Reformat prediction block for schema compatibility if needed
    pred_data = prediction_result.get("prediction", {})
    response_payload = {
        "status": "success",
        "ready_for_prediction": True,
        "location": prediction_result.get("location"),
        "prediction": {
            "class": pred_data.get("class", 0),
            "flood_probability": pred_data.get("flood_probability", 0.0),
            "flood_probability_percent": pred_data.get("flood_probability_percent", 0.0),
            "non_flood_probability": pred_data.get("non_flood_probability", 1.0),
            "risk_level": pred_data.get("risk_level", "LOW")
        },
        "model": prediction_result.get("model"),
        "data_quality": prediction_result.get("data_quality"),
        "input_audit": prediction_result.get("input_audit")
    }

    return response_payload


@router.get(
    "/predictions/{location_id}",
    response_model=PredictionHistoryResponse,
    responses={404: {"model": ErrorResponse, "description": "Location not found"}}
)
def get_prediction_history(
    location_id: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: SupabaseService = Depends(get_db)
):
    """
    Retrieves historical prediction records for a location with pagination.
    """
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    history = db.get_prediction_history(loc.get("id"), limit=limit, offset=offset)

    items = []
    for h in history:
        items.append(
            PredictionHistoryItem(
                id=h.get("id"),
                location_id=h.get("location_id"),
                created_at=str(h.get("created_at")),
                prediction_class=h.get("prediction_class", 0),
                flood_probability=float(h.get("flood_probability", 0.0)),
                non_flood_probability=float(h.get("non_flood_probability", 1.0)),
                model_name=h.get("model_name", "RandomForestClassifier"),
                model_version=h.get("model_version", "1.0.0"),
                data_quality_status=h.get("data_quality_status", "GOOD"),
                data_source=h.get("data_source", "Open-Meteo")
            )
        )

    return PredictionHistoryResponse(
        status="success",
        location_id=loc.get("id"),
        total=len(items),
        items=items
    )


@router.get(
    "/predictions/{location_id}/latest",
    response_model=PredictionHistoryItem,
    responses={404: {"model": ErrorResponse, "description": "No prediction history found"}}
)
def get_latest_prediction(
    location_id: str,
    db: SupabaseService = Depends(get_db)
):
    """
    Retrieves the most recent recorded prediction for a location.
    """
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    latest = db.get_latest_prediction(loc.get("id"))
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "NO_PREDICTION_HISTORY", "message": f"No prediction history recorded for location '{location_id}' yet."}
        )

    return PredictionHistoryItem(
        id=latest.get("id"),
        location_id=latest.get("location_id"),
        created_at=str(latest.get("created_at")),
        prediction_class=latest.get("prediction_class", 0),
        flood_probability=float(latest.get("flood_probability", 0.0)),
        non_flood_probability=float(latest.get("non_flood_probability", 1.0)),
        model_name=latest.get("model_name", "RandomForestClassifier"),
        model_version=latest.get("model_version", "1.0.0"),
        data_quality_status=latest.get("data_quality_status", "GOOD"),
        data_source=latest.get("data_source", "Open-Meteo")
    )
