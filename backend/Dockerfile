# =============================================================================
# EcoMind Backend - Production Dockerfile
# Multi-stage / lightweight Python 3.10 slim base
# =============================================================================

FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install minimal OS dependencies for network health checks, OpenMP, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user and persistent database directory
RUN groupadd -g 1000 ecomind && \
    useradd -u 1000 -g ecomind -m -s /bin/bash ecomind && \
    mkdir -p /app/database && \
    chown -R ecomind:ecomind /app

# Copy dependency specifications first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY --chown=ecomind:ecomind . .

# Ensure proper permissions on application directory and SQLite storage
RUN chown -R ecomind:ecomind /app

# Switch to non-root user for runtime security
USER ecomind

# Expose FastAPI backend port
EXPOSE 8000

# Health check to ensure the API is responding
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Production command to start FastAPI with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

