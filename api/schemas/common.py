"""
Common Pydantic Schemas for API responses, errors, and input sanitization.
"""

import re
from typing import Optional, Any
from pydantic import BaseModel, Field


def sanitize_input_string(value: str, max_length: int = 255) -> str:
    """
    Sanitizes external user/query strings against XSS and SQL injection.
    Strips HTML tags and dangerous SQL chars. Truncates to max_length.
    """
    if not value:
        return ""
    # Strip HTML tags
    clean = re.sub(r"<[^>]*>", "", value.strip())
    # Strip dangerous SQL characters
    clean = re.sub(r"['\";=]", "", clean)
    return clean[:max_length]


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
    request_id: Optional[str] = Field(None, example="REQ-A1B2C3D4E5F6")
    details: Optional[Any] = None
