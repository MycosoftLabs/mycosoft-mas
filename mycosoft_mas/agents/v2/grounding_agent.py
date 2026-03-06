"""
Grounding Agent - Wraps GroundingGate for agent-based invocation.
Capabilities: ground_input, validate_ep, inspect_ep.
Created: February 17, 2026
"""

from __future__ import annotations

import logging
from typing import Any, Dict

try:
    from mycosoft_mas.agents.base_agent import BaseAgent
except Exception:
    BaseAgent = object  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)


class GroundingAgent(BaseAgent if BaseAgent is not object else object):  # type: ignore[misc]
    """Agent wrapper for GroundingGate - Experience Packet creation and validation."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        if BaseAgent is not object:
            super().__init__(agent_id=agent_id, name=name, config=config or {})
        else:
            self.agent_id = agent_id
            self.name = name
            self.config = config or {}
        self.capabilities = ["ground_input", "validate_ep", "inspect_ep"]

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        if task_type == "ground_input":
            return await self._ground_input(task)
        if task_type == "validate_ep":
            return await self._validate_ep(task)
        if task_type == "inspect_ep":
            return await self._inspect_ep(task)
        return {"status": "skipped", "result": {"reason": f"unknown task type: {task_type}"}}

    async def _ground_input(self, task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.consciousness import get_consciousness
            from mycosoft_mas.consciousness.grounding_gate import GroundingGate

            consciousness = get_consciousness()
            gate = GroundingGate(consciousness)
            ep = await gate.build_experience_packet(
                content=task.get("content", ""),
                source=task.get("source", "text"),
                context=task.get("context"),
                session_id=task.get("session_id"),
                user_id=task.get("user_id"),
            )
            await gate.attach_self_state(ep)
            await gate.attach_world_state(ep)
            valid, errors = gate.validate(ep)
            ep_id = getattr(ep, "id", None) or "ep_unknown"
            return {"status": "success", "result": {"ep_id": ep_id, "valid": valid, "errors": errors}}
        except Exception as e:
            logger.warning("GroundingAgent ground_input failed: %s", e)
            return {"status": "error", "result": {"error": str(e)}}

    async def _validate_ep(self, task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.schemas.experience_packet import (
                ExperiencePacket,
                GroundTruth,
                SelfState,
                WorldStateRef,
                Observation,
                Uncertainty,
                Provenance,
            )
            from mycosoft_mas.consciousness import get_consciousness
            from mycosoft_mas.consciousness.grounding_gate import GroundingGate

            ep_data = task.get("ep") or task.get("experience_packet")
            if not ep_data:
                return {"status": "error", "result": {"error": "ep or experience_packet required"}}
            ep = ExperiencePacket(
                ground_truth=ep_data.get("ground_truth") or GroundTruth(),
                self_state=ep_data.get("self_state") or SelfState(),
                world_state=ep_data.get("world_state") or WorldStateRef(),
                observation=ep_data.get("observation") or Observation(modality="text", raw_payload=""),
                uncertainty=ep_data.get("uncertainty") or Uncertainty(),
                provenance=ep_data.get("provenance") or Provenance(),
            )
            consciousness = get_consciousness()
            gate = GroundingGate(consciousness)
            valid, errors = gate.validate(ep)
            return {"status": "success", "result": {"valid": valid, "errors": errors}}
        except Exception as e:
            logger.warning("GroundingAgent validate_ep failed: %s", e)
            return {"status": "error", "result": {"error": str(e)}}

    async def _inspect_ep(self, task: Dict[str, Any]) -> Dict[str, Any]:
        ep_id = task.get("ep_id")
        if not ep_id:
            return {"status": "error", "result": {"error": "ep_id required"}}
        try:
            import os
            import httpx
            url = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
            path = f"/api/mindex/grounding/experience-packets/{ep_id}"
            headers = {}
            if os.getenv("MINDEX_API_KEY"):
                headers["X-API-Key"] = os.getenv("MINDEX_API_KEY")
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{url}{path}", headers=headers or None)
                if r.status_code == 200:
                    return {"status": "success", "result": r.json()}
                return {"status": "error", "result": {"error": r.text[:200], "status": r.status_code}}
        except Exception as e:
            logger.warning("GroundingAgent inspect_ep failed: %s", e)
            return {"status": "error", "result": {"error": str(e)}}
