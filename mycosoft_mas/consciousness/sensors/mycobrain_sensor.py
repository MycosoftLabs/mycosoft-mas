"""
MycoBrain Sensor

Reads device telemetry from MycoBrain devices:
- Sensor readings (BME688/690)
- Device status
- Presence detection
- Environmental data

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import httpx

from mycosoft_mas.consciousness.sensors.base_sensor import BaseSensor, SensorStatus

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.world_model import WorldModel, SensorReading, DataFreshness

logger = logging.getLogger(__name__)


class MycoBrainSensor(BaseSensor):
    """
    Sensor for MycoBrain device telemetry.
    
    Connects to the MycoBrain service for real-time device
    data, sensor readings, and presence detection.
    """
    
    # API endpoints
    MYCOBRAIN_API_BASE = "http://192.168.0.188:8001/api/mycobrain"
    LOCAL_SERVICE = "http://localhost:8003"  # Local MycoBrain service
    
    def __init__(self, world_model: Optional["WorldModel"] = None):
        super().__init__(world_model, "mycobrain")
        self._client: Optional[httpx.AsyncClient] = None
        self._api_base = self.MYCOBRAIN_API_BASE
    
    async def connect(self) -> bool:
        """Connect to the MycoBrain API."""
        try:
            self._client = httpx.AsyncClient(timeout=5.0)
            
            # Try MAS API endpoint
            try:
                response = await self._client.get(f"{self.MYCOBRAIN_API_BASE}/health")
                if response.status_code == 200:
                    self._api_base = self.MYCOBRAIN_API_BASE
                    self._mark_connected()
                    return True
            except Exception:
                pass
            
            # Try local service
            try:
                response = await self._client.get(f"{self.LOCAL_SERVICE}/health")
                if response.status_code == 200:
                    self._api_base = self.LOCAL_SERVICE
                    self._mark_connected()
                    return True
            except Exception:
                pass
            
            self._mark_error("Could not connect to MycoBrain API")
            return False
            
        except Exception as e:
            self._mark_error(str(e))
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the MycoBrain API."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._mark_disconnected()
    
    async def read(self) -> Optional["SensorReading"]:
        """Read current device telemetry."""
        from mycosoft_mas.consciousness.world_model import SensorReading, DataFreshness
        
        if not self._client:
            await self.connect()
        
        if not self.is_connected:
            return None
        
        try:
            data = {}
            
            # Get all device statuses
            devices = await self._get_devices()
            if devices:
                data["devices"] = devices
                data["active_count"] = sum(
                    1 for d in devices if d.get("status") == "online"
                )
            
            # Get latest sensor readings
            readings = await self._get_sensor_readings()
            if readings:
                data["sensor_readings"] = readings
            
            # Get presence detection status
            presence = await self._get_presence()
            if presence:
                data["presence"] = presence
            
            reading = SensorReading(
                sensor_type="mycobrain",
                data=data,
                timestamp=datetime.now(timezone.utc),
                freshness=DataFreshness.LIVE if data else DataFreshness.UNAVAILABLE,
                confidence=0.9 if data else 0.0,
                source_url=self._api_base
            )
            
            self._record_reading(reading)
            return reading
            
        except Exception as e:
            self._mark_error(str(e))
            return None
    
    async def _get_devices(self) -> Optional[List[Dict[str, Any]]]:
        """Get list of all MycoBrain devices."""
        try:
            response = await self._client.get(f"{self._api_base}/devices")
            if response.status_code == 200:
                return response.json().get("devices", [])
        except Exception as e:
            logger.debug(f"Devices error: {e}")
        return None
    
    async def _get_sensor_readings(self) -> Optional[Dict[str, Any]]:
        """Get latest sensor readings from all devices."""
        try:
            response = await self._client.get(f"{self._api_base}/sensors/latest")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Sensor readings error: {e}")
        return None
    
    async def _get_presence(self) -> Optional[Dict[str, Any]]:
        """Get presence detection status."""
        try:
            response = await self._client.get(f"{self._api_base}/presence")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Presence error: {e}")
        return None
    
    async def get_device_telemetry(self, device_id: str) -> Dict[str, Any]:
        """Get telemetry for a specific device."""
        if not self._client or not self.is_connected:
            return {"error": "Not connected"}
        
        try:
            response = await self._client.get(
                f"{self._api_base}/devices/{device_id}/telemetry"
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Device not found: {device_id}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_environmental_data(self) -> Dict[str, Any]:
        """Get aggregated environmental data from all sensors."""
        if not self._client or not self.is_connected:
            return {"error": "Not connected"}
        
        try:
            response = await self._client.get(f"{self._api_base}/environment")
            if response.status_code == 200:
                return response.json()
            return {"error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def check_presence(self, user_id: str = "morgan") -> Dict[str, Any]:
        """Check if a specific user is present."""
        if not self._client or not self.is_connected:
            return {"error": "Not connected", "present": False}
        
        try:
            response = await self._client.get(
                f"{self._api_base}/presence/{user_id}"
            )
            if response.status_code == 200:
                return response.json()
            return {"present": False, "confidence": 0}
        except Exception as e:
            return {"error": str(e), "present": False}
    
    async def get_air_quality(self) -> Dict[str, Any]:
        """Get aggregated air quality data from BME688/690 sensors."""
        if not self._client or not self.is_connected:
            return {"error": "Not connected"}
        
        try:
            response = await self._client.get(f"{self._api_base}/air-quality")
            if response.status_code == 200:
                return response.json()
            return {"error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
