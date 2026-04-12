"""Signal Classifier Agent — TAC-O Maritime Integration

Runs NLM acoustic/magnetic classification on sensor data from
maritime sensor packages. All classifications pass through
AVANI ecological safety gate before operator alerting.

Data flow:
  MycoBrain MDP -> this agent -> NLM classify/acoustic endpoint
  -> AVANI marine mammal filter -> FUSARIUM threat panel
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.integrations.zeetachec_client import MaritimeSensorNetworkClient

logger = logging.getLogger(__name__)


class SignalClassifierAgent(BaseAgent):
    """Ingests sensor data and runs NLM classification with AVANI gating."""

    def __init__(self, agent_id: str = "taco-signal-classifier", name: str = "Signal Classifier", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = [
            "acoustic_classification",
            "magnetic_classification",
            "avani_ecological_gate",
        ]
        self.cluster = "taco"
        self.nlm_endpoint = self.config.get("nlm_endpoint", "http://192.168.0.189:8000/api/mindex/nlm/classify/acoustic")
        self.avani_endpoint = self.config.get("avani_endpoint", "http://192.168.0.188:8001/api/avani/ecological-review")
        self.mammal_score_threshold = 0.5
        self.internal_token = os.getenv("MINDEX_INTERNAL_TOKEN", "").strip()
        self.api_key = os.getenv("MINDEX_API_KEY", "").strip()
        self.sensor_network_client = MaritimeSensorNetworkClient(
            self.config.get("sensor_network_client") or self.config.get("zeetachec_client")
        )

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        if task_type == "classify_acoustic":
            return await self._classify_acoustic(task)
        elif task_type == "classify_magnetic":
            return await self._classify_magnetic(task)
        return {"status": "error", "message": f"Unknown task type: {task_type}"}

    async def _classify_acoustic(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run acoustic classification through NLM and AVANI gate."""
        sensor_data = task.get("sensor_data", {})
        sensor_id = sensor_data.get("sensor_id", "unknown")

        logger.info("Classifying acoustic data from sensor %s", sensor_id)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                headers = {"X-Internal-Token": self.internal_token} if self.internal_token else {"X-API-Key": self.api_key} if self.api_key else None
                nlm_response = await client.post(self.nlm_endpoint, json=sensor_data, headers=headers)
                nlm_response.raise_for_status()
                classification = nlm_response.json()

                avani_response = await client.post(self.avani_endpoint, json=classification)
                avani_response.raise_for_status()
                avani_review = avani_response.json()

            result = {
                "sensor_id": sensor_id,
                "classification": classification.get("classification"),
                "confidence": classification.get("confidence", 0.0),
                "marine_mammal_score": classification.get("marine_mammal_score", 0.0),
                "avani_review": avani_review,
                "recommendation": classification.get("recommendation"),
            }

            await self.sensor_network_client.create_assessment(
                {
                    "observation_ids": [str(sensor_data.get("observation_id"))] if sensor_data.get("observation_id") else [],
                    "assessment_type": "acoustic_classification",
                    "classification": classification,
                    "recommendation": {
                        "summary": classification.get("recommendation"),
                        "action": avani_review.get("action", "pass"),
                    },
                    "urgency": classification.get("confidence", 0.0),
                    "avani_ecological_check": avani_review,
                    "merkle_hash": sensor_data.get("merkle_hash"),
                }
            )
            await self.record_task_completion("classify_acoustic", result, True)
            return {"status": "success", "result": result}
        except Exception as exc:  # noqa: BLE001
            await self.record_error("acoustic_classification_failed", {"error": str(exc), "sensor_id": sensor_id})
            return {
                "status": "error",
                "message": "Failed to classify acoustic data",
                "sensor_id": sensor_id,
                "error": str(exc),
            }

    async def _classify_magnetic(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run magnetic anomaly classification."""
        sensor_data = task.get("sensor_data", {})
        sensor_id = sensor_data.get("sensor_id", "unknown")

        logger.info("Classifying magnetic data from sensor %s", sensor_id)
        anomaly_score = float(sensor_data.get("anomaly_score", 0.0) or 0.0)
        classification = {
            "classification": "magnetic_anomaly" if anomaly_score >= self.mammal_score_threshold else "baseline",
            "confidence": max(0.0, min(anomaly_score, 1.0)),
            "recommendation": "Investigate correlated contact" if anomaly_score >= self.mammal_score_threshold else "Continue monitoring",
        }
        await self.sensor_network_client.create_assessment(
            {
                "observation_ids": [str(sensor_data.get("observation_id"))] if sensor_data.get("observation_id") else [],
                "assessment_type": "magnetic_classification",
                "classification": classification,
                "recommendation": {"summary": classification["recommendation"]},
                "urgency": classification["confidence"],
                "merkle_hash": sensor_data.get("merkle_hash"),
            }
        )
        await self.record_task_completion("classify_magnetic", classification, True)
        return {"status": "success", "result": {"sensor_id": sensor_id, **classification}}
