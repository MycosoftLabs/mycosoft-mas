# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]





# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]





# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]








# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]





# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]





# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]









# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]





# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]





# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]








# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]





# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]





# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]











# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]





# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]




# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]



# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]





# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/mindex/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas /app/mycosoft_mas
COPY services/mindex /app/services/mindex

# Create data directories
RUN mkdir -p /app/data /mnt/nas/mindex

# Set environment variables
ENV PYTHONPATH=/app
ENV MINDEX_PORT=8000
ENV MINDEX_HOST=0.0.0.0
ENV MINDEX_NAS_PATH=/mnt/nas/mindex
ENV MINDEX_AUTO_SYNC=true
ENV MINDEX_SYNC_INTERVAL=24
ENV MINDEX_MAX_RECORDS=50000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "services.mindex.api"]


# MINDEX - Mycological Index Data System
# Dockerfile for the MINDEX fungal knowledge base service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/a