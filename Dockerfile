# Dockerfile for Payment Gateway API with UV native
# Multi-stage build for optimized image size
FROM python:3.14-slim AS builder

# Install UV
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy project files for UV
COPY pyproject.toml .
COPY uv.lock* .

# Create virtual environment and install dependencies with cache
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv && \
    uv sync --frozen --no-dev

# Final stage - smaller production image
FROM python:3.14-slim

# Set environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    DEBUG=false

# No system packages needed - psycopg2-binary includes its own PostgreSQL libraries

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY . .

# Create non-root user for security and fix permissions
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app/logs

# Switch to non-root user (commented for development)
# USER appuser

# Expose port (different from portal-api)
EXPOSE 8000

# Health check removed due to disk space constraints
# Can be handled at orchestration level (docker-compose/kubernetes)

# Production command with multiple workers
# Note: No alembic migration needed - uses portal-api database
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]