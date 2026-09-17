"""
Prediction Pydantic Schemas.
"""

from typing import List, Optional, Dict, Any
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
    location: LocationShortSchema
    prediction: PredictionOutputSchema
    model: ModelInfoSchema
    data_quality: DataQualityAuditSchema
    input_audit: Optional[Dict[str, Any]] = None


class PredictionHistoryItem(BaseModel):
    id: Optional[int] = None
    location_id: int
    created_at: str
    prediction_class: int
    flood_probability: float
    non_flood_probability: float
    model_name: str = "RandomForestClassifier"
    model_version: str = "1.0.0"
    data_quality_status: str = "GOOD"
    data_source: str = "Open-Meteo"


class PredictionHistoryResponse(BaseModel):
    status: str = Field(default="success")
    location_id: int
    total: int
    items: List[PredictionHistoryItem]
