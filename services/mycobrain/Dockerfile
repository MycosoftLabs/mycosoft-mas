# MycoBrain Service - Docker Container
# Manages serial communication with MycoBrain hardware devices
#
# Note: On Windows, COM ports can't be directly accessed from Docker.
# Options:
#   1. Use host networking and run on Linux
#   2. Use ser2net to bridge COM to TCP
#   3. Run this container but point to host-based serial service
#
# Usage:
#   docker build -t mycobrain-service .
#   docker run -p 8003:8003 mycobrain-service

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycobrain_service_standalone.py ./
COPY __init__.py ./

# Create directories for logs
RUN mkdir -p /app/logs

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV MYCOBRAIN_PORT=8003
ENV MYCOBRAIN_HOST=0.0.0.0
ENV DEFAULT_SERIAL_PORT=COM5
ENV BAUD_RATE=115200

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the service
CMD ["python", "mycobrain_service_standalone.py"]
