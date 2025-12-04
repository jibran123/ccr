# Multi-Stage Dockerfile for Common Configuration Repository (CCR)
# Optimized for CI/CD pipeline with security best practices

# ============================================================
# STAGE 1: Base Python Image with Security Updates
# ============================================================
FROM python:3.11-slim AS base

# Install security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# ============================================================
# STAGE 2: Build Stage - Install Dependencies
# ============================================================
FROM base AS builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# ============================================================
# STAGE 3: Runtime Stage - Final Image
# ============================================================
FROM base AS runtime

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health/live || exit 1

# Switch to non-root user
USER appuser

# Run application
CMD ["python", "run.py"]

# Labels for metadata (OCI standard)
LABEL org.opencontainers.image.title="Common Configuration Repository (CCR)" \
      org.opencontainers.image.description="Internal operations tool for managing API deployments" \
      org.opencontainers.image.vendor="Your Company" \
      org.opencontainers.image.authors="Jibran Patel <jibran@yourcompany.com>" \
      org.opencontainers.image.source="https://github.com/yourcompany/ccr" \
      org.opencontainers.image.documentation="https://github.com/yourcompany/ccr/blob/main/README.md"
