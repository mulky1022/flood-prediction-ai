"""
Weather package for Open-Meteo integration and precipitation processing.
"""
from .weather_models import CurrentWeather, RainfallMetrics
from .weather_processor import (
    extract_current_weather,
    calculate_rainfall_7d,
    calculate_monthly_rainfall,
    get_weather_for_location,
)

__all__ = [
    "CurrentWeather",
    "RainfallMetrics",
    "extract_current_weather",
    "calculate_rainfall_7d",
    "calculate_monthly_rainfall",
    "get_weather_for_location",
]
