# Security Architecture & Controls

## 1. Zero Client Secrets Policy
- Privileged keys (e.g. `SUPABASE_SERVICE_ROLE_KEY`, database passwords) are strictly confined to backend execution environments.
- Frontend scripts communicate exclusively via same-origin `/api/v1/...` REST endpoints. Zero secrets are compiled or exposed in static JavaScript bundles.

---

## 2. API Gateway Security & Middleware
- **Security Headers Middleware (`api/middleware/security.py`)**: Enforces `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, and `Referrer-Policy`.
- **CORS Policy (`FRONTEND_ORIGIN`)**: Restricts cross-origin HTTP requests to authorized domain origins.
- **Rate Limiting (`RateLimiterMiddleware`)**: Enforces rate limits per client IP across critical API route categories (`/api/v1/emergency`, `/api/v1/notifications`, `/api/v1/admin`, `/api/v1/predictions`).
- **Correlation ID Tracking (`CorrelationIdMiddleware`)**: Attaches unique `X-Request-ID` headers to every incoming HTTP request for audit logging and request tracing.

---

## 3. Data Privacy & Phone Masking
- Recipient phone numbers for alert delivery are normalized to E.164 format (`+94771234567`) and masked for privacy (`+9477****567`). No plaintext phone numbers are exposed in public logs.
