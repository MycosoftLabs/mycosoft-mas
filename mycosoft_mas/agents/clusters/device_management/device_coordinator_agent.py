"""
Mycosoft Multi-Agent System (MAS) - Device Coordinator Agent

This module implements the DeviceCoordinatorAgent, which manages device connections,
coordinates data collection, and handles device communication.
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

class DeviceType(Enum):
    """Enumeration of device types."""
    SENSOR = "sensor"
    CAMERA = "camera"
    CONTROLLER = "controller"
    DISPLAY = "display"
    GATEWAY = "gateway"

class DeviceStatus(Enum):
    """Enumeration of device statuses."""
    OFFLINE = "offline"
    ONLINE = "online"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    CALIBRATING = "calibrating"

class ConnectionType(Enum):
    """Enumeration of connection types."""
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    ZIGBEE = "zigbee"
    ETHERNET = "ethernet"
    USB = "usb"

@dataclass
class DeviceConfig:
    """Data class for storing device configuration."""
    device_id: str
    device_type: DeviceType
    name: str
    description: str
    connection_type: ConnectionType
    connection_params: Dict[str, Any]
    sampling_rate: int
    calibration_params: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@dataclass
class DeviceData:
    """Data class for storing device data."""
    device_id: str
    timestamp: datetime
    data_type: str
    values: Dict[str, Any]
    metadata: Dict[str, Any]

@dataclass
class DeviceCommand:
    """Data class for storing device commands."""
    device_id: str
    command_type: str
    parameters: Dict[str, Any]
    priority: int
    timestamp: datetime
    metadata: Dict[str, Any]

class DeviceCoordinatorAgent(BaseAgent):
    """
    Agent responsible for managing device connections, coordinating data collection,
    and handling device communication.
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the DeviceCoordinatorAgent."""
        super().__init__(agent_id, name, config)
        
        # Initialize storage
        self.devices: Dict[str, DeviceConfig] = {}
        self.device_data: Dict[str, List[DeviceData]] = {}
        self.device_commands: Dict[str, List[DeviceCommand]] = {}
        self.connected_devices: Set[str] = set()
        
        # Initialize directories
        self.data_dir = Path(config.get('data_dir', 'data/devices'))
        self.command_dir = Path(config.get('command_dir', 'data/commands'))
        
        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.command_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize queues
        self.connection_queue = asyncio.Queue()
        self.data_queue = asyncio.Queue()
        self.command_queue = asyncio.Queue()
        
        # Initialize metrics
        self.metrics.update({
            "devices_registered": 0,
            "devices_connected": 0,
            "devices_disconnected": 0,
            "data_points_received": 0,
            "commands_sent": 0,
            "commands_executed": 0,
            "connection_errors": 0
        })

    async def initialize(self) -> bool:
        """Initialize the agent and its services."""
        try:
            self.status = AgentStatus.INITIALIZING
            self.logger.info(f"Initializing DeviceCoordinatorAgent {self.name}")
            
            # Load existing devices
            await self._load_devices()
            
            # Start background tasks
            self.background_tasks.extend([
                asyncio.create_task(self._process_connection_queue()),
                asyncio.create_task(self._process_data_queue()),
                asyncio.create_task(self._process_command_queue())
            ])
            
            self.status = AgentStatus.ACTIVE
            self.is_running = True
            self.metrics["start_time"] = datetime.now()
            
            self.logger.info(f"DeviceCoordinatorAgent {self.name} initialized successfully")
            return True
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Failed to initialize DeviceCoordinatorAgent {self.name}: {str(e)}")
            return False

    async def stop(self) -> bool:
        """Stop the agent and cleanup resources."""
        try:
            self.logger.info(f"Stopping DeviceCoordinatorAgent {self.name}")
            self.is_running = False
            
            # Disconnect all devices
            for device_id in self.connected_devices:
                await self.disconnect_device(device_id)
            
            # Save devices
            await self._save_devices()
            
            # Cancel background tasks
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self.background_tasks = []
            self.status = AgentStatus.STOPPED
            
            self.logger.info(f"DeviceCoordinatorAgent {self.name} stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping DeviceCoordinatorAgent {self.name}: {str(e)}")
            return False

    async def register_device(self, config: DeviceConfig) -> bool:
        """
        Register a new device.
        
        Args:
            config: Device configuration
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            # Check if device already exists
            if config.device_id in self.devices:
                raise ValueError(f"Device already registered: {config.device_id}")
            
            # Store device
            self.devices[config.device_id] = config
            self.device_data[config.device_id] = []
            self.device_commands[config.device_id] = []
            
            # Save device
            await self._save_device(config.device_id)
            
            self.metrics["devices_registered"] += 1
            self.logger.info(f"Registered device: {config.device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering device: {str(e)}")
            return False

    async def unregister_device(self, device_id: str) -> bool:
        """
        Unregister a device.
        
        Args:
            device_id: ID of the device to unregister
            
        Returns:
            bool: True if unregistration was successful, False otherwise
        """
        try:
            # Check if device exists
            if device_id not in self.devices:
                raise ValueError(f"Device not found: {device_id}")
            
            # Disconnect device if connected
            if device_id in self.connected_devices:
                await self.disconnect_device(device_id)
            
            # Remove device
            del self.devices[device_id]
            del self.device_data[device_id]
            del self.device_commands[device_id]
            
            # Delete device file
            file_path = self.data_dir / f"{device_id}.json"
            if file_path.exists():
                file_path.unlink()
            
            self.logger.info(f"Unregistered device: {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error unregistering device {device_id}: {str(e)}")
            return False

    async def connect_device(self, device_id: str) -> bool:
        """
        Connect to a device.
        
        Args:
            device_id: ID of the device to connect to
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            # Check if device exists
            if device_id not in self.devices:
                raise ValueError(f"Device not found: {device_id}")
            
            # Check if device is already connected
            if device_id in self.connected_devices:
                raise ValueError(f"Device already connected: {device_id}")
            
            # Add to connection queue
            await self.connection_queue.put({
                "device_id": device_id,
                "action": "connect"
            })
            
            self.logger.info(f"Queued connection for device: {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to device {device_id}: {str(e)}")
            return False

    async def disconnect_device(self, device_id: str) -> bool:
        """
        Disconnect from a device.
        
        Args:
            device_id: ID of the device to disconnect from
            
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        try:
            # Check if device exists
            if device_id not in self.devices:
                raise ValueError(f"Device not found: {device_id}")
            
            # Check if device is connected
            if device_id not in self.connected_devices:
                raise ValueError(f"Device not connected: {device_id}")
            
            # Add to connection queue
            await self.connection_queue.put({
                "device_id": device_id,
                "action": "disconnect"
            })
            
            self.logger.info(f"Queued disconnection for device: {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from device {device_id}: {str(e)}")
            return False

    async def send_command(self, device_id: str, command: DeviceCommand) -> bool:
        """
        Send a command to a device.
        
        Args:
            device_id: ID of the device to send command to
            command: The command to send
            
        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        try:
            # Check if device exists
            if device_id not in self.devices:
                raise ValueError(f"Device not found: {device_id}")
            
            # Check if device is connected
            if device_id not in self.connected_devices:
                raise ValueError(f"Device not connected: {device_id}")
            
            # Add to command queue
            await self.command_queue.put({
                "device_id": device_id,
                "command": command
            })
            
            self.logger.info(f"Queued command for device: {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending command to device {device_id}: {str(e)}")
            return False

    async def get_device_data(self, device_id: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> List[DeviceData]:
        """
        Get data from a device.
        
        Args:
            device_id: ID of the device to get data from
            start_time: Start time for data range
            end_time: End time for data range
            
        Returns:
            List[DeviceData]: List of device data points
        """
        try:
            # Check if device exists
            if device_id not in self.devices:
                raise ValueError(f"Device not found: {device_id}")
            
            # Get all data
            data = self.device_data[device_id]
            
            # Filter by time range if specified
            if start_time or end_time:
                data = [
                    point for point in data
                    if (not start_time or point.timestamp >= start_time) and
                       (not end_time or point.timestamp <= end_time)
                ]
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting data from device {device_id}: {str(e)}")
            return []

    async def _load_devices(self):
        """Load devices from storage."""
        try:
            # Load device files
            for file_path in self.data_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        
                        # Convert to DeviceConfig
                        config = self._dict_to_device_config(data)
                        
                        # Store device
                        self.devices[config.device_id] = config
                        self.device_data[config.device_id] = []
                        self.device_commands[config.device_id] = []
                        
                        self.logger.info(f"Loaded device: {config.device_id}")
                except Exception as e:
                    self.logger.error(f"Error loading device from {file_path}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error loading devices: {str(e)}")

    async def _save_devices(self):
        """Save devices to storage."""
        try:
            # Save each device
            for device_id, config in self.devices.items():
                try:
                    # Convert to dictionary
                    data = self._device_config_to_dict(config)
                    
                    # Save to file
                    file_path = self.data_dir / f"{device_id}.json"
                    with open(file_path, 'w') as f:
                        json.dump(data, f, default=str)
                except Exception as e:
                    self.logger.error(f"Error saving device {device_id}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error saving devices: {str(e)}")

    async def _save_device(self, device_id: str):
        """Save a device to storage."""
        try:
            if device_id in self.devices:
                # Convert to dictionary
                data = self._device_config_to_dict(self.devices[device_id])
                
                # Save to file
                file_path = self.data_dir / f"{device_id}.json"
                with open(file_path, 'w') as f:
                    json.dump(data, f, default=str)
        except Exception as e:
            self.logger.error(f"Error saving device {device_id}: {str(e)}")

    async def _process_connection_queue(self):
        """Process the connection queue."""
        while self.is_running:
            try:
                task = await self.connection_queue.get()
                device_id = task.get('device_id')
                action = task.get('action')
                
                if device_id in self.devices:
                    if action == 'connect':
                        # Connect to device
                        success = await self._connect_to_device(device_id)
                        
                        if success:
                            self.connected_devices.add(device_id)
                            self.metrics["devices_connected"] += 1
                    elif action == 'disconnect':
                        # Disconnect from device
                        success = await self._disconnect_from_device(device_id)
                        
                        if success:
                            self.connected_devices.remove(device_id)
                            self.metrics["devices_disconnected"] += 1
                
                self.connection_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing connection queue: {str(e)}")
                await asyncio.sleep(1)

    async def _process_data_queue(self):
        """Process the data queue."""
        while self.is_running:
            try:
                task = await self.data_queue.get()
                device_id = task.get('device_id')
                data = task.get('data')
                
                if device_id in self.devices:
                    # Store data
                    self.device_data[device_id].append(data)
                    
                    # Save data to file
                    file_path = self.data_dir / f"{device_id}_data.json"
                    with open(file_path, 'a') as f:
                        json.dump(self._device_data_to_dict(data), f)
                        f.write('\n')
                    
                    self.metrics["data_points_received"] += 1
                
                self.data_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing data queue: {str(e)}")
                await asyncio.sleep(1)

    async def _process_command_queue(self):
        """Process the command queue."""
        while self.is_running:
            try:
                task = await self.command_queue.get()
                device_id = task.get('device_id')
                command = task.get('command')
                
                if device_id in self.devices and device_id in self.connected_devices:
                    # Send command to device
                    success = await self._send_command_to_device(device_id, command)
                    
                    if success:
                        # Store command
                        self.device_commands[device_id].append(command)
                        
                        # Save command to file
                        file_path = self.command_dir / f"{device_id}_commands.json"
                        with open(file_path, 'a') as f:
                            json.dump(self._device_command_to_dict(command), f)
                            f.write('\n')
                        
                        self.metrics["commands_sent"] += 1
                        self.metrics["commands_executed"] += 1
                
                self.command_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing command queue: {str(e)}")
                await asyncio.sleep(1)

    async def _connect_to_device(self, device_id: str) -> bool:
        """
        Connect to a device.
        
        Args:
            device_id: ID of the device to connect to
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            # Get device config
            config = self.devices[device_id]
            
            # This is a placeholder for actual device connection logic
            # In a real implementation, this would use the appropriate protocol
            # based on the connection_type
            
            # Simulate connection delay
            await asyncio.sleep(1)
            
            self.logger.info(f"Connected to device: {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to device {device_id}: {str(e)}")
            self.metrics["connection_errors"] += 1
            return False

    async def _disconnect_from_device(self, device_id: str) -> bool:
        """
        Disconnect from a device.
        
        Args:
            device_id: ID of the device to disconnect from
            
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        try:
            # Get device config
            config = self.devices[device_id]
            
            # This is a placeholder for actual device disconnection logic
            # In a real implementation, this would use the appropriate protocol
            # based on the connection_type
            
            # Simulate disconnection delay
            await asyncio.sleep(1)
            
            self.logger.info(f"Disconnected from device: {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from device {device_id}: {str(e)}")
            self.metrics["connection_errors"] += 1
            return False

    async def _send_command_to_device(self, device_id: str, command: DeviceCommand) -> bool:
        """
        Send a command to a device.
        
        Args:
            device_id: ID of the device to send command to
            command: The command to send
            
        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        try:
            # Get device config
            config = self.devices[device_id]
            
            # This is a placeholder for actual command sending logic
            # In a real implementation, this would use the appropriate protocol
            # based on the connection_type
            
            # Simulate command delay
            await asyncio.sleep(0.5)
            
            self.logger.info(f"Sent command to device: {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending command to device {device_id}: {str(e)}")
            return False

    def _device_config_to_dict(self, config: DeviceConfig) -> Dict[str, Any]:
        """Convert DeviceConfig to dictionary."""
        return {
            "device_id": config.device_id,
            "device_type": config.device_type.value,
            "name": config.name,
            "description": config.description,
            "connection_type": config.connection_type.value,
            "connection_params": config.connection_params,
            "sampling_rate": config.sampling_rate,
            "calibration_params": config.calibration_params,
            "metadata": config.metadata,
            "created_at": config.created_at,
            "updated_at": config.updated_at
        }

    def _dict_to_device_config(self, data: Dict[str, Any]) -> DeviceConfig:
        """Convert dictionary to DeviceConfig."""
        return DeviceConfig(
            device_id=data.get("device_id", ""),
            device_type=DeviceType(data.get("device_type", "sensor")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            connection_type=ConnectionType(data.get("connection_type", "wifi")),
            connection_params=data.get("connection_params", {}),
            sampling_rate=data.get("sampling_rate", 60),
            calibration_params=data.get("calibration_params", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )

    def _device_data_to_dict(self, data: DeviceData) -> Dict[str, Any]:
        """Convert DeviceData to dictionary."""
        return {
            "device_id": data.device_id,
            "timestamp": data.timestamp,
            "data_type": data.data_type,
            "values": data.values,
            "metadata": data.metadata
        }

    def _device_command_to_dict(self, command: DeviceCommand) -> Dict[str, Any]:
        """Convert DeviceCommand to dictionary."""
        return {
            "device_id": command.device_id,
            "command_type": command.command_type,
            "parameters": command.parameters,
            "priority": command.priority,
            "timestamp": command.timestamp,
            "metadata": command.metadata
        } 