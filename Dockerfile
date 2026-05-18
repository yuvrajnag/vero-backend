# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Builder
#   Compiles native extensions (psycopg2, numpy, scikit-learn, etc.) in an
#   isolated layer so the final image stays lean.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# System libs needed to compile wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libpq-dev \
        libffi-dev \
        libssl-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies into a dedicated prefix so we can copy cleanly
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Runtime
#   Minimal image: only the installed packages + application code.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="vero-backend"
LABEL org.opencontainers.image.description="Vero AI Tech Backend — FastAPI + pgvector"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Put installed packages on the path
    PYTHONPATH="/app" \
    PATH="/install/bin:$PATH"

# Runtime system libs (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled wheels from builder
COPY --from=builder /install /usr/local

# Create a non-root user for security
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy application code (respects .dockerignore)
COPY --chown=appuser:appgroup . .

# Ensure uploads dir exists and is writable
RUN mkdir -p /app/uploads && chown -R appuser:appgroup /app/uploads

USER appuser

# Render injects $PORT at runtime — default 8000 for local testing
EXPOSE 8000

# Healthcheck — Render uses /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# ── Entrypoint ────────────────────────────────────────────────────────────────
# Workers = (2 × CPU cores) + 1  →  1 worker is fine on Render free/starter
# Use $PORT so Render's dynamic port injection works automatically.
CMD uvicorn app.main:app \
        --host 0.0.0.0 \
        --port ${PORT:-8000} \
        --workers 1 \
        --loop uvloop \
        --http httptools \
        --log-level info \
        --no-access-log
