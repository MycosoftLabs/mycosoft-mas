"""
OpenViking Bridge - Bidirectional bridge between MAS memory and edge devices.

Connects MAS's 6-layer memory system (on MINDEX) to OpenViking context databases
running on Jetson Orin edge devices. Enables:

- Device → MAS: Sensor observations, task completions, learned patterns promoted
  to MAS semantic/episodic layers
- MAS → Device: Agent knowledge, cultivation protocols, updated models pushed
  to device viking://resources/

Each registered device has its own OpenVikingClient connection. The bridge
coordinates sync, query, and push operations across all devices.

Created: March 19, 2026
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse
from uuid import uuid4

logger = logging.getLogger("OpenVikingBridge")


class DeviceConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    SYNCING = "syncing"
    ERROR = "error"
    STALE = "stale"


@dataclass
class DeviceConnection:
    """Represents a registered edge device's OpenViking instance."""

    device_id: str
    device_name: str
    openviking_url: str
    host: str
    port: int
    status: DeviceConnectionStatus = DeviceConnectionStatus.DISCONNECTED
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sync_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "openviking_url": self.openviking_url,
            "host": self.host,
            "port": self.port,
            "status": self.status.value,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "last_error": self.last_error,
            "registered_at": self.registered_at.isoformat(),
            "sync_count": self.sync_count,
            "tags": self.tags,
            "metadata": self.metadata,
        }


# Mapping from OpenViking paths to MAS memory layers
VIKING_TO_MAS_LAYER_MAP: Dict[str, str] = {
    "viking://memories/sensor-observations/": "episodic",
    "viking://memories/task-completions/": "episodic",
    "viking://memories/errors-learned/": "semantic",
    "viking://memories/device-preferences/": "system",
    "viking://resources/mas-agent-context/": "semantic",
    "viking://resources/mushroom-cultivation/": "semantic",
    "viking://skills/": "procedural",
}

# Paths synced device → MAS (pulled from device)
DEVICE_TO_MAS_PATHS = [
    "viking://memories/sensor-observations/",
    "viking://memories/task-completions/",
    "viking://memories/errors-learned/",
]

# Paths synced MAS → device (pushed to device)
MAS_TO_DEVICE_PATHS = [
    "viking://resources/mas-agent-context/",
    "viking://resources/mushroom-cultivation/",
    "viking://skills/",
]


# Allowed private subnet for OpenViking devices (LAN only)
_ALLOWED_NETWORKS = [
    ipaddress.ip_network("192.168.0.0/24"),  # Mycosoft LAN
]


