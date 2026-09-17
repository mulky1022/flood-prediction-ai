"""
Client Configuration Route.
Exposes public client-side runtime configuration (e.g. CARTO Basemap API key)
without exposing any sensitive backend secrets or credentials.
"""

import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Config"])


class ClientConfigResponse(BaseModel):
    status: str = "ok"
    carto_api_key: str = ""
    app_env: str = "production"
    version: str = "1.0.0"


@router.get("/config", response_model=ClientConfigResponse)
def get_client_config():
    """
    Returns public client-side configuration.
    Safely retrieves the CARTO API key configured in backend environment.
    """
    carto_key = (
        os.getenv("CARTO_API_KEY") or
        os.getenv("VITE_CARTO_API_KEY") or
        os.getenv("NEXT_PUBLIC_CARTO_API_KEY") or
        ""
    ).strip()

    return ClientConfigResponse(
        status="ok",
        carto_api_key=carto_key,
        app_env=os.getenv("APP_ENV", "development"),
        version=os.getenv("APP_VERSION", "1.0.0")
    )
