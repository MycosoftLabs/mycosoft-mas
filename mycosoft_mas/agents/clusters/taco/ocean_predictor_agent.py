"""Ocean Predictor Agent — TAC-O Maritime Integration

Forecasts environmental conditions using NLM NextStatePredictionHead
and SonarPerformancePredictionHead. Feeds sonar performance predictions
to operators and ingests NOAA/NCEP data via Worldview maritime endpoints.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class OceanPredictorAgent(BaseAgent):
    """Forecasts ocean conditions and predicts sonar performance."""

    def __init__(self, agent_id: str = "taco-ocean-predictor", name: str = "Ocean Predictor", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = [
            "ocean_forecast",
            "sonar_performance_prediction",
            "environmental_assessment",
        ]
        self.cluster = "taco"
        self.worldview_endpoint = self.config.get(
            "worldview_endpoint",
            "http://192.168.0.189:8000/api/mindex/maritime/ocean-environments",
        )
        self.sonar_endpoint = self.config.get(
            "sonar_endpoint",
            "http://192.168.0.189:8000/api/mindex/nlm/predict/sonar-performance",
        )
        self.internal_token = os.getenv("MINDEX_INTERNAL_TOKEN", "").strip()
        self.api_key = os.getenv("MINDEX_API_KEY", "").strip()

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        if task_type == "predict_sonar_performance":
            return await self._predict_sonar(task)
        elif task_type == "forecast_environment":
            return await self._forecast_environment(task)
        return {"status": "error", "message": f"Unknown task type: {task_type}"}

    async def _predict_sonar(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Predict sonar detection ranges for current environment."""
        location = task.get("location", {})
        logger.info("Sonar performance prediction at (%.4f, %.4f)", location.get("lat", 0), location.get("lon", 0))
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                headers = {"X-Internal-Token": self.internal_token} if self.internal_token else {"X-API-Key": self.api_key} if self.api_key else None
                response = await client.post(self.sonar_endpoint, json=task.get("environment", task), headers=headers)
                response.raise_for_status()
                prediction = response.json()
            await self.record_task_completion("predict_sonar_performance", prediction, True)
            return {"status": "success", "result": prediction}
        except Exception as exc:  # noqa: BLE001
            await self.record_error("predict_sonar_failed", {"error": str(exc), "task": task})
            return {"status": "error", "message": "sonar_prediction_failed", "error": str(exc)}

    async def _forecast_environment(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Forecast ocean environmental conditions."""
        logger.info("Environment forecast requested")
        params = {}
        location = task.get("location", {})
        if location.get("lat") is not None and location.get("lon") is not None:
            params = {"lat": location.get("lat"), "lon": location.get("lon"), "radius_nm": task.get("radius_nm", 50)}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                headers = {"X-Internal-Token": self.internal_token} if self.internal_token else {"X-API-Key": self.api_key} if self.api_key else None
                response = await client.get(self.worldview_endpoint, params=params, headers=headers)
                response.raise_for_status()
                environment = response.json()
            result = {"forecast": environment.get("environments", []), "source": self.worldview_endpoint}
            await self.record_task_completion("forecast_environment", result, True)
            return {"status": "success", "result": result}
        except Exception as exc:  # noqa: BLE001
            await self.record_error("forecast_environment_failed", {"error": str(exc), "task": task})
            return {"status": "error", "message": "environment_forecast_failed", "error": str(exc)}
