"""
Location Pydantic Schemas.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LocationSchema(BaseModel):
    id: int = Field(..., example=7)
    record_id: str = Field(..., example="LOC-007")
    district: str = Field(..., example="Ratnapura")
    place_name: str = Field(..., example="Ratnapura Town (Kalu Ganga Upper)")
    latitude: float = Field(..., example=6.6828)
    longitude: float = Field(..., example=80.4036)
    elevation_m: Optional[float] = Field(None, example=34.0)
    distance_to_river_m: Optional[float] = Field(None, example=110.0)
    population_density_per_km2: Optional[float] = Field(None, example=920.0)
    built_up_percent: Optional[float] = Field(None, example=52.0)
    drainage_index: Optional[float] = Field(None, example=0.26)
    ndvi: Optional[float] = Field(None, example=0.28)
    ndwi: Optional[float] = Field(None, example=0.31)
    historical_flood_count: Optional[float] = Field(None, example=9.0)
    infrastructure_score: Optional[float] = Field(None, example=48.0)
    nearest_hospital_km: Optional[float] = Field(None, example=2.1)
    nearest_evac_km: Optional[float] = Field(None, example=1.0)
    landcover: Optional[str] = Field(None, example="Urban")
    soil_type: Optional[str] = Field(None, example="Silty")
    water_supply: Optional[str] = Field(None, example="Surface water")
    electricity: Optional[str] = Field(None, example="Mixed")
    road_quality: Optional[str] = Field(None, example="Good (paved)")
    urban_rural: Optional[str] = Field(None, example="Urban")
    water_presence_flag: Optional[str] = Field(None, example="Likely")


class LocationListResponse(BaseModel):
    status: str = Field(default="success")
    total: int = Field(..., example=33)
    locations: List[LocationSchema]


class LocationDetailsResponse(BaseModel):
    status: str = Field(default="success", example="success")
    location: LocationSchema
    current_prediction: Optional[Dict[str, Any]] = None
    active_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    recent_history: List[Dict[str, Any]] = Field(default_factory=list)
    official_warning: Optional[Dict[str, Any]] = None
    status_flag: str = Field(default="CURRENT", example="CURRENT")  # CURRENT, STALE, NO_CURRENT_PREDICTION, ERROR


