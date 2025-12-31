"""
MycoBrain MAS Integration

Bridges MycoBrain service with Mycosoft MAS orchestrator for:
- Device registration with MAS agents
- Telemetry forwarding to MINDEX
- Command routing from MAS
- Workflow automation
"""

import asyncio
import logging
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class MycoBrainMASIntegration:
    """Integration between MycoBrain service and MAS orchestrator."""
    
    def __init__(
        self,
        mycobrain_url: str = "http://localhost:8003",
        mas_url: str = "http://localhost:8001",
        mindex_url: str = "http://localhost:8000",
    ):
        self.mycobrain_url = mycobrain_url
        self.mas_url = mas_url
        self.mindex_url = mindex_url
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def register_device_with_mas(
        self,
        device_id: str,
        port: str,
        serial_number: Optional[str] = None,
        firmware_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Register MycoBrain device with MAS orchestrator."""
        try:
            response = await self.client.post(
                f"{self.mas_url}/agents/mycobrain-device/register",
                json={
                    "device_id": device_id,
                    "port": port,
                    "serial_number": serial_number or device_id,
                    "firmware_version": firmware_version or "unknown",
                    "metadata": metadata or {},
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to register device with MAS: {e}")
            return {"error": str(e)}
    
    async def forward_telemetry_to_mindex(
        self,
        device_id: str,
        telemetry_data: Dict[str, Any],
    ) -> bool:
        """Forward telemetry data to MINDEX."""
        try:
            response = await self.client.post(
                f"{self.mindex_url}/api/mindex/telemetry",
                json={
                    "source": "mycobrain",
                    "device_id": device_id,
                    "timestamp": datetime.now().isoformat(),
                    "data": telemetry_data,
                },
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to forward telemetry to MINDEX: {e}")
            return False
    
    async def send_command_via_mas(
        self,
        device_id: str,
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send command to device via MAS orchestrator."""
        try:
            response = await self.client.post(
                f"{self.mas_url}/agents/mycobrain-device/command",
                json={
                    "device_id": device_id,
                    "command": command,
                    "parameters": parameters or {},
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send command via MAS: {e}")
            return {"error": str(e)}
    
    async def get_device_status_from_mas(
        self,
        device_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get device status from MAS."""
        try:
            response = await self.client.get(
                f"{self.mas_url}/agents/mycobrain-device/status/{device_id}",
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(f"Device status not available from MAS: {e}")
            return None
    
    async def list_devices_from_mas(self) -> List[Dict[str, Any]]:
        """List all MycoBrain devices from MAS."""
        try:
            response = await self.client.get(
                f"{self.mas_url}/agents/mycobrain-device/devices",
            )
            response.raise_for_status()
            data = response.json()
            return data.get("devices", [])
        except Exception as e:
            logger.debug(f"Device list not available from MAS: {e}")
            return []
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()






















