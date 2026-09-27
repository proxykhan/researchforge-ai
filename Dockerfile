# ---- Stage 1: build dependencies ----
FROM python:3.13-slim AS builder

WORKDIR /build

# Install system deps needed to compile C extensions (asyncpg, uvloop)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy everything needed to install
COPY pyproject.toml ./
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini ./

RUN pip install --no-cache-dir .


# ---- Stage 2: runtime image ----
FROM python:3.13-slim AS runtime

# libpq is needed at runtime by asyncpg/psycopg
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser

# Copy the pre-built virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source and Alembic config
WORKDIR /app
COPY --from=builder /build/src/ src/
COPY --from=builder /build/alembic/ alembic/
COPY --from=builder /build/alembic.ini ./

# Switch to non-root
USER appuser

EXPOSE 8000

# Health check — hits the liveness endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/api/v1/health"]

# Default entrypoint: API server
# Override with "worker" command in docker-compose for the worker service
CMD ["uvicorn", "researchforge.api.app:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--loop", "uvloop", "--http", "httptools"]
