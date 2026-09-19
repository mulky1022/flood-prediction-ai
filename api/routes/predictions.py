"""
Predictions API Routes — Unified Prediction API Layer.
"""

from typing import Optional, List
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from api.schemas.prediction import (
    PredictionResponse,
    CanonicalPredictionResponse,
    CanonicalLocationBlock,
    CanonicalRiskBlock,
    CanonicalActionBlock,
    CanonicalForecastBlock,
    MapPredictionItem,
    MapPredictionResponse,
    PredictionHistoryResponse,
    PredictionHistoryItem,
)
from api.schemas.common import ErrorResponse
from services.risk_engine import RiskEngine
from api.dependencies import get_db, get_prediction_engine, get_alert_service, SupabaseService, PredictorService, AlertService

router = APIRouter(tags=["Predictions"])


def _calculate_prediction_validity_and_status(created_at_str: Optional[str]) -> tuple:
    """
    Calculates prediction validity window and operational status.
    """
    now = datetime.now(timezone.utc)

    if not created_at_str:
        pred_time = now.isoformat()
        return pred_time, pred_time, (now + timedelta(hours=12)).isoformat(), "CURRENT"

    try:
        s = str(created_at_str)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        created_dt = datetime.fromisoformat(s)
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)

        valid_until_dt = created_dt + timedelta(hours=12)
        age_hours = (now - created_dt).total_seconds() / 3600.0

        if age_hours <= 12:
            status_str = "CURRENT"
        elif age_hours <= 24:
            status_str = "STALE"
        else:
            status_str = "EXPIRED"

        return created_dt.isoformat(), created_dt.isoformat(), valid_until_dt.isoformat(), status_str
    except Exception:
        pred_time = now.isoformat()
        return pred_time, pred_time, (now + timedelta(hours=12)).isoformat(), "CURRENT"


def _build_action_block(risk_level: str) -> CanonicalActionBlock:
    """
    Generates action recommendations based on risk level using central RiskEngine.
    """
    action_info = RiskEngine.get_canonical_action(risk_level)
    return CanonicalActionBlock(code=action_info["code"], message=action_info["message"])


