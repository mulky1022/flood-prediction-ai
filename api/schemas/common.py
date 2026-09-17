"""
Common Pydantic Schemas for API responses and errors.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", example="ok")
    service: str = Field(default="Sri Lanka FloodWatch API", example="Sri Lanka FloodWatch API")
    version: str = Field(default="1.0.0", example="1.0.0")
    model_loaded: bool = Field(default=True, example=True)
    database_connected: bool = Field(default=False, example=False)


class ErrorResponse(BaseModel):
    status: str = Field(default="error", example="error")
    code: str = Field(..., example="LOCATION_NOT_FOUND")
    message: str = Field(..., example="Location ID not found.")
    details: Optional[Any] = None
