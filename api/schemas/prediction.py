"""
Prediction Pydantic Schemas.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class LocationShortSchema(BaseModel):
    id: int = Field(..., example=7)
    district: str = Field(..., example="Ratnapura")
    place_name: str = Field(..., example="Ratnapura Town (Kalu Ganga Upper)")


class PredictionOutputSchema(BaseModel):
    prediction_class: int = Field(..., alias="class", example=1)
    flood_probability: float = Field(..., ge=0.0, le=1.0, example=0.7196)
    flood_probability_percent: Optional[float] = Field(None, example=71.96)
    non_flood_probability: float = Field(..., ge=0.0, le=1.0, example=0.2804)
    risk_level: Optional[str] = Field(default="LOW", example="HIGH")

    class Config:
        populate_by_name = True


class ModelInfoSchema(BaseModel):
    name: str = Field(default="RandomForestClassifier", example="RandomForestClassifier")
    version: str = Field(default="1.0.0", example="1.0.0")
    feature_count: int = Field(default=64, example=64)


class DataQualityAuditSchema(BaseModel):
    missing_features: List[str] = Field(default_factory=list)
    invalid_features: List[str] = Field(default_factory=list)
    unknown_categories: List[str] = Field(default_factory=list)
    weather_quality: str = Field(default="GOOD", example="GOOD")
    leakage_features_derived: List[str] = Field(default_factory=list)


class PredictionResponse(BaseModel):
    status: str = Field(default="success", example="success")
    ready_for_prediction: bool = Field(default=True, example=True)
    prediction_id: Optional[int] = Field(None, example=101)
    location: LocationShortSchema
    prediction: PredictionOutputSchema
    model: ModelInfoSchema
    data_quality: DataQualityAuditSchema
    input_audit: Optional[Dict[str, Any]] = None


class CanonicalRiskBlock(BaseModel):
    level: str = Field(..., example="HIGH")
    score: float = Field(..., ge=0.0, le=1.0, example=0.82)
    flood_probability_percent: Optional[float] = Field(None, example=82.0)


class CanonicalActionBlock(BaseModel):
    code: str = Field(..., example="PREPARE")
    message: str = Field(..., example="Prepare for possible flooding.")


class CanonicalForecastBlock(BaseModel):
    precipitation_sum_24h_mm: Optional[float] = Field(None, example=45.2)
    precipitation_sum_72h_mm: Optional[float] = Field(None, example=120.5)
    river_discharge_m3s: Optional[float] = Field(None, example=350.0)


class CanonicalLocationBlock(BaseModel):
    location_id: int = Field(..., example=7)
    record_id: Optional[str] = Field(None, example="LOC-007")
    name: str = Field(..., example="Ratnapura")
    district: str = Field(..., example="Ratnapura")
    latitude: Optional[float] = Field(None, example=6.6828)
    longitude: Optional[float] = Field(None, example=80.3992)


class CanonicalPredictionResponse(BaseModel):
    prediction_id: Optional[int] = Field(None, example=101)
    location: CanonicalLocationBlock
    prediction_time: str = Field(..., example="2026-09-18T08:00:00Z")
    valid_from: str = Field(..., example="2026-09-18T08:00:00Z")
    valid_until: str = Field(..., example="2026-09-18T20:00:00Z")
    is_stale: bool = Field(default=False, example=False)
    risk: CanonicalRiskBlock
    forecast: Optional[CanonicalForecastBlock] = None
    confidence: float = Field(default=0.90, ge=0.0, le=1.0, example=0.91)
    action: Optional[CanonicalActionBlock] = None
    conditions: Optional[Dict[str, Any]] = None
    model: ModelInfoSchema = Field(default_factory=ModelInfoSchema)
    status: str = Field(default="CURRENT", example="CURRENT")


class MapPredictionItem(BaseModel):
    location_id: int = Field(..., example=7)
    record_id: Optional[str] = Field(None, example="LOC-007")
    name: Optional[str] = Field(None, example="Ratnapura")
    district: Optional[str] = Field(None, example="Ratnapura")
    latitude: Optional[float] = Field(None, example=6.6828)
    longitude: Optional[float] = Field(None, example=80.3992)
    prediction_id: Optional[int] = Field(None, example=101)
    prediction_time: Optional[str] = Field(None, example="2026-09-18T08:00:00Z")
    risk_level: str = Field(default="LOW", example="HIGH")
    flood_probability: float = Field(default=0.0, example=0.82)
    action_code: Optional[str] = Field(default="SAFE", example="PREPARE")
    action_message: Optional[str] = Field(default="Normal conditions.", example="Prepare emergency supplies.")
    status: str = Field(default="CURRENT", example="CURRENT")


class MapPredictionResponse(BaseModel):
    status: str = Field(default="success")
    total: int = Field(..., example=33)
    predictions: List[MapPredictionItem]


class PredictionHistoryItem(BaseModel):
    id: Optional[Union[int, str]] = None
    prediction_id: Optional[Union[int, str]] = None
    location_id: int = Field(..., example=7)
    created_at: str = Field(..., example="2026-09-18T08:00:00+05:30")
    prediction_time: Optional[str] = Field(None, example="2026-09-18T08:00:00+05:30")
    valid_from: Optional[str] = Field(None, example="2026-09-18T08:00:00+05:30")
    valid_until: Optional[str] = Field(None, example="2026-09-18T20:00:00+05:30")
    prediction_class: int = Field(..., example=1)
    flood_probability: float = Field(..., ge=0.0, le=1.0, example=0.75)
    flood_probability_percent: Optional[float] = Field(None, example=75.0)
    non_flood_probability: float = Field(default=0.25, ge=0.0, le=1.0, example=0.25)
    risk_level: Optional[str] = Field(default="LOW", example="HIGH")
    action_code: Optional[str] = Field(None, example="PREPARE")
    action_message: Optional[str] = Field(None, example="Prepare emergency supplies and monitor local water levels.")
    confidence: Optional[float] = Field(default=0.90, example=0.90)
    model_name: str = Field(default="RandomForestClassifier", example="RandomForestClassifier")
    model_version: str = Field(default="1.0.0", example="1.0.0")
    data_quality_status: str = Field(default="GOOD", example="GOOD")
    data_source: str = Field(default="Open-Meteo", example="Open-Meteo")
    status: str = Field(default="RECORDED", example="RECORDED")


class PredictionHistoryResponse(BaseModel):
    status: str = Field(default="success", example="success")
    location_id: int = Field(..., example=7)
    total: int = Field(..., example=15)
    limit: int = Field(default=50, example=50)
    offset: int = Field(default=0, example=0)
    has_more: bool = Field(default=False, example=False)
    items: List[PredictionHistoryItem]
