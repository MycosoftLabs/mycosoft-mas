"""
Mycosoft Multi-Agent System (MAS)

A distributed multi-agent system for managing and coordinating various business operations.
"""

__version__ = "0.1.0"
__author__ = "Mycosoft"
__description__ = "Mycosoft Multi-Agent System for business operations management"

from fastapi import FastAPI, Response


def create_app() -> FastAPI:
    """Return a minimal FastAPI application for testing."""
    app = FastAPI()

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    @app.get("/metrics")
    async def metrics() -> Response:
        # Minimal Prometheus-compatible output for unit tests.
        body = "python_info{implementation=\"cpython\"} 1\n"
        return Response(content=body, media_type="text/plain; version=0.0.4")

    return app
