"""
NatureOS Sensor

Reads ecosystem and life status data from NatureOS:
- Device health
- Ecosystem monitoring
- Life status
- Environmental conditions

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
import httpx

from mycosoft_mas.consciousness.sensors.base_sensor import BaseSensor, SensorStatus

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.world_model import WorldModel, SensorReading, DataFreshness

logger = logging.getLogger(__name__)


class NatureOSSensor(BaseSensor):
    """
    Sensor for NatureOS ecosystem data.
    
    Connects to the NatureOS platform for life monitoring,
    device status, and ecosystem health data.
    """
    
    # API endpoints
    NATUREOS_API_BASE = "http://192.168.0.188:8001/api/natureos"
    
    def __init__(self, world_model: Optional["WorldModel"] = None):
        super().__init__(world_model, "natureos")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def connect(self) -> bool:
        """Connect to the NatureOS API."""
        try:
            self._client = httpx.AsyncClient(timeout=10.0)
            
            response = await self._client.get(f"{self.NATUREOS_API_BASE}/health")
            if response.status_code == 200:
                self._mark_connected()
                return True
            
            self._mark_error(f"API returned {response.status_code}")
            return False
            
        except Exception as e:
            self._mark_error(str(e))
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the NatureOS API."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._mark_disconnected()
    
    async def read(self) -> Optional["SensorReading"]:
        """Read current ecosystem status."""
        from mycosoft_mas.consciousness.world_model import SensorReading, DataFreshness
        
        if not self._client:
            await self.connect()
        
        if not self.is_connected:
            return None
        
        try:
            data = {}
            
            # Get ecosystem status
            ecosystem = await self._get_ecosystem_status()
            if ecosystem:
                data["ecosystem"] = ecosystem
                data["overall_status"] = ecosystem.get("overall", "unknown")
            
            # Get device status
            devices = await self._get_device_status()
            if devices:
                data["devices"] = devices
                data["device_count"] = len(devices.get("devices", []))
            
            # Get life monitoring data
            life = await self._get_life_status()
            if life:
                data["life"] = life
            
            reading = SensorReading(
                sensor_type="natureos",
                data=data,
                timestamp=datetime.now(timezone.utc),
                freshness=DataFreshness.RECENT if data else DataFreshness.UNAVAILABLE,
                confidence=0.85 if data else 0.0,
                source_url=self.NATUREOS_API_BASE
            )
            
            self._record_reading(reading)
            return reading
            
        except Exception as e:
            self._mark_error(str(e))
            return None
    
    async def _get_ecosystem_status(self) -> Optional[Dict[str, Any]]:
        """Get overall ecosystem status."""
        try:
            response = await self._client.get(f"{self.NATUREOS_API_BASE}/ecosystem/status")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Ecosystem status error: {e}")
        return None
    
    async def _get_device_status(self) -> Optional[Dict[str, Any]]:
        """Get status of all NatureOS devices."""
        try:
            response = await self._client.get(f"{self.NATUREOS_API_BASE}/devices")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Device status error: {e}")
        return None
    
    async def _get_life_status(self) -> Optional[Dict[str, Any]]:
        """Get life monitoring data."""
        try:
            response = await self._client.get(f"{self.NATUREOS_API_BASE}/life/status")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Life status error: {e}")
        return None
    
    async def get_device_details(self, device_id: str) -> Dict[str, Any]:
        """Get detailed info about a specific device."""
        if not self._client or not self.is_connected:
            return {"error": "Not connected"}
        
        try:
            response = await self._client.get(
                f"{self.NATUREOS_API_BASE}/devices/{device_id}"
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Device not found: {device_id}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_ecosystem_metrics(self) -> Dict[str, Any]:
        """Get ecosystem health metrics."""
        if not self._client or not self.is_connected:
            return {"error": "Not connected"}
        
        try:
            response = await self._client.get(
                f"{self.NATUREOS_API_BASE}/ecosystem/metrics"
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
