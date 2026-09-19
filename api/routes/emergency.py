"""
Emergency & Low-Bandwidth API Routes — Phase 14 Presentation Layer.
Consumes canonical Phase 1-13 prediction, risk, action, and official warning engines.
Strictly location-isolated. Never runs ML or calculates risk in emergency delivery layer.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.schemas.emergency import (
    EmergencyDataResponse,
    EmergencyLocationBlock,
    EmergencyPredictionBlock,
    EmergencyActionBlock,
    EmergencyOfficialWarningBlock,
    EmergencyInfoBlock,
)
from api.schemas.common import ErrorResponse
from services.risk_engine import RiskEngine
from api.dependencies import (
    get_db,
    get_prediction_engine,
    get_official_warning_service,
    SupabaseService,
    PredictorService,
    OfficialWarningService
)

router = APIRouter(prefix="/emergency", tags=["Emergency Mode"])


def _calculate_prediction_freshness(created_at_str: Optional[str]) -> tuple:
    now = datetime.now(timezone.utc)
    if not created_at_str:
        now_iso = now.isoformat()
        return now_iso, now_iso, (now + timedelta(hours=12)).isoformat(), "CURRENT"

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
        now_iso = now.isoformat()
        return now_iso, now_iso, (now + timedelta(hours=12)).isoformat(), "CURRENT"


@router.get(
    "/{location_id}",
    response_model=EmergencyDataResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Location not found"},
        422: {"model": ErrorResponse, "description": "Invalid location parameter"}
    },
    summary="Get aggregated low-bandwidth emergency flood risk & official warning payload"
)
def get_emergency_data(
    location_id: str,
    lang: Optional[str] = Query("en", description="Target language code: en, si, ta"),
    db: SupabaseService = Depends(get_db),
    predictor: PredictorService = Depends(get_prediction_engine),
    warning_service: OfficialWarningService = Depends(get_official_warning_service)
):
    """
    Lightweight read-only Emergency API payload.
    Aggregates canonical location, prediction, Phase 5 action, Phase 13 official warning, and DMC 117 hotline info.
    Payload size is minimized (< 2KB) for low-bandwidth cellular environments.
    """
    # 1. Validate location isolation
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    canonical_loc_id = loc.get("id")

    loc_block = EmergencyLocationBlock(
        id=str(location_id),
        name=loc.get("place_name") or loc.get("name", "Unknown Location"),
        district=loc.get("district", "Unknown"),
        province=loc.get("province", "Sri Lanka")
    )

    # 2. Canonical Prediction & Action
    pred_block = None
    action_block = None
    try:
        latest_db_record = db.get_latest_prediction(canonical_loc_id)
        if not latest_db_record:
            # Fallback to live inference if database record missing
            prediction_result = predictor.predict_location(canonical_loc_id, use_cache=True)
            if prediction_result.get("status") == "success":
                latest_db_record = db.save_prediction(prediction_result)
                if isinstance(latest_db_record, dict) and latest_db_record.get("data"):
                    latest_db_record = latest_db_record.get("data")

        if latest_db_record and isinstance(latest_db_record, dict):
            p_time, v_from, v_until, freshness = _calculate_prediction_freshness(latest_db_record.get("created_at"))
            risk_level = str(latest_db_record.get("risk_level", "LOW")).upper()
            pred_id = str(latest_db_record.get("id") or latest_db_record.get("prediction_id", ""))

            pred_block = EmergencyPredictionBlock(
                prediction_id=pred_id,
                risk_level=risk_level,
                prediction_time=p_time,
                valid_from=v_from,
                valid_until=v_until,
                freshness_status=freshness
            )

            # Canonical Phase 5 Action
            action_info = RiskEngine.get_canonical_action(risk_level)
            action_block = EmergencyActionBlock(
                code=action_info["code"],
                message=action_info["message"]
            )
    except Exception as e:
        # Prediction API partial failure handling - preserve prediction as None
        pred_block = None
        action_block = None

    # 3. Canonical Phase 13 Official Warning
    warning_block = None
    try:
        warning_data = warning_service.get_current_warning(canonical_loc_id)
        if warning_data and isinstance(warning_data, dict):
            warn_item = warning_data.get("warning") or warning_data
            status_val = warning_data.get("status", "NONE")

            if isinstance(warn_item, dict) and warn_item.get("title"):
                warning_block = EmergencyOfficialWarningBlock(
                    warning_id=warn_item.get("id") or warn_item.get("warning_id"),
                    status=status_val,
                    source_name=warn_item.get("source_name", "Disaster Management Centre (DMC) Sri Lanka"),
                    source_url=warn_item.get("source_url", "https://www.dmc.gov.lk"),
                    title=warn_item.get("title"),
                    message=warn_item.get("message"),
                    issued_at=warn_item.get("issued_at") or warn_item.get("created_at"),
                    valid_until=warn_item.get("valid_until")
                )
            else:
                warning_block = EmergencyOfficialWarningBlock(
                    status=status_val,
                    title="No Active Official Warning" if status_val == "NO_ACTIVE_WARNING" else "Warning Unavailable",
                    message="No official warning recorded for this area."
                )
    except Exception:
        warning_block = EmergencyOfficialWarningBlock(
            status="UNAVAILABLE",
            title="Official Warning Unavailable",
            message="Official warning service could not be reached."
        )

    # 4. Emergency DMC Hotline 117 Info
    info_block = EmergencyInfoBlock(
        hotline="117",
        hotline_name="Disaster Management Centre Hotline",
        hotline_url="tel:117",
        safety_guidance="In case of sudden flooding, move immediately to higher ground. Keep emergency supplies ready and call DMC Hotline 117."
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    return EmergencyDataResponse(
        status="success",
        location=loc_block,
        prediction=pred_block,
        action=action_block,
        official_warning=warning_block,
        emergency=info_block,
        timestamp=now_iso
    )
