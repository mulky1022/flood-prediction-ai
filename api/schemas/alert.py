"""
Alert Pydantic Schemas.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class AlertLocationInfo(BaseModel):
    id: int = Field(..., example=7)
    record_id: Optional[str] = Field(None, example="LK-RAT-07")
    district: str = Field(..., example="Ratnapura")
    place_name: str = Field(..., example="Ratnapura Town (Kalu Ganga Upper)")
    latitude: Optional[float] = Field(None, example=6.6828)
    longitude: Optional[float] = Field(None, example=80.4014)


class AlertItem(BaseModel):
    id: int = Field(..., example=1)
    prediction_id: Optional[Union[int, str]] = Field(None, example="TEST-RAT-001")
    location_id: int = Field(..., example=7)
    location: Optional[AlertLocationInfo] = None
    risk_level: str = Field(..., example="HIGH")
    action_code: Optional[str] = Field(None, example="PREPARE")
    action_message: Optional[str] = Field(None, example="Prepare emergency supplies and monitor local water levels.")
    valid_from: Optional[str] = Field(None, example="2026-09-18T12:00:00+05:30")
    expires_at: Optional[str] = Field(None, example="2026-09-18T18:00:00+05:30")
    flood_probability: float = Field(..., ge=0.0, le=1.0, example=0.7650)
    flood_probability_percent: Optional[float] = Field(None, example=76.50)
    prediction_class: int = Field(..., example=1)
    title: str = Field(..., example="High Flood Risk Warning — Ratnapura")
    message: str = Field(..., example="Hydrological model indicates elevated runoff and high flood probability (76.50%) in Ratnapura.")
    recommendation: Optional[str] = Field(
        None,
        example="Alert local emergency response units and prepare low-lying drainage channels."
    )
    status: str = Field(default="ACTIVE", example="ACTIVE")
    notification_status: str = Field(default="NOT_REQUIRED", example="NOT_REQUIRED")
    data_source: str = Field(default="Open-Meteo / RandomForest v1.0.0", example="Open-Meteo / RandomForest v1.0.0")
    created_at: str
    updated_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None


class AlertResponse(BaseModel):
    status: str = Field(default="success", example="success")
    alert: AlertItem


class CurrentAlertResponse(BaseModel):
    status: str = Field(default="success", example="success")
    alert: Optional[AlertItem] = None
    message: str = Field(..., example="Active flood alert found.")


class AlertListResponse(BaseModel):
    status: str = Field(default="success", example="success")
    total: int = Field(..., example=5)
    active_count: int = Field(..., example=2)
    items: List[AlertItem]


class AlertActionResponse(BaseModel):
    status: str = Field(default="success", example="success")
    action: str = Field(..., example="ACKNOWLEDGE")
    alert_id: int = Field(..., example=1)
    message: str = Field(..., example="Alert 1 marked as ACKNOWLEDGED.")
    alert: AlertItem


class AlertProcessResponse(BaseModel):
    status: str = Field(default="success", example="success")
    location_id: int = Field(..., example=7)
    action_taken: str = Field(..., example="ALERT_CREATED")  # ALERT_CREATED, ALERT_UPDATED, ALERT_RESOLVED, NO_ALERT_REQUIRED
    alert: Optional[AlertItem] = None
    message: str = Field(..., example="High risk alert created.")
