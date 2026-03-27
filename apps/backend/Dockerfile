# apps/backend/Dockerfile
# Multi-stage build: builder installs dependencies, runtime runs the app.

# ---------------------------------------------------------------------------
# Stage 1: builder – install Python dependencies into /venv
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# build-essential is needed for any C-extension wheels (e.g. psycopg2 from source)
# psycopg2-binary is used here so this is mostly a safety net.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /venv

COPY requirements.txt .
RUN /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: runtime – lean image that only contains the app and the venv
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# libmagic1 is required at runtime by python-magic (MIME byte-sniffing for file uploads)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN useradd --create-home --no-log-init appuser

WORKDIR /app

# Copy venv from builder
COPY --from=builder /venv /venv

# Copy application source
COPY . .

# Entrypoint script (runs migrations, then starts uvicorn)
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PATH="/venv/bin:$PATH"

USER appuser

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
