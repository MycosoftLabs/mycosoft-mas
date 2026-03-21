"""
Workspace Sensor

Reads MYCA's live workspace state from VM 191:
- Active tasks and their status
- Platform connectivity (Slack, Discord, Signal, email)
- Recent staff interactions
- Pending notifications
- Daily schedule progress

Author: Morgan Rockwell / MYCA
Created: March 3, 2026
"""

import logging
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

import httpx

from mycosoft_mas.consciousness.sensors.base_sensor import BaseSensor

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.world_model import (
        SensorReading,
        WorldModel,
    )

logger = logging.getLogger(__name__)


class WorkspaceSensor(BaseSensor):
    """
    Sensor for MYCA's workspace on VM 191.

    Reads task state, platform status, and staff interactions
    so the consciousness pipeline can include workspace awareness
    in every response.
    """

    WORKSPACE_API_BASE = os.getenv("MYCA_WORKSPACE_URL", "http://192.168.0.191:8100")
    # Fallback: workspace API may also run on MAS VM during early dev
    FALLBACK_API_BASE = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")

    def __init__(self, world_model: Optional["WorldModel"] = None):
        super().__init__(world_model, "workspace")
        self._client: Optional[httpx.AsyncClient] = None
        self._api_base = self.WORKSPACE_API_BASE
        self._cached_state: Dict[str, Any] = {}
        self._last_fetch: Optional[datetime] = None
        # Refresh interval: don't hammer the API on every chat turn
        self._refresh_seconds = 30

    async def connect(self) -> bool:
        """Connect to the workspace API."""
        try:
            self._client = httpx.AsyncClient(timeout=5.0)

            # Try VM 191 first
            try:
                resp = await self._client.get(f"{self.WORKSPACE_API_BASE}/api/workspace/health")
                if resp.status_code == 200:
                    self._api_base = self.WORKSPACE_API_BASE
                    self._mark_connected()
                    return True
            except Exception:
                pass

            # Fallback to MAS VM workspace router
            try:
                resp = await self._client.get(f"{self.FALLBACK_API_BASE}/api/workspace/health")
                if resp.status_code == 200:
                    self._api_base = self.FALLBACK_API_BASE
                    self._mark_connected()
                    logger.info("Workspace sensor using MAS fallback")
                    return True
            except Exception:
                pass

            self._mark_error("Workspace API unreachable on both 191 and 188")
            return False

        except Exception as e:
            self._mark_error(str(e))
            return False

    async def disconnect(self) -> None:
        """Close the workspace connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._mark_disconnected()

    async def read(self) -> Optional["SensorReading"]:
        """Read the current workspace state."""
        from mycosoft_mas.consciousness.world_model import DataFreshness, SensorReading

        # Use cache if fresh enough
        if self._last_fetch and self._cached_state:
            age = (datetime.now(timezone.utc) - self._last_fetch).total_seconds()
            if age < self._refresh_seconds:
                return SensorReading(
                    sensor_type="workspace",
                    data=self._cached_state,
                    timestamp=self._last_fetch,
                    freshness=DataFreshness.RECENT,
                    confidence=0.9,
                )

        if not self._client or not self.is_connected:
            connected = await self.connect()
            if not connected:
                # Return cached data if available, even if stale
                if self._cached_state:
                    return SensorReading(
                        sensor_type="workspace",
                        data=self._cached_state,
                        timestamp=self._last_fetch or datetime.now(timezone.utc),
                        freshness=DataFreshness.STALE,
                        confidence=0.5,
                    )
                return None

        try:
            resp = await self._client.get(f"{self._api_base}/api/workspace/status")
            if resp.status_code == 200:
                data = resp.json()
                workspace = data.get("workspace", data)

                self._cached_state = {
                    "vm_ip": workspace.get("vm_ip", "192.168.0.191"),
                    "platforms": workspace.get("platforms", {}),
                    "active_conversations": workspace.get("active_conversations", 0),
                    "pending_tasks": workspace.get("pending_tasks", 0),
                    "total_tasks": workspace.get("total_tasks", 0),
                    "staff": workspace.get("staff_directory", {}),
                }
                self._last_fetch = datetime.now(timezone.utc)

                reading = SensorReading(
                    sensor_type="workspace",
                    data=self._cached_state,
                    timestamp=self._last_fetch,
                    freshness=DataFreshness.LIVE,
                    confidence=1.0,
                    source_url=f"{self._api_base}/api/workspace/status",
                )
                self._record_reading(reading)
                return reading

            self._mark_error(f"Workspace API returned {resp.status_code}")
            return None

        except Exception as e:
            self._mark_error(str(e))
            if self._cached_state:
                return SensorReading(
                    sensor_type="workspace",
                    data=self._cached_state,
                    timestamp=self._last_fetch or datetime.now(timezone.utc),
                    freshness=DataFreshness.STALE,
                    confidence=0.4,
                )
            return None

    async def get_task_summary(self) -> str:
        """Get a human-readable summary of current tasks for LLM context."""
        reading = await self.read()
        if not reading:
            return "Workspace status unavailable."

        data = reading.data
        parts = []

        pending = data.get("pending_tasks", 0)
        total = data.get("total_tasks", 0)
        if total > 0:
            parts.append(f"{pending} pending tasks out of {total} total")

        convos = data.get("active_conversations", 0)
        if convos > 0:
            parts.append(f"{convos} active conversations")

        platforms = data.get("platforms", {})
        connected = [p for p, s in platforms.items() if s == "connected"]
        if connected:
            parts.append(f"Connected platforms: {', '.join(connected)}")

        if not parts:
            return "Workspace is idle — no active tasks or conversations."

        return "Current workspace: " + "; ".join(parts) + "."
