"""
Data structures for normalized weather variables and rainfall metrics.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class CurrentWeather:
    temperature_c: Optional[float]
    humidity_percent: Optional[float]
    precipitation_mm: Optional[float]
    rain_mm: Optional[float]
    weather_code: Optional[int]
    wind_speed_kmh: Optional[float]
    observed_at: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RainfallMetrics:
    rainfall_7d_mm: float
    monthly_rainfall_mm: float
    rainfall_7d_definition: str
    monthly_rainfall_definition: str
    rainfall_7d_status: str
    monthly_rainfall_status: str
    window_start: Optional[str]
    window_end: Optional[str]
    expected_hours: int
    received_hours: int
    missing_hours: int
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
