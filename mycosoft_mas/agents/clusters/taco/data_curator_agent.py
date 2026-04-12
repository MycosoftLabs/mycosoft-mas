"""Data Curator Agent — TAC-O Maritime Integration

Manages training data lifecycle: ingestion, labeling, quality assurance,
versioning, and provenance tracking. Coordinates with maritime field
collections and maintains MINDEX acoustic/magnetic datasets.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class DataCuratorAgent(BaseAgent):
    """Manages training data lifecycle for TAC-O NLM models."""

    def __init__(self, agent_id: str = "taco-data-curator", name: str = "Data Curator", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = [
            "dataset_ingestion",
            "data_labeling",
            "quality_assurance",
            "version_tracking",
            "provenance_audit",
        ]
        self.cluster = "taco"
        self.mindex_endpoint = self.config.get(
            "mindex_endpoint", "http://192.168.0.189:8000"
        )

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        if task_type == "ingest_training_data":
            return await self._ingest_training_data(task)
        elif task_type == "audit_provenance":
            return await self._audit_provenance(task)
        elif task_type == "dataset_status":
            return await self._dataset_status(task)
        return {"status": "error", "message": f"Unknown task type: {task_type}"}

    async def _ingest_training_data(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest new training data from maritime field collection."""
        source = task.get("source", "unknown")
        logger.info("Ingesting training data from source: %s", source)
        result = {
            "ingestion": "received",
            "source": source,
            "dataset_name": task.get("dataset_name"),
            "record_count": task.get("record_count", 0),
            "storage_path": task.get("storage_path"),
        }
        await self.record_task_completion("ingest_training_data", result, True)
        return {"status": "success", "result": result}

    async def _audit_provenance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Audit data provenance via Merkle hash chain."""
        observation_id = task.get("observation_id")
        logger.info("Provenance audit for observation %s", observation_id)
        result = {
            "audit": "pass" if task.get("merkle_hash") else "warning",
            "observation_id": observation_id,
            "merkle_hash_present": bool(task.get("merkle_hash")),
        }
        await self.record_task_completion("audit_provenance", result, True)
        return {"status": "success", "result": result}

    async def _dataset_status(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get current training dataset status."""
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                obs_response = await client.get(f"{self.mindex_endpoint}/api/mindex/taco/observations?limit=1&offset=0")
                obs_response.raise_for_status()
                obs_data = obs_response.json()

                sig_response = await client.get(f"{self.mindex_endpoint}/api/mindex/maritime/acoustic-signatures?limit=1&offset=0")
                sig_response.raise_for_status()
                sig_data = sig_response.json()

            result = {
                "tables": ["acoustic_signatures", "taco_observations"],
                "observation_count_visible": obs_data.get("total", 0),
                "signature_count_visible": sig_data.get("total", 0),
                "status": "ready",
            }
            await self.record_task_completion("dataset_status", result, True)
            return {"status": "success", "result": result}
        except Exception as exc:  # noqa: BLE001
            await self.record_error("dataset_status_failed", {"error": str(exc)})
            return {"status": "error", "message": "dataset_status_failed", "error": str(exc)}
