"""
Weather Pydantic Schemas.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class CurrentWeatherSchema(BaseModel):
    temperature_c: Optional[float] = Field(None, example=23.8)
    humidity_percent: Optional[float] = Field(None, example=98.0)
    precipitation_mm: Optional[float] = Field(None, example=0.0)
    rain_mm: Optional[float] = Field(None, example=0.0)
    weather_code: Optional[int] = Field(None, example=3)
    wind_speed_kmh: Optional[float] = Field(None, example=5.3)
    observed_at: Optional[str] = Field(None, example="2026-09-16T22:45")


class RainfallSchema(BaseModel):
    rainfall_7d_mm: float = Field(..., example=114.5)
    monthly_rainfall_mm: float = Field(..., example=248.4)
    rainfall_7d_definition: str = Field(..., example="rolling_168_hourly_precipitation_sum")
    monthly_rainfall_definition: str = Field(..., example="rolling_30_days_daily_precipitation_sum")
    rainfall_7d_status: str = Field(..., example="VERIFIED")
    monthly_rainfall_status: str = Field(..., example="PROVISIONAL")
    window_start: Optional[str] = Field(None, example="2026-09-10T22:00")
    window_end: Optional[str] = Field(None, example="2026-09-17T21:00")
    expected_hours: int = Field(168, example=168)
    received_hours: int = Field(168, example=168)
    missing_hours: int = Field(0, example=0)
    data_quality: str = Field(default="GOOD", example="GOOD")


class WeatherLocationSchema(BaseModel):
    id: int = Field(..., example=7)
    district: str = Field(..., example="Ratnapura")
    place_name: str = Field(..., example="Ratnapura Town (Kalu Ganga Upper)")
    latitude: float = Field(..., example=6.6828)
    longitude: float = Field(..., example=80.4036)


class WeatherResponse(BaseModel):
    status: str = Field(default="success")
    location: WeatherLocationSchema
    current: CurrentWeatherSchema
    rainfall: RainfallSchema
    source: Dict[str, Any]
