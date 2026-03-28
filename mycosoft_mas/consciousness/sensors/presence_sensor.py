"""
Presence Sensor

Reads presence data from the Mycosoft website:
- Online users count
- Active sessions
- Staff online
- Superuser presence
- Session statistics

Author: MYCA
Created: March 28, 2026
"""

import logging
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

import httpx

from mycosoft_mas.consciousness.sensors.base_sensor import BaseSensor

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.world_model import SensorReading, WorldModel

logger = logging.getLogger(__name__)


class PresenceSensor(BaseSensor):
    """
    Sensor for user presence data.

    Connects to the presence API to get real-time information about
    online users, active sessions, staff presence, and site statistics.
    """

    # API endpoints (env-configurable)
    PRESENCE_API_BASE = os.getenv("MYCA_PRESENCE_URL", "http://192.168.0.187:3000/api/presence")
    FALLBACK_API_BASE = os.getenv(
        "MYCA_PRESENCE_FALLBACK_URL", "http://localhost:3010/api/presence"
    )

    def __init__(self, world_model: Optional["WorldModel"] = None):
        super().__init__(world_model, "presence")
        self._client: Optional[httpx.AsyncClient] = None
        self._api_base = self.PRESENCE_API_BASE

    async def connect(self) -> bool:
        """Connect to the Presence API."""
        try:
            self._client = httpx.AsyncClient(timeout=5.0)

            # Try primary endpoint
            try:
                response = await self._client.get(f"{self.PRESENCE_API_BASE}/health")
                if response.status_code == 200:
                    self._api_base = self.PRESENCE_API_BASE
                    self._mark_connected()
                    return True
            except Exception:
                pass

            # Try fallback
            try:
                response = await self._client.get(f"{self.FALLBACK_API_BASE}/health")
                if response.status_code == 200:
                    self._api_base = self.FALLBACK_API_BASE
                    self._mark_connected()
                    return True
            except Exception:
                pass

            self._mark_error("Could not connect to Presence API")
            return False

        except Exception as e:
            self._mark_error(str(e))
            return False

    async def disconnect(self) -> None:
        """Disconnect from the Presence API."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._mark_disconnected()

    async def read(self) -> Optional[Dict[str, Any]]:
        """Read current presence data.

        Returns a plain dict (not SensorReading) for lightweight consumption
        by WorldModel.update() and update_all().
        """
        if not self._client:
            await self.connect()

        if not self.is_connected:
            return None

        try:
            data: Dict[str, Any] = {}

            # Get online users summary
            summary = await self._get_summary()
            if summary:
                data.update(summary)

            # Get session stats
            sessions = await self._get_sessions()
            if sessions:
                data["sessions"] = sessions
                data["sessions_count"] = sessions.get("active", 0)

            # Get staff status
            staff = await self._get_staff()
            if staff:
                data["staff"] = staff
                data["staff_count"] = staff.get("online_count", 0)
                data["superuser_online"] = staff.get("superuser_online", False)

            return data if data else None

        except Exception as e:
            self._mark_error(str(e))
            return None

    async def _get_summary(self) -> Optional[Dict[str, Any]]:
        """Get online users summary."""
        try:
            response = await self._client.get(f"{self._api_base}/summary")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Presence summary error: {e}")
        return None

    async def _get_sessions(self) -> Optional[Dict[str, Any]]:
        """Get active session stats."""
        try:
            response = await self._client.get(f"{self._api_base}/sessions")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Presence sessions error: {e}")
        return None

    async def _get_staff(self) -> Optional[Dict[str, Any]]:
        """Get staff presence info."""
        try:
            response = await self._client.get(f"{self._api_base}/staff")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Presence staff error: {e}")
        return None
