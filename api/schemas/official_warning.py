"""
Pydantic Schemas for Official Government Warnings.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class OfficialWarningItem(BaseModel):
    id: Optional[int] = Field(None, example=1)
    warning_id: str = Field(..., example="TEST-WARN-RAT-001")
    location_id: int = Field(..., example=7)
    source_id: str = Field(default="DMC-SL", example="DMC-SL")
    source_name: str = Field(default="Disaster Management Centre (DMC) Sri Lanka", example="Disaster Management Centre (DMC) Sri Lanka")
    source_type: str = Field(default="GOVERNMENT_AGENCY", example="GOVERNMENT_AGENCY")
    source_url: Optional[str] = Field(None, example="https://www.dmc.gov.lk/warnings/2026-ratnapura")
    official_reference: Optional[str] = Field(None, example="DMC/FL/2026/09/18/RAT01")
    warning_type: str = Field(default="FLOOD_WARNING", example="FLOOD_WARNING")
    severity: str = Field(default="MAJOR", example="MAJOR")
    title: str = Field(..., example="Official Flood Warning — Kalu Ganga Basin (Ratnapura)")
    message: str = Field(..., example="Irrigation Dept & DMC report severe river overflow risk. Evacuate low-lying areas.")
    issued_at: str
    valid_from: str
    valid_until: str
    status: str = Field(default="ACTIVE", example="ACTIVE")
    language: str = Field(default="en", example="en")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class OfficialWarningCurrentResponse(BaseModel):
    status: str = Field(default="success", example="success")
    state: str = Field(..., example="ACTIVE")  # ACTIVE, NO_ACTIVE_WARNING, EXPIRED, UNAVAILABLE
    location_id: int = Field(..., example=7)
    location_name: Optional[str] = Field(None, example="Ratnapura Town (Kalu Ganga Upper)")
    district: Optional[str] = Field(None, example="Ratnapura")
    warning: Optional[OfficialWarningItem] = None
    message: str = Field(..., example="Active official government warning found.")


class OfficialWarningListResponse(BaseModel):
    status: str = Field(default="success", example="success")
    total: int = Field(..., example=1)
    location_id: int = Field(..., example=7)
    warnings: List[OfficialWarningItem]


class OfficialWarningIngestRequest(BaseModel):
    warning_id: Optional[str] = Field(None, example="WARN-DMC-2026-001")
    location_id: int = Field(..., example=7)
    source_id: Optional[str] = Field("DMC-SL", example="DMC-SL")
    source_name: Optional[str] = Field("Disaster Management Centre (DMC) Sri Lanka", example="Disaster Management Centre (DMC) Sri Lanka")
    source_type: Optional[str] = Field("GOVERNMENT_AGENCY", example="GOVERNMENT_AGENCY")
    source_url: Optional[str] = Field(None, example="https://www.dmc.gov.lk/warnings/2026-001")
    official_reference: Optional[str] = Field(None, example="DMC/FL/2026/09/18/01")
    warning_type: Optional[str] = Field("FLOOD_WARNING", example="FLOOD_WARNING")
    severity: Optional[str] = Field("MAJOR", example="MAJOR")
    title: str = Field(..., example="Official Flood Warning")
    message: str = Field(..., example="Severe flood warning issued by DMC.")
    issued_at: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: str = Field(..., example="2026-09-19T12:00:00+05:30")
    status: Optional[str] = Field("ACTIVE", example="ACTIVE")
    language: Optional[str] = Field("en", example="en")
