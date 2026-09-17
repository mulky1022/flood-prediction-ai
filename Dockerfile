# Production Dockerfile for Sri Lanka Live Flood Early Prediction Backend
FROM python:3.11-slim

# Set working directory & environment variables
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase
COPY api/ ./api/
COPY config/ ./config/
COPY data/ ./data/
COPY database/ ./database/
COPY model/ ./model/
COPY services/ ./services/
COPY weather/ ./weather/
COPY cache/ ./cache/
COPY frontend/ ./frontend/

# Create non-root runtime user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose backend API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Launch production Uvicorn server (no --reload)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
