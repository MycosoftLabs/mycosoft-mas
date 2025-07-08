"""
Mycosoft Multi-Agent System (MAS)

A distributed multi-agent system for managing and coordinating various business operations.
"""

__version__ = "0.1.0"
__author__ = "Mycosoft"
__description__ = "Mycosoft Multi-Agent System for business operations management"

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Return a minimal FastAPI application for testing."""
    app = FastAPI()

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app
