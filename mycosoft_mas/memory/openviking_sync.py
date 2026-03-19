"""
OpenViking Sync Service - Periodic and event-driven synchronization.

Manages the background sync loop between MAS memory and OpenViking devices.
Supports both periodic sync (configurable interval) and event-driven sync
(e.g., anomaly detected, new protocol learned).

Publishes sync events to Redis pub/sub so other MAS components can react
(e.g., cross-device knowledge sharing).

Created: March 19, 2026
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("OpenVikingSync")

# Default sync interval in seconds (configurable via env)
DEFAULT_SYNC_INTERVAL = int(os.environ.get("OPENVIKING_SYNC_INTERVAL", "300"))

# Redis channel for OpenViking sync events
SYNC_CHANNEL = "mas:openviking:sync"
EVENT_CHANNEL = "mas:openviking:events"


class SyncEvent:
    """Types of sync events published to Redis."""

    DEVICE_SYNCED = "device_synced"
    DEVICE_ERROR = "device_error"
    KNOWLEDGE_SHARED = "knowledge_shared"
    ANOMALY_DETECTED = "anomaly_detected"
    DEVICE_REGISTERED = "device_registered"
    DEVICE_UNREGISTERED = "device_unregistered"
    SYNC_CYCLE_COMPLETE = "sync_cycle_complete"


class OpenVikingSyncService:
    """
    Background sync service for OpenViking device memory.

    Runs a periodic sync loop that:
    1. Pulls new memories from each device → MAS (device_to_mas)
    2. Pushes MAS knowledge → each device (mas_to_device)
    3. Shares cross-device knowledge (federated learning)
    4. Publishes sync events for other MAS components

    Can also be triggered on-demand for specific devices.
    """

    def __init__(
        self,
        sync_interval: int = DEFAULT_SYNC_INTERVAL,
    ) -> None:
        self._sync_interval = sync_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._bridge = None  # OpenVikingBridge (lazy)
        self._redis = None  # Redis client (lazy)
        self._event_handlers: List[Callable] = []
        self._sync_history: List[Dict[str, Any]] = []
        self._max_history = 100

    async def initialize(self) -> None:
        """Initialize the sync service with bridge and Redis connections."""
        from mycosoft_mas.memory.openviking_bridge import get_openviking_bridge

        self._bridge = await get_openviking_bridge()

        # Try to get Redis for pub/sub
        try:
            import redis.asyncio as aioredis

            redis_host = os.environ.get("REDIS_HOST", "192.168.0.189")
            redis_port = int(os.environ.get("REDIS_PORT", "6379"))
            self._redis = aioredis.Redis(
                host=redis_host, port=redis_port, decode_responses=True
            )
            await self._redis.ping()
            logger.info("OpenVikingSync connected to Redis at %s:%d", redis_host, redis_port)
        except Exception as e:
            logger.warning("OpenVikingSync running without Redis pub/sub: %s", e)
            self._redis = None

    async def start(self) -> None:
        """Start the periodic sync loop."""
        if self._running:
            logger.warning("OpenVikingSync already running")
            return

        if self._bridge is None:
            await self.initialize()

        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info(
            "OpenVikingSync started (interval=%ds)", self._sync_interval
        )

    async def stop(self) -> None:
        """Stop the periodic sync loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._redis:
            await self._redis.aclose()
            self._redis = None
        logger.info("OpenVikingSync stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Periodic Sync Loop ─────────────────────────────────────────────

    async def _sync_loop(self) -> None:
        """Main periodic sync loop."""
        while self._running:
            try:
                await self._run_sync_cycle()
            except Exception as e:
                logger.exception("Sync cycle error: %s", e)
            try:
                await asyncio.sleep(self._sync_interval)
            except asyncio.CancelledError:
                break

    async def _run_sync_cycle(self) -> Dict[str, Any]:
        """Run a single sync cycle across all devices."""
        if not self._bridge:
            return {"error": "Bridge not initialized"}

        cycle_start = datetime.now(timezone.utc)
        results = await self._bridge.sync_all_devices()

        # Cross-device knowledge sharing
        cross_device_results = await self._share_cross_device_knowledge()

        cycle_result = {
            "timestamp": cycle_start.isoformat(),
            "device_syncs": results,
            "cross_device": cross_device_results,
            "duration_ms": (
                datetime.now(timezone.utc) - cycle_start
            ).total_seconds() * 1000,
        }

        # Track history
        self._sync_history.append(cycle_result)
        if len(self._sync_history) > self._max_history:
            self._sync_history = self._sync_history[-self._max_history:]

        # Publish sync event
        await self._publish_event(
            SyncEvent.SYNC_CYCLE_COMPLETE,
            {
                "device_count": len(results),
                "total_synced": sum(
                    r.get("pull", {}).get("synced_items", 0)
                    + r.get("push", {}).get("pushed_items", 0)
                    for r in results
                    if "error" not in r
                ),
                "errors": sum(1 for r in results if "error" in r),
            },
        )

        return cycle_result

    # ── On-Demand Sync ─────────────────────────────────────────────────

    async def trigger_sync(self, device_id: str) -> Dict[str, Any]:
        """Trigger an immediate sync for a specific device."""
        if not self._bridge:
            await self.initialize()

        result = await self._bridge.sync_device(device_id)

        await self._publish_event(
            SyncEvent.DEVICE_SYNCED,
            {"device_id": device_id, "result": result},
        )

        return result

    async def trigger_sync_all(self) -> List[Dict[str, Any]]:
        """Trigger an immediate sync for all devices."""
        if not self._bridge:
            await self.initialize()
        return await self._bridge.sync_all_devices()

    # ── Event-Driven Sync ──────────────────────────────────────────────

    async def on_anomaly_detected(
        self,
        device_id: str,
        anomaly: Dict[str, Any],
    ) -> None:
        """Handle anomaly detection from a device — immediate sync + alert.

        When a device detects something unusual (e.g., gas resistance spike),
        we immediately pull its latest data and promote to MAS.
        """
        logger.info("Anomaly detected on %s: %s", device_id, anomaly.get("type", "unknown"))

        if self._bridge:
            # Immediate pull from the device
            await self._bridge.sync_from_device(device_id)

        # Publish anomaly event for other agents
        await self._publish_event(
            SyncEvent.ANOMALY_DETECTED,
            {"device_id": device_id, "anomaly": anomaly},
        )

    async def on_knowledge_learned(
        self,
        source_device_id: str,
        knowledge: Dict[str, Any],
    ) -> None:
        """Handle new knowledge from a device — share with all devices.

        Example: Mushroom1 learns that a gas resistance pattern means
        contamination → share with Hyphae1 so it knows without experiencing it.
        """
        if not self._bridge:
            return

        devices = self._bridge.list_devices()
        pushed_to = []

        for conn in devices:
            if conn.device_id == source_device_id:
                continue
            try:
                content = json.dumps(knowledge, default=str)
                await self._bridge.push_resource_to_device(
                    device_id=conn.device_id,
                    content=content,
                    reason=f"Cross-device knowledge from {source_device_id}",
                    target="viking://resources/mas-agent-context/",
                )
                pushed_to.append(conn.device_id)
            except Exception as e:
                logger.warning(
                    "Failed to share knowledge to %s: %s", conn.device_id, e
                )

        await self._publish_event(
            SyncEvent.KNOWLEDGE_SHARED,
            {
                "source_device": source_device_id,
                "shared_to": pushed_to,
                "knowledge_type": knowledge.get("type", "unknown"),
            },
        )

    # ── Cross-Device Knowledge Sharing ─────────────────────────────────

    async def _share_cross_device_knowledge(self) -> Dict[str, Any]:
        """After syncing all devices, check for learnings to share across devices.

        If device A learned something (in viking://memories/errors-learned/),
        it should be pushed to device B's viking://resources/mas-agent-context/.
        """
        if not self._bridge:
            return {"shared": 0}

        devices = self._bridge.list_devices()
        if len(devices) < 2:
            return {"shared": 0, "reason": "fewer_than_2_devices"}

        shared_count = 0
        for source in devices:
            client = self._bridge._clients.get(source.device_id)
            if not client:
                continue

            try:
                # Get recently learned errors/patterns
                learned = await client.find(
                    query="learned pattern error observation",
                    top_k=5,
                    target_uri="viking://memories/errors-learned/",
                )
                if not learned:
                    continue

                for item in learned:
                    content = await client.read(item.get("uri", ""), tier="L1")
                    if not content:
                        continue

                    # Push to all other devices
                    for target in devices:
                        if target.device_id == source.device_id:
                            continue
                        await self._bridge.push_to_device(
                            device_id=target.device_id,
                            content=content.get("content", ""),
                            viking_path="viking://resources/mas-agent-context/",
                            metadata={
                                "source_device": source.device_id,
                                "type": "cross_device_learning",
                                "synced_at": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                        shared_count += 1
            except Exception as e:
                logger.warning(
                    "Cross-device share from %s failed: %s", source.device_id, e
                )

        return {"shared": shared_count}

    # ── Pub/Sub ────────────────────────────────────────────────────────

    async def _publish_event(
        self,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Publish a sync event to Redis for other MAS components."""
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        if self._redis:
            try:
                await self._redis.publish(EVENT_CHANNEL, json.dumps(event, default=str))
            except Exception as e:
                logger.warning("Failed to publish sync event: %s", e)

        # Call registered handlers
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.warning("Event handler error: %s", e)

    def on_event(self, handler: Callable) -> None:
        """Register a handler for sync events."""
        self._event_handlers.append(handler)

    # ── Status ─────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get sync service status."""
        return {
            "running": self._running,
            "sync_interval": self._sync_interval,
            "history_count": len(self._sync_history),
            "last_sync": (
                self._sync_history[-1]["timestamp"]
                if self._sync_history
                else None
            ),
        }

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sync history."""
        return self._sync_history[-limit:]


# ── Singleton ──────────────────────────────────────────────────────────

_sync_instance: Optional[OpenVikingSyncService] = None
_sync_lock = asyncio.Lock()


async def get_openviking_sync() -> OpenVikingSyncService:
    """Get or create the singleton OpenVikingSyncService instance."""
    global _sync_instance
    if _sync_instance is None:
        async with _sync_lock:
            if _sync_instance is None:
                _sync_instance = OpenVikingSyncService()
                await _sync_instance.initialize()
    return _sync_instance
