"""
Device Registry - February 4, 2026

Tracks all MycoBrain devices including firmware versions,
hardware specifications, telemetry data, and device status.

Supported Devices:
- SporeBase: Main controller unit
- Mushroom1: Cultivation monitoring device
- NFC Tags: Smart product tags
- Sensors: Environmental sensors
"""

import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from mycosoft_mas.registry.system_registry import (
    get_registry, SystemRegistry, DeviceInfo, DeviceType
)

logger = logging.getLogger("DeviceRegistry")


# ============================================================================
# Known Devices Configuration
# ============================================================================

KNOWN_DEVICES = [
    {
        "device_id": "sporebase-001",
        "name": "SporeBase Alpha",
        "type": DeviceType.SPOREBASE,
        "firmware_version": "1.2.0",
        "hardware_version": "rev3",
        "description": "Primary cultivation controller"
    },
    {
        "device_id": "mushroom1-001",
        "name": "Mushroom1 Unit A",
        "type": DeviceType.MUSHROOM1,
        "firmware_version": "2.0.1",
        "hardware_version": "rev2",
        "description": "Lion's Mane monitoring station"
    },
    {
        "device_id": "mushroom1-002",
        "name": "Mushroom1 Unit B",
        "type": DeviceType.MUSHROOM1,
        "firmware_version": "2.0.1",
        "hardware_version": "rev2",
        "description": "Reishi monitoring station"
    },
    {
        "device_id": "nfc-batch-001",
        "name": "NFC Tag Batch 1",
        "type": DeviceType.NFC_TAG,
        "firmware_version": None,
        "hardware_version": "ntag215",
        "description": "Product authentication tags"
    },
    {
        "device_id": "sensor-temp-001",
        "name": "Temperature Sensor Array",
        "type": DeviceType.SENSOR,
        "firmware_version": "1.0.0",
        "hardware_version": "ds18b20-array",
        "description": "Multi-zone temperature monitoring"
    },
    {
        "device_id": "sensor-humidity-001",
        "name": "Humidity Sensor Array",
        "type": DeviceType.SENSOR,
        "firmware_version": "1.0.0",
        "hardware_version": "dht22-array",
        "description": "Multi-zone humidity monitoring"
    },
    {
        "device_id": "sensor-co2-001",
        "name": "CO2 Sensor",
        "type": DeviceType.SENSOR,
        "firmware_version": "1.0.0",
        "hardware_version": "mh-z19b",
        "description": "CO2 level monitoring"
    },
    {
        "device_id": "gateway-001",
        "name": "IoT Gateway Primary",
        "type": DeviceType.GATEWAY,
        "firmware_version": "3.1.0",
        "hardware_version": "esp32-gateway",
        "description": "Main IoT hub for device communication"
    }
]


