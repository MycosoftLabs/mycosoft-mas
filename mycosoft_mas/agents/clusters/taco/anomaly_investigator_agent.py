"""Anomaly Investigator Agent — TAC-O Maritime Integration

Monitors all sensor feeds for deviations from environmental baselines.
Triggers investigation workflows when anomaly score exceeds threshold.
Correlates anomalies with AIS vessel traffic and environmental models.
"""

import logging
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AnomalyInvestigatorAgent(BaseAgent):
    """Monitors sensor feeds for baseline deviations and triggers investigations."""

    def __init__(self, agent_id: str = "taco-anomaly-investigator", name: str = "Anomaly Investigator", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = [
            "anomaly_detection",
            "ais_correlation",
            "investigation_trigger",
        ]
        self.cluster = "taco"
        self.anomaly_threshold = self.config.get("anomaly_threshold", 0.7)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        if task_type == "evaluate_anomaly":
            return await self._evaluate_anomaly(task)
        elif task_type == "correlate_ais":
            return await self._correlate_ais(task)
        return {"status": "error", "message": f"Unknown task type: {task_type}"}

    async def _evaluate_anomaly(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate sensor data for anomalies against baseline."""
        observation = task.get("observation", {})
        anomaly_score = observation.get("anomaly_score", 0.0)

        if anomaly_score > self.anomaly_threshold:
            logger.warning(
                "Anomaly detected: score=%.2f (threshold=%.2f) sensor=%s",
                anomaly_score, self.anomaly_threshold,
                observation.get("sensor_id", "unknown"),
            )
            return {
                "status": "success",
                "result": {
                    "anomaly_detected": True,
                    "anomaly_score": anomaly_score,
                    "action": "investigate",
                },
            }

        return {
            "status": "success",
            "result": {"anomaly_detected": False, "anomaly_score": anomaly_score},
        }

    async def _correlate_ais(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate anomaly with AIS vessel traffic data."""
        observation = task.get("observation", {})
        ais_tracks = task.get("ais_tracks", [])
        logger.info("AIS correlation requested for observation %s", task.get("observation_id"))

        correlated = []
        obs_lat = observation.get("latitude")
        obs_lon = observation.get("longitude")
        for track in ais_tracks:
            if obs_lat is None or obs_lon is None:
                continue
            track_lat = track.get("latitude")
            track_lon = track.get("longitude")
            if track_lat is None or track_lon is None:
                continue
            if abs(float(track_lat) - float(obs_lat)) <= 0.25 and abs(float(track_lon) - float(obs_lon)) <= 0.25:
                correlated.append(track)

        result = {
            "correlated": bool(correlated),
            "matches": correlated,
            "match_count": len(correlated),
        }
        await self.record_task_completion("correlate_ais", result, True)
        return {"status": "success", "result": result}
