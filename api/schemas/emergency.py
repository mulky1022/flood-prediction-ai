"""
Pydantic Schemas for Emergency & Low-Bandwidth API.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class EmergencyLocationBlock(BaseModel):
    id: str = Field(..., example="RATNAPURA_001")
    name: str = Field(..., example="Ratnapura")
    district: str = Field(..., example="Ratnapura")
    province: str = Field(..., example="Sabaragamuwa")


class EmergencyPredictionBlock(BaseModel):
    prediction_id: Optional[str] = Field(None, example="PRED-RAT-001")
    risk_level: str = Field(..., example="HIGH")
    prediction_time: Optional[str] = Field(None, example="2026-09-18T10:00:00+00:00")
    valid_from: Optional[str] = Field(None, example="2026-09-18T10:00:00+00:00")
    valid_until: Optional[str] = Field(None, example="2026-09-18T22:00:00+00:00")
    freshness_status: str = Field("CURRENT", example="CURRENT")


class EmergencyActionBlock(BaseModel):
    code: str = Field(..., example="PREPARE")
    message: str = Field(..., example="Prepare emergency supplies and move valuables to high ground.")


class EmergencyOfficialWarningBlock(BaseModel):
    warning_id: Optional[str] = Field(None, example="DMC-WARN-RAT-001")
    status: str = Field("NONE", example="ACTIVE")
    source_name: Optional[str] = Field(None, example="Disaster Management Centre (DMC) Sri Lanka")
    source_url: Optional[str] = Field(None, example="https://www.dmc.gov.lk")
    title: Optional[str] = Field(None, example="Official Flood Warning")
    message: Optional[str] = Field(None, example="Severe flood warning issued.")
    issued_at: Optional[str] = Field(None, example="2026-09-18T11:00:00+05:30")
    valid_until: Optional[str] = Field(None, example="2026-09-19T11:00:00+05:30")


class EmergencyInfoBlock(BaseModel):
    hotline: str = Field("117", example="117")
    hotline_name: str = Field("Disaster Management Centre Hotline", example="Disaster Management Centre Hotline")
    hotline_url: str = Field("tel:117", example="tel:117")
    safety_guidance: str = Field(
        "In case of sudden flooding, move immediately to higher ground. Keep emergency supplies ready and call DMC Hotline 117.",
        example="In case of sudden flooding, move immediately to higher ground."
    )


class EmergencyDataResponse(BaseModel):
    status: str = Field("success", example="success")
    location: EmergencyLocationBlock
    prediction: Optional[EmergencyPredictionBlock] = None
    action: Optional[EmergencyActionBlock] = None
    official_warning: Optional[EmergencyOfficialWarningBlock] = None
    emergency: EmergencyInfoBlock = Field(default_factory=EmergencyInfoBlock)
    timestamp: str = Field(..., example="2026-09-18T20:30:00+05:30")
