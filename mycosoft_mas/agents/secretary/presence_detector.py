"""
Presence Detector for Secretary Agent

This module implements a presence detection service that integrates with various
devices to detect user presence and location.
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable, Awaitable
from pathlib import Path
from enum import Enum, auto

from .schedule_manager import (
    PresenceSource, LocationType, ActivityType,
    ScheduleManager
)

class DeviceType(Enum):
    """Types of devices that can be used for presence detection"""
    PHONE = auto()
    SMARTWATCH = auto()
    MICROPHONE = auto()
    THERMOSTAT = auto()
    MOTION_SENSOR = auto()
    CAMERA = auto()
    DOOR_SENSOR = auto()
    LIGHT_SENSOR = auto()
    COMPUTER = auto()
    SMART_SPEAKER = auto()
    WEARABLE = auto()
    SMART_BULB = auto()
    SMART_PLUG = auto()
    SMART_LOCK = auto()
    SMART_DOORBELL = auto()
    SMART_CAMERA = auto()
    SMART_THERMOSTAT = auto()
    SMART_VACUUM = auto()
    SMART_ROBOT = auto()
    SMART_ASSISTANT = auto()
    CUSTOM = auto()

class DeviceStatus(Enum):
    """Status of a device"""
    ONLINE = auto()
    OFFLINE = auto()
    ERROR = auto()
    UNKNOWN = auto()

class DetectionMethod(Enum):
    """Methods used for presence detection"""
    GPS = auto()
    BLUETOOTH = auto()
    WIFI = auto()
    SOUND = auto()
    MOTION = auto()
    TEMPERATURE = auto()
    LIGHT = auto()
    DOOR = auto()
    KEYBOARD = auto()
    MOUSE = auto()
    CAMERA = auto()
    VOICE = auto()
    HEART_RATE = auto()
    STEP_COUNT = auto()
    SLEEP = auto()
    CUSTOM = auto()

@dataclass
class Device:
    """Information about a device used for presence detection"""
    device_id: str
    device_type: DeviceType
    name: str
    location: LocationType
    status: DeviceStatus
    detection_methods: List[DetectionMethod]
    last_seen: datetime
    battery_level: Optional[int] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    firmware_version: Optional[str] = None
    custom_data: Dict[str, Any] = field(default_factory=dict)

class PresenceDetector:
    """
    Service that detects user presence using various devices.
    
    This class:
    1. Manages device connections and status
    2. Processes presence detection events
    3. Integrates with the schedule manager
    4. Provides presence information to the secretary agent
    """
    
    def __init__(self, config: Dict[str, Any], schedule_manager: ScheduleManager):
        """
        Initialize the presence detector.
        
        Args:
            config: Configuration dictionary for the presence detector
            schedule_manager: Schedule manager instance
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.schedule_manager = schedule_manager
        
        # Create data directory
        self.data_dir = Path("data/secretary/presence")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Device registry
        self.devices: Dict[str, Device] = {}
        
        # Detection handlers
        self.detection_handlers: Dict[DetectionMethod, List[Callable]] = {}
        
        # Metrics
        self.metrics = {
            "devices_registered": 0,
            "detection_events": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "device_errors": 0
        }
        
        # Load data
        self._load_data()
    
    def _load_data(self) -> None:
        """Load device data from disk"""
        try:
            # Load devices
            devices_file = self.data_dir / "devices.json"
            if devices_file.exists():
                with open(devices_file, "r") as f:
                    devices_data = json.load(f)
                    
                    for device_data in devices_data:
                        device = Device(
                            device_id=device_data["device_id"],
                            device_type=DeviceType[device_data["device_type"]],
                            name=device_data["name"],
                            location=LocationType[device_data["location"]],
                            status=DeviceStatus[device_data["status"]],
                            detection_methods=[
                                DetectionMethod[m] for m in device_data["detection_methods"]
                            ],
                            last_seen=datetime.fromisoformat(device_data["last_seen"]),
                            battery_level=device_data.get("battery_level"),
                            ip_address=device_data.get("ip_address"),
                            mac_address=device_data.get("mac_address"),
                            firmware_version=device_data.get("firmware_version"),
                            custom_data=device_data.get("custom_data", {})
                        )
                        
                        self.devices[device.device_id] = device
            
            # Load metrics
            metrics_file = self.data_dir / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file, "r") as f:
                    self.metrics = json.load(f)
                    
        except Exception as e:
            self.logger.error(f"Error loading device data: {str(e)}")
    
    async def save_data(self) -> None:
        """Save device data to disk"""
        try:
            # Save devices
            devices_file = self.data_dir / "devices.json"
            devices_data = []
            
            for device in self.devices.values():
                device_data = {
                    "device_id": device.device_id,
                    "device_type": device.device_type.name,
                    "name": device.name,
                    "location": device.location.name,
                    "status": device.status.name,
                    "detection_methods": [m.name for m in device.detection_methods],
                    "last_seen": device.last_seen.isoformat(),
                    "battery_level": device.battery_level,
                    "ip_address": device.ip_address,
                    "mac_address": device.mac_address,
                    "firmware_version": device.firmware_version,
                    "custom_data": device.custom_data
                }
                devices_data.append(device_data)
            
            with open(devices_file, "w") as f:
                json.dump(devices_data, f, indent=2)
            
            # Save metrics
            metrics_file = self.data_dir / "metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving device data: {str(e)}")
    
    async def start(self) -> None:
        """Start the presence detector"""
        self.logger.info("Starting presence detector")
        
        # Start background tasks
        asyncio.create_task(self._periodic_save())
        asyncio.create_task(self._check_devices())
        
        self.logger.info("Presence detector started")
    
    async def stop(self) -> None:
        """Stop the presence detector"""
        self.logger.info("Stopping presence detector")
        
        # Save data
        await self.save_data()
        
        self.logger.info("Presence detector stopped")
    
    # Device Management Methods
    
    async def register_device(
        self,
        device_type: DeviceType,
        name: str,
        location: LocationType,
        detection_methods: List[DetectionMethod],
        ip_address: Optional[str] = None,
        mac_address: Optional[str] = None,
        firmware_version: Optional[str] = None,
        custom_data: Dict[str, Any] = None
    ) -> str:
        """
        Register a new device for presence detection.
        
        Args:
            device_type: Type of device
            name: Device name
            location: Device location
            detection_methods: Methods used for detection
            ip_address: Device IP address (optional)
            mac_address: Device MAC address (optional)
            firmware_version: Device firmware version (optional)
            custom_data: Additional device data (optional)
            
        Returns:
            str: Device ID
        """
        device_id = str(uuid.uuid4())
        
        device = Device(
            device_id=device_id,
            device_type=device_type,
            name=name,
            location=location,
            status=DeviceStatus.ONLINE,
            detection_methods=detection_methods,
            last_seen=datetime.now(),
            ip_address=ip_address,
            mac_address=mac_address,
            firmware_version=firmware_version,
            custom_data=custom_data or {}
        )
        
        self.devices[device_id] = device
        self.metrics["devices_registered"] += 1
        
        await self.save_data()
        
        return device_id
    
    async def update_device_status(
        self,
        device_id: str,
        status: DeviceStatus,
        battery_level: Optional[int] = None
    ) -> None:
        """
        Update device status.
        
        Args:
            device_id: Device ID
            status: New device status
            battery_level: Device battery level (optional)
        """
        if device_id in self.devices:
            device = self.devices[device_id]
            device.status = status
            device.last_seen = datetime.now()
            
            if battery_level is not None:
                device.battery_level = battery_level
            
            if status == DeviceStatus.ERROR:
                self.metrics["device_errors"] += 1
            
            await self.save_data()
    
    async def remove_device(self, device_id: str) -> None:
        """
        Remove a device from the registry.
        
        Args:
            device_id: Device ID
        """
        if device_id in self.devices:
            del self.devices[device_id]
            await self.save_data()
    
    async def get_device(self, device_id: str) -> Optional[Device]:
        """
        Get device information.
        
        Args:
            device_id: Device ID
            
        Returns:
            Optional[Device]: Device information, or None if not found
        """
        return self.devices.get(device_id)
    
    async def get_devices_by_location(self, location: LocationType) -> List[Device]:
        """
        Get devices in a specific location.
        
        Args:
            location: Location to search for
            
        Returns:
            List[Device]: List of devices in the location
        """
        return [
            device for device in self.devices.values()
            if device.location == location
        ]
    
    async def get_devices_by_type(self, device_type: DeviceType) -> List[Device]:
        """
        Get devices of a specific type.
        
        Args:
            device_type: Device type to search for
            
        Returns:
            List[Device]: List of devices of the specified type
        """
        return [
            device for device in self.devices.values()
            if device.device_type == device_type
        ]
    
    # Detection Methods
    
    async def register_detection_handler(
        self,
        detection_method: DetectionMethod,
        handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Register a handler for a detection method.
        
        Args:
            detection_method: Detection method
            handler: Async function to handle detection events
        """
        if detection_method not in self.detection_handlers:
            self.detection_handlers[detection_method] = []
        
        self.detection_handlers[detection_method].append(handler)
    
    async def process_detection_event(
        self,
        device_id: str,
        detection_method: DetectionMethod,
        event_data: Dict[str, Any]
    ) -> None:
        """
        Process a detection event from a device.
        
        Args:
            device_id: Device ID
            detection_method: Detection method
            event_data: Event data
        """
        try:
            # Update device last seen
            if device_id in self.devices:
                device = self.devices[device_id]
                device.last_seen = datetime.now()
            
            # Call detection handlers
            if detection_method in self.detection_handlers:
                for handler in self.detection_handlers[detection_method]:
                    try:
                        await handler(event_data)
                    except Exception as e:
                        self.logger.error(f"Error in detection handler: {str(e)}")
            
            # Update metrics
            self.metrics["detection_events"] += 1
            
            # Save data
            await self.save_data()
            
        except Exception as e:
            self.logger.error(f"Error processing detection event: {str(e)}")
    
    async def detect_presence(
        self,
        device_id: str,
        location: LocationType,
        activity: Optional[ActivityType] = None,
        confidence: float = 1.0
    ) -> None:
        """
        Detect user presence and update the schedule manager.
        
        Args:
            device_id: Device ID
            location: Detected location
            activity: Detected activity (optional)
            confidence: Detection confidence (0.0 to 1.0)
        """
        try:
            # Map device type to presence source
            device_type_to_source = {
                DeviceType.PHONE: PresenceSource.PHONE,
                DeviceType.SMARTWATCH: PresenceSource.SMARTWATCH,
                DeviceType.MICROPHONE: PresenceSource.MICROPHONE,
                DeviceType.THERMOSTAT: PresenceSource.THERMOSTAT,
                DeviceType.MOTION_SENSOR: PresenceSource.MOTION_SENSOR,
                DeviceType.CAMERA: PresenceSource.CAMERA,
                DeviceType.DOOR_SENSOR: PresenceSource.DOOR_SENSOR,
                DeviceType.LIGHT_SENSOR: PresenceSource.LIGHT_SENSOR,
                DeviceType.COMPUTER: PresenceSource.COMPUTER
            }
            
            # Get device
            device = await self.get_device(device_id)
            if not device:
                return
            
            # Get presence source
            presence_source = device_type_to_source.get(device.device_type)
            if not presence_source:
                return
            
            # Update schedule manager
            await self.schedule_manager.update_presence(
                presence_source,
                location,
                activity
            )
            
            # Log detection
            self.logger.info(
                f"Presence detected: {presence_source.name} at {location.name}"
                + (f" doing {activity.name}" if activity else "")
                + f" (confidence: {confidence:.2f})"
            )
            
        except Exception as e:
            self.logger.error(f"Error detecting presence: {str(e)}")
    
    async def clear_presence(self, device_id: str) -> None:
        """
        Clear presence detection for a device.
        
        Args:
            device_id: Device ID
        """
        try:
            # Map device type to presence source
            device_type_to_source = {
                DeviceType.PHONE: PresenceSource.PHONE,
                DeviceType.SMARTWATCH: PresenceSource.SMARTWATCH,
                DeviceType.MICROPHONE: PresenceSource.MICROPHONE,
                DeviceType.THERMOSTAT: PresenceSource.THERMOSTAT,
                DeviceType.MOTION_SENSOR: PresenceSource.MOTION_SENSOR,
                DeviceType.CAMERA: PresenceSource.CAMERA,
                DeviceType.DOOR_SENSOR: PresenceSource.DOOR_SENSOR,
                DeviceType.LIGHT_SENSOR: PresenceSource.LIGHT_SENSOR,
                DeviceType.COMPUTER: PresenceSource.COMPUTER
            }
            
            # Get device
            device = await self.get_device(device_id)
            if not device:
                return
            
            # Get presence source
            presence_source = device_type_to_source.get(device.device_type)
            if not presence_source:
                return
            
            # Clear presence in schedule manager
            await self.schedule_manager.clear_presence(presence_source)
            
            # Log clearing
            self.logger.info(f"Presence cleared: {presence_source.name}")
            
        except Exception as e:
            self.logger.error(f"Error clearing presence: {str(e)}")
    
    # Background Tasks
    
    async def _periodic_save(self) -> None:
        """Periodically save data to disk"""
        while True:
            try:
                await asyncio.sleep(300)  # Save every 5 minutes
                await self.save_data()
            except Exception as e:
                self.logger.error(f"Error in periodic save: {str(e)}")
                await asyncio.sleep(60)
    
    async def _check_devices(self) -> None:
        """Periodically check device status"""
        while True:
            try:
                now = datetime.now()
                
                # Check for offline devices
                for device_id, device in self.devices.items():
                    # Consider device offline if not seen in 5 minutes
                    if (now - device.last_seen) > timedelta(minutes=5):
                        if device.status != DeviceStatus.OFFLINE:
                            await self.update_device_status(
                                device_id,
                                DeviceStatus.OFFLINE
                            )
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error checking devices: {str(e)}")
                await asyncio.sleep(60) 