@router.get(
    "/predictions/current/{location_id}",
    response_model=CanonicalPredictionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Location or prediction not found"},
        422: {"model": ErrorResponse, "description": "Invalid location parameter"}
    },
    summary="Get unified canonical current prediction for a location"
)
def get_current_prediction(
    location_id: str,
    db: SupabaseService = Depends(get_db),
    predictor: PredictorService = Depends(get_prediction_engine),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    Unified Prediction API — Single application gateway endpoint for current predictions.
    Strictly location-isolated. Never falls back to another location.
    """
    # 1. Validate location
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    canonical_loc_id = loc.get("id")

    # 2. Retrieve latest database prediction record or run live inference if missing
    latest_db_record = db.get_latest_prediction(canonical_loc_id)

    if not latest_db_record:
        # Run live inference to generate initial canonical prediction for location
        prediction_result = predictor.predict_location(canonical_loc_id, use_cache=True, derive_leakage_baselines=True)
        if prediction_result.get("status") == "success":
            save_res = db.save_prediction(prediction_result)
            pred_id = save_res.get("prediction_id") or (save_res.get("data", {}).get("id") if isinstance(save_res.get("data"), dict) else None)
            
            # Evaluate user alert preferences
            try:
                alert_service.evaluate_and_trigger_user_preferences(canonical_loc_id, prediction_result, None)
            except Exception:
                pass

            pred_data = prediction_result.get("prediction", {})
            risk_lvl = pred_data.get("risk_level", "LOW")
            prob = float(pred_data.get("flood_probability", 0.0))

            now_iso = datetime.now(timezone.utc).isoformat()
            valid_until_iso = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

            return CanonicalPredictionResponse(
                prediction_id=pred_id,
                location=CanonicalLocationBlock(
                    location_id=canonical_loc_id,
                    record_id=loc.get("record_id"),
                    name=loc.get("place_name") or loc.get("name", "Unknown Station"),
                    district=loc.get("district", "Unknown"),
                    latitude=loc.get("latitude"),
                    longitude=loc.get("longitude")
                ),
                prediction_time=now_iso,
                valid_from=now_iso,
                valid_until=valid_until_iso,
                is_stale=False,
                risk=CanonicalRiskBlock(
                    level=risk_lvl,
                    score=prob,
                    flood_probability_percent=round(prob * 100, 2)
                ),
                confidence=0.90,
                action=_build_action_block(risk_lvl),
                conditions={
                    "rainfall_mm_24h": float(pred_data.get("precipitation_sum_24h_mm") or 0.0),
                    "water_level_m": float(pred_data.get("river_discharge_m3s") or 0.0),
                    "water_level_trend": "Steady",
                    "humidity_percent": 85.0,
                    "temperature_c": 26.5
                },
                status="CURRENT"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"status": "error", "code": "NO_CURRENT_PREDICTION", "message": f"No current prediction available for location '{location_id}'."}
            )

    # Enforce Location Isolation invariant
    rec_loc_id = latest_db_record.get("location_id")
    if str(rec_loc_id) != str(canonical_loc_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "code": "LOCATION_ISOLATION_VIOLATION", "message": f"Database query returned record for location '{rec_loc_id}', expected '{canonical_loc_id}'."}
        )

    pred_time_iso, valid_from_iso, valid_until_iso, pred_status = _calculate_prediction_validity_and_status(latest_db_record.get("created_at"))
    prob = float(latest_db_record.get("flood_probability", 0.0))
    risk_lvl = latest_db_record.get("risk_level") or RiskEngine.derive_risk_level(prob)

    return CanonicalPredictionResponse(
        prediction_id=latest_db_record.get("id"),
        location=CanonicalLocationBlock(
            location_id=canonical_loc_id,
            record_id=loc.get("record_id"),
            name=loc.get("place_name") or loc.get("name", "Unknown Station"),
            district=loc.get("district", "Unknown"),
            latitude=loc.get("latitude"),
            longitude=loc.get("longitude")
        ),
        prediction_time=pred_time_iso,
        valid_from=valid_from_iso,
        valid_until=valid_until_iso,
        is_stale=(pred_status == "STALE"),
        risk=CanonicalRiskBlock(
            level=risk_lvl,
            score=prob,
            flood_probability_percent=round(prob * 100, 2)
        ),
        confidence=0.90,
        action=_build_action_block(risk_lvl),
        conditions={
            "rainfall_mm_24h": float(latest_db_record.get("rainfall_7d_mm", 0.0) / 7.0),
            "water_level_m": 0.0,
            "water_level_trend": "Steady",
            "humidity_percent": 85.0,
            "temperature_c": 26.5
        },
        status=pred_status
    )


@router.get(
    "/predictions/map",
    response_model=MapPredictionResponse,
    summary="Get current predictions for all map stations"
)
def get_map_predictions(
    db: SupabaseService = Depends(get_db),
    predictor: PredictorService = Depends(get_prediction_engine)
):
    """
    Returns canonical prediction records for all monitoring stations on the Flood Map.
    Guarantees zero client-side risk calculations.
    """
    locations = db.get_locations()
    items = []

    for loc in locations:
        loc_id = loc.get("id")
        if not loc_id:
            continue

        latest = db.get_latest_prediction(loc_id)

        if latest:
            pred_id = latest.get("id")
            pred_time = str(latest.get("created_at"))
            prob = float(latest.get("flood_probability", 0.0))
            risk_lvl = latest.get("risk_level") or RiskEngine.derive_risk_level(prob)
            status_str = "CURRENT"
        else:
            pred_id = None
            pred_time = datetime.now(timezone.utc).isoformat()
            risk_lvl = "LOW"
            prob = 0.0
            status_str = "NO_CURRENT_PREDICTION"

        lat_val = float(loc.get("latitude")) if loc.get("latitude") is not None else None
        lon_val = float(loc.get("longitude")) if loc.get("longitude") is not None else None

        action_blk = _build_action_block(risk_lvl)

        items.append(
            MapPredictionItem(
                location_id=loc_id,
                record_id=loc.get("record_id", f"LOC-{loc_id:03d}"),
                name=loc.get("place_name") or loc.get("name") or f"Station {loc_id}",
                district=loc.get("district") or "Sri Lanka",
                latitude=lat_val,
                longitude=lon_val,
                prediction_id=pred_id,
                prediction_time=pred_time,
                risk_level=risk_lvl,
                flood_probability=prob,
                action_code=action_blk.code,
                action_message=action_blk.message,
                status=status_str
            )
        )

    return MapPredictionResponse(
        status="success",
        total=len(items),
        predictions=items
    )


@router.get(
    "/predictions/id/{prediction_id}",
    response_model=PredictionHistoryItem,
    responses={404: {"model": ErrorResponse, "description": "Prediction record not found"}},
    summary="Get single prediction record by ID"
)
def get_prediction_by_id(
    prediction_id: int,
    db: SupabaseService = Depends(get_db)
):
    """
    Retrieves a single prediction record by its primary key ID.
    """
    pred_record = db.get_prediction_by_id(prediction_id)
    if not pred_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "PREDICTION_NOT_FOUND", "message": f"Prediction record '{prediction_id}' not found."}
        )

    return PredictionHistoryItem(
        id=pred_record.get("id"),
        prediction_id=pred_record.get("id"),
        location_id=pred_record.get("location_id"),
        created_at=str(pred_record.get("created_at")),
        prediction_time=str(pred_record.get("created_at")),
        prediction_class=pred_record.get("prediction_class", 0),
        flood_probability=float(pred_record.get("flood_probability", 0.0)),
        non_flood_probability=float(pred_record.get("non_flood_probability", 1.0)),
        risk_level=pred_record.get("risk_level", "LOW"),
        model_name=pred_record.get("model_name", "RandomForestClassifier"),
        model_version=pred_record.get("model_version", "1.0.0"),
        data_quality_status=pred_record.get("data_quality_status", "GOOD"),
        data_source=pred_record.get("data_source", "Open-Meteo"),
        status="RECORDED"
    )


@router.get(
    "/predict/{location_id}",
    response_model=PredictionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Location not found"},
        422: {"model": ErrorResponse, "description": "Prediction blocked or feature unavailable"},
        503: {"model": ErrorResponse, "description": "Weather service unavailable"}
    },
    summary="Execute live ML prediction pipeline for a location"
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
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

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

    # Data Integrity Guard: Ensure returned location strictly matches requested location
    returned_loc_id = prediction_result.get("location", {}).get("id")
    requested_loc_id = loc.get("id")
    if returned_loc_id is not None and requested_loc_id is not None and str(returned_loc_id) != str(requested_loc_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "code": "LOCATION_PREDICTION_MISMATCH", "message": f"Data integrity error: requested location '{requested_loc_id}' but prediction generated for '{returned_loc_id}'."}
        )

    prev_pred = db.get_latest_prediction(loc.get("id"))
    save_result = db.save_prediction(prediction_result)
    pred_id = save_result.get("prediction_id") or (save_result.get("data", {}).get("id") if isinstance(save_result.get("data"), dict) else None)

    try:
        alert_service.evaluate_and_trigger_user_preferences(loc.get("id"), prediction_result, prev_pred)
    except Exception:
        pass

    pred_data = prediction_result.get("prediction", {})
    return {
        "status": "success",
        "ready_for_prediction": True,
        "prediction_id": pred_id,
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


@router.get(
    "/predictions/history/{location_id}",
    response_model=PredictionHistoryResponse,
    responses={404: {"model": ErrorResponse, "description": "Location not found"}},
    summary="Get prediction history for a location"
)
def get_prediction_history_canonical(
    location_id: str,
    risk_level: Optional[str] = Query(None, description="Filter by risk level (LOW, MODERATE, HIGH, CRITICAL)"),
    start_date: Optional[str] = Query(None, description="Start date ISO string"),
    end_date: Optional[str] = Query(None, description="End date ISO string"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: SupabaseService = Depends(get_db)
):
    """
    Retrieves historical prediction records strictly belonging to the specified location.
    Preserves historical prediction identity, model version, risk level, and canonical action.
    """
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    canonical_loc_id = loc.get("id")

    # Sanitize Query defaults if directly invoked in Python functions
    clean_risk = risk_level if isinstance(risk_level, str) else None
    clean_start = start_date if isinstance(start_date, str) else None
    clean_end = end_date if isinstance(end_date, str) else None
    clean_limit = limit if isinstance(limit, int) else 50
    clean_offset = offset if isinstance(offset, int) else 0

    # Fetch total un-paginated count for pagination metadata
    all_matching = db.get_prediction_history(
        canonical_loc_id,
        risk_level=clean_risk,
        start_date=clean_start,
        end_date=clean_end,
        limit=1000,
        offset=0
    )
    total_count = len(all_matching)

    history = db.get_prediction_history(
        canonical_loc_id,
        risk_level=clean_risk,
        start_date=clean_start,
        end_date=clean_end,
        limit=clean_limit,
        offset=clean_offset
    )

    items = []
    for h in history:
        prob = float(h.get("flood_probability", 0.0))
        risk_lvl = h.get("risk_level") or RiskEngine.derive_risk_level(prob)
        action_mapping = RiskEngine.get_canonical_action(risk_lvl)

        pred_id = h.get("prediction_id") or h.get("id")
        created_at_str = str(h.get("created_at") or datetime.now(timezone.utc).isoformat())

        items.append(
            PredictionHistoryItem(
                id=pred_id,
                prediction_id=pred_id,
                location_id=canonical_loc_id,
                created_at=created_at_str,
                prediction_time=created_at_str,
                valid_from=str(h.get("valid_from") or created_at_str),
                valid_until=str(h.get("valid_until") or created_at_str),
                prediction_class=int(h.get("prediction_class", 1 if risk_lvl in ["HIGH", "CRITICAL"] else 0)),
                flood_probability=prob,
                flood_probability_percent=round(prob * 100, 2),
                non_flood_probability=round(1.0 - prob, 4),
                risk_level=risk_lvl,
                action_code=str(h.get("action_code") or action_mapping["code"]),
                action_message=str(h.get("action_message") or action_mapping["message"]),
                confidence=float(h.get("confidence", 0.90)),
                model_name=str(h.get("model_name", "RandomForestClassifier")),
                model_version=str(h.get("model_version", "1.0.0")),
                data_quality_status=str(h.get("data_quality_status", "GOOD")),
                data_source=str(h.get("data_source", "Open-Meteo")),
                status="RECORDED"
            )
        )

    has_more = (clean_offset + clean_limit) < total_count

    return PredictionHistoryResponse(
        status="success",
        location_id=canonical_loc_id,
        total=total_count,
        limit=clean_limit,
        offset=clean_offset,
        has_more=has_more,
        items=items
    )


@router.get(
    "/predictions/{location_id}",
    response_model=PredictionHistoryResponse,
    responses={404: {"model": ErrorResponse, "description": "Location not found"}},
    include_in_schema=False
)
def get_prediction_history_legacy(
    location_id: str,
    risk_level: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: SupabaseService = Depends(get_db)
):
    """
    Legacy route alias for prediction history.
    """
    return get_prediction_history_canonical(
        location_id=location_id,
        risk_level=risk_level,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
        db=db
    )


@router.get(
    "/predictions/{location_id}/latest",
    response_model=PredictionHistoryItem,
    responses={404: {"model": ErrorResponse, "description": "No prediction history found"}},
    summary="Get latest recorded prediction record"
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
        prediction_id=latest.get("id"),
        location_id=latest.get("location_id"),
        created_at=str(latest.get("created_at")),
        prediction_time=str(latest.get("created_at")),
        prediction_class=latest.get("prediction_class", 0),
        flood_probability=float(latest.get("flood_probability", 0.0)),
        non_flood_probability=float(latest.get("non_flood_probability", 1.0)),
        risk_level=latest.get("risk_level", "LOW"),
        model_name=latest.get("model_name", "RandomForestClassifier"),
        model_version=latest.get("model_version", "1.0.0"),
        data_quality_status=latest.get("data_quality_status", "GOOD"),
        data_source=latest.get("data_source", "Open-Meteo"),
        status="RECORDED"
    )


@router.get(
    "/predictions/id/{prediction_id}",
    response_model=PredictionHistoryItem,
    responses={404: {"model": ErrorResponse, "description": "Prediction record not found"}},
    summary="Get single prediction record by ID"
)
def get_prediction_by_id(
    prediction_id: int,
    db: SupabaseService = Depends(get_db)
):
    """
    Retrieves a single prediction record by its primary key ID.
    """
    pred_record = db.get_prediction_by_id(prediction_id)
    if not pred_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "PREDICTION_NOT_FOUND", "message": f"Prediction record '{prediction_id}' not found."}
        )

    return PredictionHistoryItem(
        id=pred_record.get("id"),
        prediction_id=pred_record.get("id"),
        location_id=pred_record.get("location_id"),
        created_at=str(pred_record.get("created_at")),
        prediction_time=str(pred_record.get("created_at")),
        prediction_class=pred_record.get("prediction_class", 0),
        flood_probability=float(pred_record.get("flood_probability", 0.0)),
        non_flood_probability=float(pred_record.get("non_flood_probability", 1.0)),
        risk_level=pred_record.get("risk_level", "LOW"),
        model_name=pred_record.get("model_name", "RandomForestClassifier"),
        model_version=pred_record.get("model_version", "1.0.0"),
        data_quality_status=pred_record.get("data_quality_status", "GOOD"),
        data_source=pred_record.get("data_source", "Open-Meteo"),
        status="RECORDED"
    )

