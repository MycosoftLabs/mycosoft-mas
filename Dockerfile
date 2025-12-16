# === build stage ===
FROM python:3.11-slim AS build

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    POETRY_VERSION=1.7.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PATH="/root/.local/bin:$PATH"

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libpq-dev \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set working directory
WORKDIR /app

# Copy Poetry files
COPY pyproject.toml ./

# Install dependencies
RUN poetry install --no-dev --no-root

# Copy application code
COPY . .

# Install the application
RUN poetry install --no-dev

# === runtime stage ===
FROM python:3.11-slim AS runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:/usr/bin:/bin:/usr/local/lib/python3.11/site-packages:$PATH"

# Install runtime system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        netcat-openbsd \
        postgresql-client \
        curl \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy from builder (includes Python packages and scripts)
COPY --from=build /app /app
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

# Convert CRLF to LF and UTF-16 to UTF-8 in Python files
RUN apt-get update && apt-get install -y --no-install-recommends dos2unix && \
    find /app -name "*.py" -type f -exec sh -c 'file "$1" | grep -q "UTF-16" && iconv -f UTF-16LE -t UTF-8 "$1" > "$1.tmp" && mv "$1.tmp" "$1"' _ {} \; && \
    find /app -name "*.py" -type f -exec dos2unix {} \; && \
    apt-get purge -y dos2unix && rm -rf /var/lib/apt/lists/*

# Copy wait-for-it script (after bin copy to ensure it's present)
COPY scripts/wait-for-it.sh /usr/local/bin/wait-for-it
RUN chmod +x /usr/local/bin/wait-for-it

# Create necessary directories
RUN mkdir -p /app/logs /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "mycosoft_mas.core.main:app", "--host", "0.0.0.0", "--port", "8000"] 