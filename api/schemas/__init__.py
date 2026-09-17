"""
API Schemas Package.
"""
from .common import HealthResponse, ErrorResponse
from .location import LocationSchema, LocationListResponse
from .weather import WeatherResponse, CurrentWeatherSchema, RainfallSchema
from .prediction import (
    PredictionResponse,
    PredictionHistoryResponse,
    PredictionHistoryItem,
)
from .alert import (
    AlertLocationInfo,
    AlertItem,
    AlertResponse,
    AlertListResponse,
    AlertActionResponse,
    AlertProcessResponse,
)

__all__ = [
    "HealthResponse",
    "ErrorResponse",
    "LocationSchema",
    "LocationListResponse",
    "WeatherResponse",
    "CurrentWeatherSchema",
    "RainfallSchema",
    "PredictionResponse",
    "PredictionHistoryResponse",
    "PredictionHistoryItem",
    "AlertLocationInfo",
    "AlertItem",
    "AlertResponse",
    "AlertListResponse",
    "AlertActionResponse",
    "AlertProcessResponse",
]

