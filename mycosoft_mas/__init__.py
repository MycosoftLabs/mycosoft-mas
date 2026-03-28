"""
Mycosoft Multi-Agent System (MAS)

A distributed multi-agent system for managing and coordinating various business operations.
"""

__version__ = "0.1.0"
__author__ = "Mycosoft"
__description__ = "Mycosoft Multi-Agent System for business operations management"

from typing import Any

from fastapi import FastAPI, Response

from mycosoft_mas.monitoring.health_check import get_health_checker


def create_app() -> FastAPI:
    """Return a minimal FastAPI application for testing."""
    app = FastAPI()

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    @app.get("/live")
    async def live() -> dict[str, Any]:
        """Fast liveness for probes; same contract as production myca_main."""
        result = await get_health_checker().liveness()
        result["service"] = "mas"
        result["version"] = __version__
        return result

    @app.get("/metrics")
    async def metrics() -> Response:
        # Minimal Prometheus-compatible output for unit tests.
        body = 'python_info{implementation="cpython"} 1\n'
        return Response(content=body, media_type="text/plain; version=0.0.4")

    return app
