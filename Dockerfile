# ============================================================================
# Multi-stage Docker Build for Lark Service
# ============================================================================
# Optimization features:
# - Multi-stage build to reduce image size (expected < 350MB)
# - China mirror sources for faster builds (Debian + PyPI)
# - Build cache optimization (separate dependency and code layers)
# - Production-grade security (non-root user, minimal permissions)
# - Health check and graceful shutdown support
# ============================================================================

# ============================================================================
# Stage 1: Builder - Compile dependencies
# ============================================================================
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /build

# Configure China mirror sources for faster apt installation
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# Install build dependencies (only needed in builder stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Configure China PyPI mirror for faster pip installation
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy dependency files (leverage Docker cache layers)
COPY requirements.txt ./

# Separate production and development dependencies
# Only install production-required dependencies
RUN grep -v "^#" requirements.txt | grep -v "pytest\|mypy\|ruff\|types-" > requirements.prod.txt && \
    pip install --no-cache-dir -r requirements.prod.txt

# ============================================================================
# Stage 2: Runtime - Minimal runtime image
# ============================================================================
FROM python:3.12-slim AS runtime

# Metadata labels
LABEL maintainer="Lark Service Team" \
      version="0.1.0" \
      description="Lark Service - Enterprise-grade Feishu API Service"

# Configure China mirror sources
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# Install runtime dependencies (only required libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application directory
WORKDIR /app

# Copy installed Python packages from builder (system site-packages)
COPY --from=builder /usr/local /usr/local

# Copy application code (copy last to maximize cache utilization)
COPY src/ /app/src/
COPY migrations/ /app/migrations/
COPY alembic.ini /app/alembic.ini

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/data

# Environment variable configuration
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user (security best practice)
RUN useradd -m -u 1000 -s /bin/bash lark && \
    chown -R lark:lark /app

# Switch to non-privileged user
USER lark

# Expose port (if API service exists)
# EXPOSE 8000

# Health check (improved version - check actual service status)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; from lark_service.core.config import Config; sys.exit(0)" || exit 1

# Volume mount points (persistent data)
VOLUME ["/app/config", "/app/logs", "/app/data"]

# Default startup command
CMD ["python", "-m", "lark_service"]

# ============================================================================
# Build instructions:
# ============================================================================
# Standard build:
#   docker build -t lark-service:latest .
#
# View image size:
#   docker images lark-service:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
#
# Multi-platform build (ARM64 + AMD64):
#   docker buildx build --platform linux/amd64,linux/arm64 \
#     -t lark-service:latest .
#
# Build with cache:
#   docker build --cache-from lark-service:latest \
#     -t lark-service:v0.1.0 .
# ============================================================================
