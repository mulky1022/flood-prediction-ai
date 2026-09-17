"""
Alert Preferences & Triggered Alerts Schemas.
"""

from typing import List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field


class AlertPreferenceBase(BaseModel):
    device_id: str = Field(..., description="Unique client device or session identifier")
    location_id: Optional[int] = Field(None, description="Monitored station ID (null = all 33 stations)")
    risk_threshold: float = Field(35.0, ge=0.0, le=100.0, description="Flood probability threshold in percent")
    notification_channels: List[str] = Field(default_factory=lambda: ["in_app"], description="Enabled notification channels")
    is_active: bool = Field(True, description="Whether this preference is currently active")


class AlertPreferenceCreate(AlertPreferenceBase):
    pass


class AlertPreferenceUpdate(BaseModel):
    location_id: Optional[int] = Field(None, description="Monitored station ID (null = all 33 stations)")
    risk_threshold: Optional[float] = Field(None, ge=0.0, le=100.0)
    notification_channels: Optional[List[str]] = None
    is_active: Optional[bool] = None


class AlertPreferenceItem(AlertPreferenceBase):
    id: int
    location_name: Optional[str] = None
    district: Optional[str] = None
    created_at: str
    updated_at: str


class AlertPreferenceResponse(BaseModel):
    status: str = "success"
    preference: AlertPreferenceItem


class AlertPreferenceListResponse(BaseModel):
    status: str = "success"
    total: int
    items: List[AlertPreferenceItem]


class TriggeredAlertItem(BaseModel):
    id: int
    preference_id: Optional[int] = None
    device_id: Optional[str] = None
    location_id: int
    location_name: Optional[str] = None
    district: Optional[str] = None
    prediction_id: Optional[int] = None
    flood_probability: float
    flood_probability_percent: float
    risk_level: str
    threshold_crossed: float
    title: str
    message: str
    status: str = "UNREAD"
    created_at: str


class TriggeredAlertListResponse(BaseModel):
    status: str = "success"
    total: int
    unread_count: int
    items: List[TriggeredAlertItem]


class TriggeredAlertActionResponse(BaseModel):
    status: str = "success"
    alert_id: int
    action: str
    message: str