class DeviceRegistry:
    """
    Manages device registration, status tracking, and telemetry.
    """
    
    def __init__(self, registry: Optional[SystemRegistry] = None):
        self._registry = registry or get_registry()
        self._device_cache: Dict[str, DeviceInfo] = {}
    
    async def initialize_known_devices(self) -> Dict[str, Any]:
        """Register all known devices in the system."""
        results = {
            "registered": [],
            "errors": []
        }
        
        for device_config in KNOWN_DEVICES:
            try:
                device = DeviceInfo(
                    device_id=device_config["device_id"],
                    name=device_config["name"],
                    type=device_config["type"],
                    firmware_version=device_config.get("firmware_version"),
                    hardware_version=device_config.get("hardware_version"),
                    status="unknown",
                    metadata={
                        "description": device_config.get("description", ""),
                        "registered_at": datetime.now(timezone.utc).isoformat()
                    }
                )
                
                await self._registry.register_device(device)
                self._device_cache[device.device_id] = device
                results["registered"].append(device.device_id)
                
            except Exception as e:
                logger.error(f"Failed to register device {device_config['device_id']}: {e}")
                results["errors"].append({
                    "device_id": device_config["device_id"],
                    "error": str(e)
                })
        
        logger.info(f"Registered {len(results['registered'])} devices")
        return results
    
    async def update_device_status(
        self,
        device_id: str,
        status: str,
        telemetry: Optional[Dict[str, Any]] = None
    ) -> Optional[DeviceInfo]:
        """Update device status and telemetry."""
        devices = await self._registry.list_devices()
        
        device = None
        for d in devices:
            if d.device_id == device_id:
                device = d
                break
        
        if not device:
            logger.warning(f"Device not found: {device_id}")
            return None
        
        # Update status
        device.status = status
        device.last_seen = datetime.now(timezone.utc)
        
        if telemetry:
            device.telemetry = {
                **device.telemetry,
                **telemetry,
                "last_update": datetime.now(timezone.utc).isoformat()
            }
        
        await self._registry.register_device(device)
        self._device_cache[device_id] = device
        
        return device
    
    async def update_firmware(
        self,
        device_id: str,
        firmware_version: str
    ) -> Optional[DeviceInfo]:
        """Update device firmware version."""
        devices = await self._registry.list_devices()
        
        device = None
        for d in devices:
            if d.device_id == device_id:
                device = d
                break
        
        if not device:
            return None
        
        old_version = device.firmware_version
        device.firmware_version = firmware_version
        device.metadata["firmware_history"] = device.metadata.get("firmware_history", [])
        device.metadata["firmware_history"].append({
            "version": old_version,
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        await self._registry.register_device(device)
        
        logger.info(f"Updated {device_id} firmware from {old_version} to {firmware_version}")
        return device
    
    async def get_device_health(self) -> Dict[str, Any]:
        """Get health summary for all devices."""
        devices = await self._registry.list_devices()
        
        now = datetime.now(timezone.utc)
        health = {
            "total_devices": len(devices),
            "online": 0,
            "offline": 0,
            "unknown": 0,
            "by_type": {},
            "devices": []
        }
        
        for device in devices:
            # Check if device was seen recently (within 5 minutes)
            if device.last_seen:
                time_since = now - device.last_seen
                if time_since < timedelta(minutes=5):
                    status = "online"
                    health["online"] += 1
                else:
                    status = "offline"
                    health["offline"] += 1
            else:
                status = "unknown"
                health["unknown"] += 1
            
            # Count by type
            device_type = device.type.value
            if device_type not in health["by_type"]:
                health["by_type"][device_type] = {"total": 0, "online": 0}
            health["by_type"][device_type]["total"] += 1
            if status == "online":
                health["by_type"][device_type]["online"] += 1
            
            health["devices"].append({
                "device_id": device.device_id,
                "name": device.name,
                "type": device_type,
                "status": status,
                "firmware": device.firmware_version,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None
            })
        
        return health
    
    async def get_devices_by_type(self, device_type: DeviceType) -> List[DeviceInfo]:
        """Get all devices of a specific type."""
        return await self._registry.list_devices(device_type.value)
    
    async def get_firmware_report(self) -> Dict[str, Any]:
        """Get firmware version report for all devices."""
        devices = await self._registry.list_devices()
        
        report = {
            "by_device_type": {},
            "outdated_devices": [],
            "firmware_versions": {}
        }
        
        for device in devices:
            device_type = device.type.value
            firmware = device.firmware_version or "unknown"
            
            if device_type not in report["by_device_type"]:
                report["by_device_type"][device_type] = {}
            
            if firmware not in report["by_device_type"][device_type]:
                report["by_device_type"][device_type][firmware] = []
            
            report["by_device_type"][device_type][firmware].append(device.device_id)
            
            # Track all firmware versions
            if firmware not in report["firmware_versions"]:
                report["firmware_versions"][firmware] = 0
            report["firmware_versions"][firmware] += 1
        
        return report


# Singleton
_device_registry: Optional[DeviceRegistry] = None


def get_device_registry() -> DeviceRegistry:
    """Get singleton device registry instance."""
    global _device_registry
    if _device_registry is None:
        _device_registry = DeviceRegistry()
    return _device_registry


async def initialize_devices() -> Dict[str, Any]:
    """Convenience function to initialize all devices."""
    registry = get_device_registry()
    return await registry.initialize_known_devices()
