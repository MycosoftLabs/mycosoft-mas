"""
NatureOS Integration Client

Client for NatureOS Full Cloud Platform API including MATLAB analysis endpoints.
Used by MAS agents for anomaly detection, forecasting, classification, and analytics.

Environment Variables:
    NATUREOS_API_URL: NatureOS backend base URL (e.g. http://192.168.0.187:5000)
    NATUREOS_API_BASE_URL: Alternative env var for same purpose

Usage:
    from mycosoft_mas.integrations.natureos_client import NATUREOSClient

    client = NATUREOSClient()
    result = await client.run_anomaly_detection(device_id="mushroom1")
    forecast = await client.forecast_environmental(metric="temperature", hours=24)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class NATUREOSClient:
    """
    Client for NatureOS API including MATLAB-driven analysis endpoints.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        self.base_url = (
            base_url
            or os.environ.get("NATUREOS_API_URL")
            or os.environ.get("NATUREOS_API_BASE_URL")
            or "http://192.168.0.187:5000"
        ).rstrip("/")
        self.timeout = timeout

    async def _post(
        self, path: str, json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=json or {})
            response.raise_for_status()
            return response.json()

    async def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def run_anomaly_detection(self, device_id: str) -> Dict[str, Any]:
        """Run anomaly detection on device telemetry via MATLAB."""
        return await self._post(
            "/api/Matlab/anomaly-detection",
            json={"deviceId": device_id},
        )

    async def forecast_environmental(
        self, metric: str, hours: int = 24
    ) -> Dict[str, Any]:
        """Environmental forecasting via MATLAB (temperature, humidity, etc.)."""
        return await self._post(
            "/api/Matlab/forecast",
            json={"metric": metric, "horizonHours": hours},
        )

    async def classify_morphology(
        self, signal_vector: List[float]
    ) -> Dict[str, Any]:
        """Fungal morphology classification from signal vector via MATLAB."""
        return await self._post(
            "/api/Matlab/classification",
            json={"signalVector": signal_vector},
        )

    async def anomaly_detection_timeseries(
        self, time_series: List[float]
    ) -> Dict[str, Any]:
        """Run anomaly detection on raw time series data."""
        return await self._post(
            "/api/Matlab/anomaly-detection",
            json={"timeSeries": time_series},
        )

    async def generate_visualization(
        self, plot_type: str, data: Dict[str, Any]
    ) -> bytes:
        """Generate plot image from MATLAB."""
        url = f"{self.base_url}/api/Matlab/visualization"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json={"plotType": plot_type, "data": data},
            )
            response.raise_for_status()
            return response.content

    async def execute_analysis(
        self, function_name: str, args: List[Any]
    ) -> Dict[str, Any]:
        """Execute named MATLAB analysis function."""
        return await self._post(
            f"/api/Matlab/analysis/{function_name}",
            json={"args": args},
        )

    async def get_matlab_health(self) -> Dict[str, Any]:
        """Get MATLAB engine status."""
        return await self._get("/api/Matlab/health")