def validate_openviking_url(url: str) -> tuple[str, int]:
    """Validate and parse an OpenViking device URL. Returns (host, port).

    Rejects URLs pointing to loopback, link-local, non-private, or
    otherwise dangerous addresses to prevent SSRF.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme!r} (must be http or https)")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname")

    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        raise ValueError(
            f"OpenViking URLs must use IP addresses, not hostnames: {hostname!r}"
        )

    if addr.is_loopback:
        raise ValueError(f"Loopback addresses are not allowed: {addr}")
    if addr.is_link_local:
        raise ValueError(f"Link-local addresses are not allowed: {addr}")
    if addr.is_multicast:
        raise ValueError(f"Multicast addresses are not allowed: {addr}")
    if addr.is_reserved:
        raise ValueError(f"Reserved addresses are not allowed: {addr}")
    if addr.is_unspecified:
        raise ValueError(f"Unspecified addresses are not allowed: {addr}")

    if not any(addr in net for net in _ALLOWED_NETWORKS):
        raise ValueError(
            f"Address {addr} is not in an allowed network. "
            f"Only devices on the Mycosoft LAN (192.168.0.0/24) can be registered."
        )

    port = parsed.port or 1933
    return str(addr), port


class OpenVikingBridge:
    """
    Bidirectional bridge between MAS 6-layer memory and OpenViking context
    databases running on edge devices.

    Sync strategy:
    - Device → MAS: Sensor observations, task completions, learned patterns
      are promoted to MAS semantic/episodic layers
    - MAS → Device: Agent knowledge, cultivation protocols, updated models
      are pushed to device viking://resources/

    Usage:
        bridge = OpenVikingBridge()
        await bridge.initialize()
        await bridge.register_device("mushroom1", "http://192.168.0.123:1933")
        results = await bridge.query_device_memory("mushroom1", "temperature readings")
    """

    def __init__(self) -> None:
        self._devices: Dict[str, DeviceConnection] = {}
        self._clients: Dict[str, Any] = {}  # device_id → OpenVikingClient
        self._coordinator = None  # MemoryCoordinator (lazy)
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the bridge and connect to memory coordinator."""
        if self._initialized:
            return
        try:
            from mycosoft_mas.memory.coordinator import get_memory_coordinator

            self._coordinator = await get_memory_coordinator()
            self._initialized = True
            logger.info("OpenVikingBridge initialized")
        except Exception as e:
            logger.warning("OpenVikingBridge init without coordinator: %s", e)
            self._initialized = True

    async def register_device(
        self,
        device_id: str,
        openviking_url: str,
        device_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DeviceConnection:
        """Register an edge device's OpenViking instance.

        Connects to the device's OpenViking server and verifies reachability.
        If the device was previously registered, its connection is updated.
        """
        from mycosoft_mas.edge.openviking_client import OpenVikingClient

        # Validate URL against SSRF — only allow Mycosoft LAN IPs
        host, port = validate_openviking_url(openviking_url)
        url = openviking_url.rstrip("/")

        client = OpenVikingClient(host=host, port=port, base_url=url)
        connected = await client.connect()

        conn = DeviceConnection(
            device_id=device_id,
            device_name=device_name or device_id,
            openviking_url=url,
            host=host,
            port=port,
            status=(
                DeviceConnectionStatus.CONNECTED
                if connected
                else DeviceConnectionStatus.ERROR
            ),
            last_error=None if connected else "Initial connection failed",
            tags=tags or [],
            metadata=metadata or {},
        )

        async with self._lock:
            # Disconnect old client if re-registering
            if device_id in self._clients:
                old = self._clients[device_id]
                await old.disconnect()

            self._devices[device_id] = conn
            self._clients[device_id] = client

        if connected:
            logger.info("Registered device %s at %s", device_id, url)
            # Initialize directory structure on device
            await self._ensure_device_directories(device_id)
        else:
            logger.warning("Registered device %s at %s (unreachable)", device_id, url)

        return conn

    async def unregister_device(self, device_id: str) -> bool:
        """Unregister a device and close its connection."""
        async with self._lock:
            if device_id not in self._devices:
                return False
            if device_id in self._clients:
                await self._clients[device_id].disconnect()
                del self._clients[device_id]
            del self._devices[device_id]
        logger.info("Unregistered device %s", device_id)
        return True

    def get_device(self, device_id: str) -> Optional[DeviceConnection]:
        """Get device connection info."""
        return self._devices.get(device_id)

    def list_devices(self) -> List[DeviceConnection]:
        """List all registered devices."""
        return list(self._devices.values())

    def _get_client(self, device_id: str):
        """Get the OpenVikingClient for a device."""
        client = self._clients.get(device_id)
        if client is None:
            raise ValueError(f"Device not registered: {device_id}")
        return client

    # ── Query Operations ───────────────────────────────────────────────

    async def query_device_memory(
        self,
        device_id: str,
        query: str,
        tier: str = "L1",
        top_k: int = 10,
        target_uri: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Query a device's OpenViking memory with tiered loading.

        Args:
            device_id: The registered device ID
            query: Semantic search query
            tier: Context tier (L0=abstract, L1=overview, L2=full)
            top_k: Max results
            target_uri: Restrict search to a specific viking:// path
        """
        client = self._get_client(device_id)
        results = await client.find(query, top_k=top_k, target_uri=target_uri)
        if results is None:
            self._devices[device_id].status = DeviceConnectionStatus.ERROR
            self._devices[device_id].last_error = "Query failed"
            return None

        # If tier is L0 or L1, fetch the appropriate summary for each result
        if tier in ("L0", "L1"):
            enriched = []
            for result in results:
                uri = result.get("uri", "")
                if uri:
                    content = await client.read(uri, tier=tier)
                    if content:
                        result["tiered_content"] = content.get("content", "")
                enriched.append(result)
            return enriched

        return results

    async def push_to_device(
        self,
        device_id: str,
        content: str,
        viking_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Push content from MAS to a device's OpenViking filesystem.

        Used to share agent knowledge, updated protocols, etc. with edge devices.
        """
        client = self._get_client(device_id)
        success = await client.write_content(viking_path, content, metadata=metadata)
        if success:
            logger.info("Pushed content to %s: %s", device_id, viking_path)
        else:
            self._devices[device_id].last_error = f"Push to {viking_path} failed"
        return success

    async def push_resource_to_device(
        self,
        device_id: str,
        content: str,
        reason: str,
        target: str = "viking://resources/mas-agent-context/",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Ingest a resource into a device's OpenViking context database.

        Unlike push_to_device, this triggers OpenViking's L0/L1 generation pipeline.
        """
        client = self._get_client(device_id)
        uri = await client.add_resource(
            content=content, reason=reason, target=target, metadata=metadata
        )
        if uri:
            logger.info("Ingested resource on %s: %s", device_id, uri)
        return uri

    # ── Sync Operations ────────────────────────────────────────────────

    async def sync_from_device(self, device_id: str) -> Dict[str, Any]:
        """Pull new memories/observations from device → MAS memory layers.

        Reads changed items from device OpenViking paths and promotes them
        to the appropriate MAS memory layer (episodic, semantic, etc.).
        """
        client = self._get_client(device_id)
        conn = self._devices[device_id]
        conn.status = DeviceConnectionStatus.SYNCING

        since = conn.last_sync or conn.registered_at
        synced_items = 0
        errors = 0

        for viking_path in DEVICE_TO_MAS_PATHS:
            try:
                changed = await client.list_changed_since(viking_path, since)
                if not changed:
                    continue

                mas_layer = VIKING_TO_MAS_LAYER_MAP.get(viking_path, "episodic")

                for item in changed:
                    uri = item.get("uri", "")
                    # Read L1 overview for promotion to MAS
                    content_data = await client.read(uri, tier="L1")
                    if not content_data:
                        continue

                    await self._promote_to_mas(
                        device_id=device_id,
                        layer=mas_layer,
                        content=content_data.get("content", ""),
                        viking_uri=uri,
                        metadata=item.get("metadata", {}),
                    )
                    synced_items += 1
            except Exception as e:
                logger.warning(
                    "Sync from device %s path %s failed: %s",
                    device_id, viking_path, e,
                )
                errors += 1

        conn.last_sync = datetime.now(timezone.utc)
        conn.sync_count += 1
        conn.status = DeviceConnectionStatus.CONNECTED
        conn.last_error = None if errors == 0 else f"{errors} path(s) failed"

        result = {
            "device_id": device_id,
            "synced_items": synced_items,
            "errors": errors,
            "direction": "device_to_mas",
            "timestamp": conn.last_sync.isoformat(),
        }
        logger.info("Synced from device %s: %d items, %d errors", device_id, synced_items, errors)
        return result

    async def push_to_device_sync(self, device_id: str) -> Dict[str, Any]:
        """Push MAS knowledge to device's OpenViking filesystem.

        Queries MAS semantic/procedural memory for knowledge relevant to the
        device and pushes it to the appropriate viking:// paths.
        """
        conn = self._devices[device_id]
        conn.status = DeviceConnectionStatus.SYNCING
        pushed_items = 0
        errors = 0

        if self._coordinator:
            try:
                # Get device-relevant knowledge from MAS semantic memory
                device_tags = conn.tags or [conn.device_name]
                for tag in device_tags:
                    memories = await self._coordinator.agent_recall(
                        agent_id="openviking_agent",
                        query=tag,
                        limit=20,
                    )
                    if not memories:
                        continue

                    for memory in memories:
                        content = memory.get("content", "")
                        if isinstance(content, dict):
                            import json
                            content = json.dumps(content, default=str)
                        elif not isinstance(content, str):
                            content = str(content)

                        success = await self.push_to_device(
                            device_id=device_id,
                            content=content,
                            viking_path="viking://resources/mas-agent-context/",
                            metadata={
                                "source": "mas_sync",
                                "tag": tag,
                                "synced_at": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                        if success:
                            pushed_items += 1
                        else:
                            errors += 1
            except Exception as e:
                logger.warning("Push to device %s failed: %s", device_id, e)
                errors += 1

        conn.status = DeviceConnectionStatus.CONNECTED
        result = {
            "device_id": device_id,
            "pushed_items": pushed_items,
            "errors": errors,
            "direction": "mas_to_device",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("Pushed to device %s: %d items, %d errors", device_id, pushed_items, errors)
        return result

    async def sync_device(self, device_id: str) -> Dict[str, Any]:
        """Full bidirectional sync for a single device."""
        pull_result = await self.sync_from_device(device_id)
        push_result = await self.push_to_device_sync(device_id)
        return {
            "device_id": device_id,
            "pull": pull_result,
            "push": push_result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def sync_all_devices(self) -> List[Dict[str, Any]]:
        """Sync all registered devices (bidirectional)."""
        results = []
        for device_id in list(self._devices.keys()):
            conn = self._devices.get(device_id)
            if not conn or conn.status == DeviceConnectionStatus.DISCONNECTED:
                continue
            try:
                result = await self.sync_device(device_id)
                results.append(result)
            except Exception as e:
                logger.warning("Sync failed for device %s: %s", device_id, e)
                results.append({
                    "device_id": device_id,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        return results

    # ── Health ─────────────────────────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """Check health of the bridge and all device connections."""
        device_statuses = {}
        for device_id, conn in self._devices.items():
            client = self._clients.get(device_id)
            if client:
                health = await client.health_check()
                device_statuses[device_id] = {
                    "status": conn.status.value,
                    "reachable": health.get("reachable", False),
                    "last_sync": conn.last_sync.isoformat() if conn.last_sync else None,
                    "sync_count": conn.sync_count,
                }
            else:
                device_statuses[device_id] = {"status": "no_client"}

        return {
            "bridge_status": "healthy" if self._initialized else "uninitialized",
            "device_count": len(self._devices),
            "devices": device_statuses,
        }

    # ── Internal Helpers ───────────────────────────────────────────────

    async def _ensure_device_directories(self, device_id: str) -> None:
        """Create the standard OpenViking directory structure on a device."""
        client = self._get_client(device_id)
        directories = [
            "viking://memories/",
            "viking://memories/sensor-observations/",
            "viking://memories/task-completions/",
            "viking://memories/errors-learned/",
            "viking://memories/device-preferences/",
            "viking://resources/",
            "viking://resources/mushroom-cultivation/",
            "viking://resources/sensor-calibration/",
            "viking://resources/mycobrain-protocols/",
            "viking://resources/mas-agent-context/",
            "viking://skills/",
            "viking://skills/environmental-monitoring/",
            "viking://skills/anomaly-detection/",
            "viking://skills/actuator-control/",
            "viking://skills/reporting/",
            "viking://sessions/",
        ]
        for d in directories:
            await client.mkdir(d)

    async def _promote_to_mas(
        self,
        device_id: str,
        layer: str,
        content: str,
        viking_uri: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Promote a device memory item to the appropriate MAS memory layer."""
        if not self._coordinator:
            logger.warning("Cannot promote to MAS: no coordinator")
            return

        entry_metadata = {
            "source": "openviking",
            "device_id": device_id,
            "viking_uri": viking_uri,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }

        try:
            if layer == "episodic":
                await self._coordinator.record_episode(
                    agent_id="openviking_agent",
                    event_type="device_observation",
                    description=content[:500],
                    outcome="synced",
                    metadata=entry_metadata,
                )
            elif layer == "semantic":
                await self._coordinator.agent_remember(
                    agent_id="openviking_agent",
                    content={"text": content, **entry_metadata},
                    layer="semantic",
                    importance=0.7,
                )
            elif layer == "procedural":
                await self._coordinator.store_procedure(
                    name=f"device_{device_id}_{viking_uri.split('/')[-2]}",
                    steps=[{"description": content}],
                    metadata=entry_metadata,
                )
            else:
                await self._coordinator.agent_remember(
                    agent_id="openviking_agent",
                    content={"text": content, **entry_metadata},
                    layer=layer,
                    importance=0.5,
                )
        except Exception as e:
            logger.warning("Failed to promote to MAS layer %s: %s", layer, e)


# ── Singleton ──────────────────────────────────────────────────────────

_bridge_instance: Optional[OpenVikingBridge] = None
_bridge_lock = asyncio.Lock()


async def get_openviking_bridge() -> OpenVikingBridge:
    """Get or create the singleton OpenVikingBridge instance."""
    global _bridge_instance
    if _bridge_instance is None:
        async with _bridge_lock:
            if _bridge_instance is None:
                _bridge_instance = OpenVikingBridge()
                await _bridge_instance.initialize()
    return _bridge_instance
