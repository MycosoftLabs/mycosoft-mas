# MyceliumSeg HTTP API for Petri v2 segmentation proxy (port 8051)
# Build from MAS repo root:
#   docker build -f scripts/myceliumseg/Dockerfile -t mycosoft/myceliumseg-api:v1 .
# Run (set DB URL to MINDEX Postgres):
#   docker run -d -p 8051:8051 -e MINDEX_DATABASE_URL=... mycosoft/myceliumseg-api:v1
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn pydantic "psycopg2-binary>=2.9"
COPY scripts/myceliumseg /app/scripts/myceliumseg
RUN mkdir -p /app/scripts && touch /app/scripts/__init__.py
ENV PYTHONPATH=/app
EXPOSE 8051
ENV PORT=8051
CMD ["python", "-m", "uvicorn", "scripts.myceliumseg.serve_api:app", "--host", "0.0.0.0", "--port", "8051"]
