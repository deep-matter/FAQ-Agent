FROM python:3.11-slim as builder

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

FROM python:3.11-slim as production

RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY --from=builder /opt/venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

COPY --chown=appuser:appuser . .

RUN mkdir -p /app/db /app/logs \
    && chown -R appuser:appuser /app

USER appuser

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application with proper production settings
CMD ["python", "-m", "uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--log-level", "info", \
     "--access-log", \
     "--no-server-header"]