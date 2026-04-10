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
import os
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

    def _build_mindex_headers(self) -> Dict[str, str]:
        """Build auth headers for MINDEX internal endpoints when available."""
        headers: Dict[str, str] = {}
        internal_token = os.getenv("MINDEX_INTERNAL_TOKEN", "").strip()
        api_key = os.getenv("MINDEX_API_KEY", "").strip()
        if internal_token:
            headers["X-Internal-Token"] = internal_token
        if api_key:
            headers["X-API-Key"] = api_key
        return headers

    def _build_mycobrain_payload(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize telemetry payload into MINDEX MycoBrain ingest schema.

        If upstream already provides a `payload` object, pass it through.
        Otherwise, preserve incoming telemetry under `raw`.
        """
        if isinstance(telemetry_data.get("payload"), dict):
            return telemetry_data["payload"]
        return {"raw": telemetry_data}
    
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
        headers = self._build_mindex_headers()
        request_body = {
            "serial_number": device_id,
            "recorded_at": datetime.now().isoformat(),
            "payload": self._build_mycobrain_payload(telemetry_data),
        }

        # Canonical internal route first, then compatibility path.
        candidate_paths = [
            "/api/mindex/internal/mycobrain/telemetry/ingest",
            "/api/mindex/mycobrain/telemetry/ingest",
        ]

        try:
            for path in candidate_paths:
                try:
                    response = await self.client.post(
                        f"{self.mindex_url.rstrip('/')}{path}",
                        json=request_body,
                        headers=headers or None,
                    )
                    if 200 <= response.status_code < 300:
                        return True
                    logger.warning(
                        "MINDEX telemetry forward failed on %s status=%s body=%s",
                        path,
                        response.status_code,
                        response.text[:500],
                    )
                except Exception as endpoint_error:
                    logger.warning("MINDEX telemetry forward error on %s: %s", path, endpoint_error)
            return False
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


























