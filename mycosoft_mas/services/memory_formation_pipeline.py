from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from mycosoft_mas.services.sensor_fusion import NaturePacket


class MemoryFormationPipeline:
    """
    Phase 1.4 memory path:
    sensors -> episodic memory -> dream consolidation trigger.
    """

    def __init__(self, consciousness: Any) -> None:
        self._consciousness = consciousness

    async def ingest_packet(self, packet: NaturePacket, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "episodic_memory_id": None,
            "dream_triggered": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        memory = getattr(self._consciousness, "_memory_coordinator", None)
        if memory:
            stored = await memory.agent_remember(
                agent_id="myca",
                content={"packet": packet.to_dict(), "context": context or {}},
                layer="episodic",
                importance=0.65,
                tags=["nature_packet", "first_light_pipeline"],
            )
            if isinstance(stored, dict):
                result["episodic_memory_id"] = stored.get("memory_id")

        dream_state = getattr(self._consciousness, "_dream_state", None)
        if dream_state and getattr(dream_state, "queue_memory_for_consolidation", None):
            await dream_state.queue_memory_for_consolidation(
                {"source": "nature_packet", "packet": packet.to_dict()}
            )
            result["dream_triggered"] = True

        return result

