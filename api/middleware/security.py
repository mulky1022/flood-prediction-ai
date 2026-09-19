"""
Phase 19 — Security & Reliability Middleware.

Provides:
1. Request Correlation ID middleware (`X-Request-ID`) attached to every request and response.
2. Security Headers middleware enforcing `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and `Content-Security-Policy`.
3. Sliding-window Rate Limiting & Abuse Prevention middleware differentiating Public, Emergency, Subscription/OTP, and Admin endpoints.
"""

import time
import uuid
import logging
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger("SecurityMiddleware")

# Rate limit thresholds (requests per window_seconds)
RATE_LIMIT_CONFIG = {
    "/api/v1/emergency": {"limit": 120, "window": 60},      # High limit so flood victims are never blocked
    "/api/v1/notifications": {"limit": 10, "window": 60},    # Strict limit to prevent SMS/WhatsApp billing abuse
    "/api/v1/admin": {"limit": 30, "window": 60},            # Admin rate limit
    "/api/v1/predictions": {"limit": 60, "window": 60},      # Standard public predictions read
    "DEFAULT": {"limit": 100, "window": 60}
}


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Assigns or passes through a unique X-Request-ID correlation header for every request.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or f"REQ-{uuid.uuid4().hex[:12].upper()}"
        request.state.request_id = req_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects production security headers into all HTTP responses.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window Rate Limiting & Abuse Prevention middleware per IP and route prefix.
    """
    def __init__(self, app):
        super().__init__(app)
        # Structure: {(ip, route_category): [timestamp1, timestamp2, ...]}
        self.request_history: Dict[Tuple[str, str], List[float]] = {}

    def _get_route_category(self, path: str) -> str:
        for prefix in ("/api/v1/emergency", "/api/v1/notifications", "/api/v1/admin", "/api/v1/predictions"):
            if path.startswith(prefix):
                return prefix
        return "DEFAULT"

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "127.0.0.1"
        path = request.url.path
        category = self._get_route_category(path)
        
        config = RATE_LIMIT_CONFIG.get(category, RATE_LIMIT_CONFIG["DEFAULT"])
        max_requests = config["limit"]
        window = config["window"]

        now = time.time()
        key = (client_ip, category)

        # Cleanup old timestamps
        timestamps = self.request_history.get(key, [])
        timestamps = [t for t in timestamps if now - t < window]

        if len(timestamps) >= max_requests:
            req_id = getattr(request.state, "request_id", f"REQ-{uuid.uuid4().hex[:12].upper()}")
            logger.warning(f"Rate limit exceeded for IP {client_ip} on category '{category}' ({path})")
            return JSONResponse(
                status_code=429,
                content={
                    "status": "error",
                    "code": "TOO_MANY_REQUESTS",
                    "message": f"Rate limit exceeded for {category}. Maximum {max_requests} requests per {window}s.",
                    "request_id": req_id
                },
                headers={"Retry-After": str(window), "X-Request-ID": req_id}
            )

        timestamps.append(now)
        self.request_history[key] = timestamps

        return await call_next(request)
