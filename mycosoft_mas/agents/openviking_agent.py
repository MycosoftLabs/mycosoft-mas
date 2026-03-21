"""
OpenViking Agent - Manages OpenViking context databases on edge devices.

This agent is responsible for:
- Managing OpenViking device connections (register/unregister)
- Syncing device memory ↔ MAS memory (bidirectional)
- Cross-device knowledge sharing (federated learning)
- Querying device memory with tiered context loading (L0/L1/L2)
- Optimizing context tiers based on access patterns
- Responding to device anomaly events

Created: March 19, 2026
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class OpenVikingAgent(BaseAgent):
    """Manages OpenViking context databases on edge devices.

    Capabilities:
    - openviking_device_management: Register/unregister devices
    - edge_memory_sync: Bidirectional sync between MAS and devices
    - cross_device_knowledge_sharing: Share learnings across devices
    - context_tier_optimization: Optimize L0/L1/L2 usage patterns
    - device_memory_query: Query device memory with tiered loading
    """

    def __init__(
        self,
        agent_id: str = "openviking_agent",
        name: str = "OpenViking Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            agent_id=agent_id,
            name=name,
            config=config or {},
        )
        self.capabilities = [
            "openviking_device_management",
            "edge_memory_sync",
            "cross_device_knowledge_sharing",
            "context_tier_optimization",
            "device_memory_query",
        ]
        self._bridge = None
        self._sync_service = None

    async def _initialize_services(self) -> None:
        """Initialize OpenViking bridge and sync service."""
        await super()._initialize_services()

        try:
            from mycosoft_mas.memory.openviking_bridge import get_openviking_bridge
            from mycosoft_mas.memory.openviking_sync import get_openviking_sync

            self._bridge = await get_openviking_bridge()
            self._sync_service = await get_openviking_sync()
            logger.info("OpenVikingAgent initialized with bridge and sync service")
        except Exception as e:
            logger.warning("OpenVikingAgent partial init: %s", e)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process tasks related to OpenViking device management and memory sync."""
        task_type = task.get("type", "")

        handlers = {
            "register_device": self._handle_register_device,
            "unregister_device": self._handle_unregister_device,
            "sync_device": self._handle_sync_device,
            "sync_all": self._handle_sync_all,
            "query_device": self._handle_query_device,
            "push_knowledge": self._handle_push_knowledge,
            "start_sync": self._handle_start_sync,
            "stop_sync": self._handle_stop_sync,
            "device_status": self._handle_device_status,
            "share_knowledge": self._handle_share_knowledge,
        }

        handler = handlers.get(task_type)
        if handler:
            try:
                result = await handler(task)
                await self.record_task_completion(
                    task.get("task_id", task_type),
                    result,
                    success=True,
                )
                return {"status": "success", "result": result}
            except Exception as e:
                logger.exception("Task %s failed: %s", task_type, e)
                await self.record_error(str(e), {"task_type": task_type})
                return {"status": "error", "error": str(e)}
        else:
            return {
                "status": "error",
                "error": f"Unknown task type: {task_type}",
                "supported_types": list(handlers.keys()),
            }

    # ── Task Handlers ──────────────────────────────────────────────────

    async def _handle_register_device(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Register an edge device's OpenViking instance."""
        if not self._bridge:
            return {"error": "Bridge not initialized"}

        conn = await self._bridge.register_device(
            device_id=task["device_id"],
            openviking_url=task["openviking_url"],
            device_name=task.get("device_name"),
            tags=task.get("tags"),
            metadata=task.get("metadata"),
        )

        # Learn about this device in MAS memory
        await self.learn_fact(
            f"Edge device '{conn.device_name}' ({conn.device_id}) registered "
            f"with OpenViking at {conn.openviking_url}. "
            f"Status: {conn.status.value}."
        )

        return conn.to_dict()

    async def _handle_unregister_device(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Unregister a device."""
        if not self._bridge:
            return {"error": "Bridge not initialized"}

        removed = await self._bridge.unregister_device(task["device_id"])
        return {"removed": removed, "device_id": task["device_id"]}

    async def _handle_sync_device(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger sync for a specific device."""
        if not self._bridge:
            return {"error": "Bridge not initialized"}

        return await self._bridge.sync_device(task["device_id"])

    async def _handle_sync_all(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger sync for all devices."""
        if not self._bridge:
            return {"error": "Bridge not initialized"}

        results = await self._bridge.sync_all_devices()
        return {"synced_devices": len(results), "results": results}

    async def _handle_query_device(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Query a device's memory."""
        if not self._bridge:
            return {"error": "Bridge not initialized"}

        results = await self._bridge.query_device_memory(
            device_id=task["device_id"],
            query=task["query"],
            tier=task.get("tier", "L1"),
            top_k=task.get("top_k", 10),
            target_uri=task.get("target_uri"),
        )
        return {
            "device_id": task["device_id"],
            "query": task["query"],
            "results": results or [],
        }

    async def _handle_push_knowledge(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Push knowledge to a device."""
        if not self._bridge:
            return {"error": "Bridge not initialized"}

        if task.get("reason"):
            uri = await self._bridge.push_resource_to_device(
                device_id=task["device_id"],
                content=task["content"],
                reason=task["reason"],
                target=task.get("viking_path", "viking://resources/mas-agent-context/"),
                metadata=task.get("metadata"),
            )
            return {"status": "ingested", "uri": uri}
        else:
            success = await self._bridge.push_to_device(
                device_id=task["device_id"],
                content=task["content"],
                viking_path=task.get("viking_path", "viking://resources/mas-agent-context/"),
                metadata=task.get("metadata"),
            )
            return {"status": "pushed" if success else "failed"}

    async def _handle_start_sync(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Start the background sync service."""
        if not self._sync_service:
            return {"error": "Sync service not initialized"}

        await self._sync_service.start()
        return {"status": "started", "interval": self._sync_service._sync_interval}

    async def _handle_stop_sync(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Stop the background sync service."""
        if not self._sync_service:
            return {"error": "Sync service not initialized"}

        await self._sync_service.stop()
        return {"status": "stopped"}

    async def _handle_device_status(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get status of a device or all devices."""
        if not self._bridge:
            return {"error": "Bridge not initialized"}

        device_id = task.get("device_id")
        if device_id:
            conn = self._bridge.get_device(device_id)
            if not conn:
                return {"error": f"Device not found: {device_id}"}
            return conn.to_dict()
        else:
            return {
                "devices": [d.to_dict() for d in self._bridge.list_devices()],
                "sync_status": (self._sync_service.get_status() if self._sync_service else None),
            }

    async def _handle_share_knowledge(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Share knowledge from one device to all others (federated learning)."""
        if not self._sync_service:
            return {"error": "Sync service not initialized"}

        await self._sync_service.on_knowledge_learned(
            source_device_id=task["source_device_id"],
            knowledge=task["knowledge"],
        )
        return {"status": "shared", "source": task["source_device_id"]}

    # ── Health ─────────────────────────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the OpenViking agent."""
        base_health = await super().health_check()

        bridge_health = {}
        if self._bridge:
            bridge_health = await self._bridge.health_check()

        sync_status = {}
        if self._sync_service:
            sync_status = self._sync_service.get_status()

        return {
            **base_health,
            "bridge": bridge_health,
            "sync": sync_status,
        }
