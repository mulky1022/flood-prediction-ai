"""
Client Configuration Route.
Exposes public client-side runtime configuration
without exposing any sensitive backend secrets or credentials.
"""

import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Config"])


class ClientConfigResponse(BaseModel):
    status: str = "ok"
    app_env: str = "production"
    version: str = "1.0.0"
    map_provider: str = "Humanitarian OpenStreetMap (HOT) & OpenStreetMap Standard"


@router.get("/config", response_model=ClientConfigResponse)
def get_client_config():
    """
    Returns public client-side runtime configuration.
    """
    return ClientConfigResponse(
        status="ok",
        app_env=os.getenv("APP_ENV", "production"),
        version=os.getenv("APP_VERSION", "1.0.0"),
        map_provider="Humanitarian OpenStreetMap (HOT) & OpenStreetMap Standard"
    )

