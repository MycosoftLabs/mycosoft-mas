"""
NATUREOS Cloud Integration Client

This module provides integration with the NATUREOS cloud system (https://github.com/MycosoftLabs/NatureOS).
NATUREOS is a cloud platform for environmental monitoring and IoT device management.

The client connects to NATUREOS via REST API for:
- Device management
- Sensor data collection
- Environmental monitoring
- Data analytics

Environment Variables:
    NATUREOS_API_URL: NATUREOS API endpoint (default: http://localhost:8002)
    NATUREOS_API_KEY: API key for authenticated requests
    NATUREOS_TENANT_ID: Tenant/organization ID (optional)

Usage:
    from mycosoft_mas.integrations.natureos_client import NATUREOSClient
    
    client = NATUREOSClient()
    devices = await client.list_devices()
    data = await client.get_sensor_data(device_id="esp32-001")
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx
import asyncio

logger = logging.getLogger(__name__)


class NATUREOSClient:
    """
    Client for interacting with the NATUREOS cloud platform.
    
    NATUREOS provides:
    - IoT device management (ESP32, sensors)
    - Real-time sensor data collection
    - Environmental monitoring
    - Data analytics and visualization
    - Device provisioning and configuration
    
    This client handles authentication, rate limiting, and error recovery.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the NATUREOS client.
        
        Args:
            config: Optional configuration dictionary. If not provided, reads from environment variables.
                   Expected keys:
                   - api_url: NATUREOS API base URL
                   - api_key: API key for authentication
                   - tenant_id: Tenant/organization ID
                   - timeout: Request timeout in seconds (default: 30)
                   - max_retries: Maximum retry attempts (default: 3)
        """
        self.config = config or {}
        
        # API endpoint
        self.api_url = self.config.get(
            "api_url",
            os.getenv("NATUREOS_API_URL", "http://localhost:8002")
        ).rstrip('/')
        
        # Authentication
        self.api_key = self.config.get(
            "api_key",
            os.getenv("NATUREOS_API_KEY", "")
        )
        
        self.tenant_id = self.config.get(
            "tenant_id",
            os.getenv("NATUREOS_TENANT_ID", "")
        )
        
        # Connection settings
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
        
        # HTTP client (lazy loading)
        self._http_client = None
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"NATUREOS client initialized - API: {self.api_url}")
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client for REST API access.
        
        Returns:
            httpx.AsyncClient: HTTP client with configured headers
            
        Note:
            Includes API key and tenant ID in headers if configured.
            Client is reused for multiple requests.
        """
        if self._http_client is None:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            if self.tenant_id:
                headers["X-Tenant-ID"] = self.tenant_id
            
            self._http_client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True
            )
        
        return self._http_client
    
    async def list_devices(
        self,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all registered devices.
        
        Args:
            device_type: Filter by device type (e.g., "esp32", "raspberry_pi")
            status: Filter by status (e.g., "online", "offline", "error")
            limit: Maximum number of devices to return
        
        Returns:
            List of device dictionaries with fields:
            - id: Device ID
            - name: Device name
            - type: Device type
            - status: Current status
            - location: Device location (if available)
            - last_seen: Last communication timestamp
            - sensors: List of attached sensors
        
        Example:
            devices = await client.list_devices(device_type="esp32", status="online")
            for device in devices:
                print(f"{device['name']} - {device['status']}")
        """
        try:
            client = await self._get_http_client()
            params = {"limit": limit}
            if device_type:
                params["device_type"] = device_type
            if status:
                params["status"] = status
            
            response = await client.get("/devices", params=params)
            response.raise_for_status()
            data = response.json()
            
            self.logger.debug(f"Retrieved {len(data.get('items', []))} devices")
            return data.get("items", [])
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error listing devices: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in list_devices: {e}")
            raise
    
    async def get_device(self, device_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific device.
        
        Args:
            device_id: Device identifier
        
        Returns:
            Device dictionary with full details including configuration and status
        """
        try:
            client = await self._get_http_client()
            response = await client.get(f"/devices/{device_id}")
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error getting device {device_id}: {e}")
            raise
    
    async def get_sensor_data(
        self,
        device_id: str,
        sensor_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get sensor data from a device.
        
        Args:
            device_id: Device identifier
            sensor_type: Filter by sensor type (e.g., "temperature", "humidity", "co2")
            start_time: Start of time range (default: 24 hours ago)
            end_time: End of time range (default: now)
            limit: Maximum number of data points
        
        Returns:
            List of sensor data records with fields:
            - timestamp: Data timestamp
            - sensor_type: Type of sensor
            - value: Sensor reading value
            - unit: Measurement unit
            - metadata: Additional sensor metadata
        
        Example:
            # Get temperature data from last hour
            end = datetime.utcnow()
            start = end - timedelta(hours=1)
            data = await client.get_sensor_data(
                device_id="esp32-001",
                sensor_type="temperature",
                start_time=start,
                end_time=end
            )
        """
        try:
            client = await self._get_http_client()
            params = {"limit": limit}
            
            if sensor_type:
                params["sensor_type"] = sensor_type
            
            if start_time:
                params["start_time"] = start_time.isoformat()
            else:
                params["start_time"] = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            
            if end_time:
                params["end_time"] = end_time.isoformat()
            else:
                params["end_time"] = datetime.utcnow().isoformat()
            
            response = await client.get(f"/devices/{device_id}/sensor-data", params=params)
            response.raise_for_status()
            data = response.json()
            
            self.logger.debug(f"Retrieved {len(data.get('items', []))} sensor data points")
            return data.get("items", [])
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error getting sensor data: {e}")
            raise
    
    async def register_device(
        self,
        device_id: str,
        name: str,
        device_type: str,
        location: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register a new device with NATUREOS.
        
        Args:
            device_id: Unique device identifier
            name: Human-readable device name
            device_type: Type of device (e.g., "esp32", "raspberry_pi")
            location: Optional location data (lat, lon, elevation)
            metadata: Optional additional metadata
        
        Returns:
            Registered device information with configuration
        
        Note:
            Device must be registered before it can send data.
            Registration creates device record and provisioning credentials.
        """
        try:
            client = await self._get_http_client()
            payload = {
                "device_id": device_id,
                "name": name,
                "device_type": device_type
            }
            if location:
                payload["location"] = location
            if metadata:
                payload["metadata"] = metadata
            
            response = await client.post("/devices/register", json=payload)
            response.raise_for_status()
            
            self.logger.info(f"Registered device: {device_id}")
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error registering device: {e}")
            raise
    
    async def update_device_config(
        self,
        device_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update device configuration.
        
        Args:
            device_id: Device identifier
            config: Configuration dictionary to update
        
        Returns:
            Updated device configuration
        
        Note:
            Configuration changes are pushed to device on next connection.
            Used for remote device management and parameter updates.
        """
        try:
            client = await self._get_http_client()
            response = await client.put(f"/devices/{device_id}/config", json=config)
            response.raise_for_status()
            
            self.logger.info(f"Updated configuration for device: {device_id}")
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error updating device config: {e}")
            raise
    
    async def register_mycobrain_device(
        self,
        device_id: str,
        serial_number: str,
        name: str,
        firmware_version: str,
        location: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register a MycoBrain device with NATUREOS.
        
        Args:
            device_id: Device identifier
            serial_number: Device serial number
            name: Human-readable device name
            firmware_version: Firmware version string
            location: Optional location dict with lat/lon
            metadata: Optional additional metadata (I²C addresses, analog labels, etc.)
        
        Returns:
            Registered device information with provisioning credentials
        """
        try:
            device_metadata = {
                "serial_number": serial_number,
                "firmware_version": firmware_version,
                "device_type": "mycobrain",
            }
            if metadata:
                device_metadata.update(metadata)
            
            return await self.register_device(
                device_id=device_id,
                name=name,
                device_type="mycobrain",
                location=location,
                metadata=device_metadata
            )
        
        except Exception as e:
            self.logger.error(f"Error registering MycoBrain device: {e}")
            raise
    
    async def send_mycobrain_command(
        self,
        device_id: str,
        command_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a command to a MycoBrain device via NATUREOS.
        
        Args:
            device_id: Device identifier
            command_type: Command type (e.g., "set_mosfet", "set_telemetry_interval", "i2c_scan")
            parameters: Command parameters
        
        Returns:
            Command execution result
        
        Note:
            Commands are routed through NATUREOS to the device.
            NATUREOS handles retry logic and acknowledgements.
        """
        try:
            client = await self._get_http_client()
            payload = {
                "command_type": command_type,
                "parameters": parameters
            }
            
            response = await client.post(
                f"/devices/{device_id}/commands/mycobrain",
                json=payload
            )
            response.raise_for_status()
            
            self.logger.info(f"Sent command {command_type} to device {device_id}")
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error sending MycoBrain command: {e}")
            raise
    
    async def get_mycobrain_devices(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get list of MycoBrain devices registered with NATUREOS.
        
        Args:
            status: Optional status filter ("online", "offline", "error")
            limit: Maximum number of devices (default: 100)
        
        Returns:
            List of MycoBrain device records
        """
        try:
            return await self.list_devices(
                device_type="mycobrain",
                status=status,
                limit=limit
            )
        except Exception as e:
            self.logger.error(f"Error fetching MycoBrain devices: {e}")
            raise
    
    async def get_mycobrain_telemetry(
        self,
        device_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get telemetry data from a MycoBrain device.
        
        Args:
            device_id: Device identifier
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Maximum number of records (default: 100)
        
        Returns:
            List of telemetry records with MycoBrain-specific fields
        """
        try:
            # Use generic sensor data endpoint with MycoBrain-specific sensor types
            return await self.get_sensor_data(
                device_id=device_id,
                sensor_type=None,  # Get all sensor types
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
        except Exception as e:
            self.logger.error(f"Error fetching MycoBrain telemetry: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check NATUREOS system health.
        
        Returns:
            Health status dictionary with:
            - status: Overall status ("ok" or "error")
            - timestamp: Check timestamp
            - version: NATUREOS API version
            - services: Dictionary of service statuses
        
        Note:
            Performs API connectivity check.
            Used for monitoring and health endpoints.
        """
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unknown"
        }
        
        try:
            client = await self._get_http_client()
            response = await client.get("/health", timeout=5)
            if response.status_code == 200:
                health.update(response.json())
                health["status"] = "ok"
            else:
                health["status"] = "error"
                health["error"] = f"HTTP {response.status_code}"
        except Exception as e:
            health["status"] = "error"
            health["error"] = str(e)
        
        return health
    
    async def close(self):
        """
        Close HTTP client and clean up resources.
        
        Note:
            Should be called when client is no longer needed.
            Closes HTTP client connection.
        """
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        
        self.logger.info("NATUREOS client connections closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes connections."""
        await self.close()

