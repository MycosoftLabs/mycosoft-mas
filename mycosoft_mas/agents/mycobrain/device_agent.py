"""
MycoBrain Device Agent

This agent manages connections to MycoBrain devices, handles command/response
cycles, and maintains device state. It communicates with devices via:
- LoRa (via Gateway)
- Direct UART (for local devices)
- MDP v1 protocol with COBS framing and CRC16
"""

import asyncio
import logging
import json
import serial_asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from enum import Enum

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus
from mycosoft_mas.protocols.mdp_v1 import (
    MDPEncoder,
    MDPDecoder,
    MDPCommand,
    MDPTelemetry,
    MDPEvent,
    MDPMessageType,
)

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """Connection type for MycoBrain device."""
    LORA = "lora"
    UART = "uart"
    GATEWAY = "gateway"  # Via Gateway firmware


class MycoBrainDeviceAgent(BaseAgent):
    """
    Agent for managing a MycoBrain device connection.
    
    Responsibilities:
    - Maintain connection to device (LoRa or UART)
    - Send commands and handle acknowledgements
    - Receive and process telemetry
    - Manage retry logic for commands
    - Track device state and health
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the MycoBrain device agent."""
        super().__init__(agent_id, name, config)
        
        # Device configuration
        self.device_id = config.get("device_id", agent_id)
        self.serial_number = config.get("serial_number", "")
        self.connection_type = ConnectionType(config.get("connection_type", "uart"))
        
        # Connection parameters
        self.uart_port = config.get("uart_port", None)
        self.uart_baudrate = config.get("uart_baudrate", 115200)
        self.lora_address = config.get("lora_address", None)
        self.gateway_url = config.get("gateway_url", None)
        
        # Protocol handlers
        self.encoder = MDPEncoder()
        self.decoder = MDPDecoder()
        
        # Device state
        self.device_status = "offline"
        self.last_telemetry: Optional[MDPTelemetry] = None
        self.last_telemetry_time: Optional[datetime] = None
        self.firmware_version: Optional[str] = None
        self.uptime_seconds: Optional[int] = None
        
        # Command queue and tracking
        self.command_queue: asyncio.Queue = asyncio.Queue()
        self.pending_commands: Dict[int, Dict[str, Any]] = {}  # sequence -> command info
        self.command_timeout = config.get("command_timeout", 5.0)
        self.max_retries = config.get("max_retries", 3)
        
        # Connection
        self.serial_reader: Optional[asyncio.StreamReader] = None
        self.serial_writer: Optional[asyncio.StreamWriter] = None
        self.connection_task: Optional[asyncio.Task] = None
        
        # Data directory
        self.data_dir = Path(config.get("data_dir", f"data/mycobrain/{self.device_id}"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Metrics
        self.metrics.update({
            "telemetry_received": 0,
            "commands_sent": 0,
            "commands_acked": 0,
            "commands_failed": 0,
            "connection_errors": 0,
            "last_connection_time": None,
        })
    
    async def initialize(self) -> bool:
        """Initialize the agent and establish device connection."""
        try:
            self.status = AgentStatus.INITIALIZING
            self.logger.info(f"Initializing MycoBrain device agent for {self.device_id}")
            
            # Start connection
            await self._connect()
            
            # Start background tasks
            self.background_tasks.extend([
                asyncio.create_task(self._process_command_queue()),
                asyncio.create_task(self._process_incoming_data()),
                asyncio.create_task(self._monitor_connection()),
            ])
            
            self.status = AgentStatus.ACTIVE
            self.is_running = True
            self.metrics["start_time"] = datetime.now()
            
            self.logger.info(f"MycoBrain device agent {self.name} initialized successfully")
            return True
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Failed to initialize MycoBrain device agent {self.name}: {str(e)}")
            return False
    
    async def stop(self) -> bool:
        """Stop the agent and close connections."""
        try:
            self.logger.info(f"Stopping MycoBrain device agent {self.name}")
            self.is_running = False
            
            # Close connection
            await self._disconnect()
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            self.status = AgentStatus.STOPPED
            self.logger.info(f"MycoBrain device agent {self.name} stopped")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping agent: {str(e)}")
            return False
    
    async def _connect(self) -> None:
        """Establish connection to device."""
        if self.connection_type == ConnectionType.UART:
            await self._connect_uart()
        elif self.connection_type == ConnectionType.GATEWAY:
            await self._connect_gateway()
        else:
            raise ValueError(f"Unsupported connection type: {self.connection_type}")
    
    async def _connect_uart(self) -> None:
        """Connect via UART."""
        if not self.uart_port:
            raise ValueError("UART port not configured")
        
        try:
            self.serial_reader, self.serial_writer = await serial_asyncio.open_serial_connection(
                url=self.uart_port,
                baudrate=self.uart_baudrate
            )
            self.device_status = "online"
            self.metrics["last_connection_time"] = datetime.now()
            self.logger.info(f"Connected to MycoBrain via UART: {self.uart_port}")
        except Exception as e:
            self.device_status = "error"
            self.metrics["connection_errors"] += 1
            self.logger.error(f"Failed to connect via UART: {str(e)}")
            raise
    
    async def _connect_gateway(self) -> None:
        """Connect via Gateway (HTTP/WebSocket)."""
        # Gateway connection would use HTTP/WebSocket to Gateway firmware
        # For now, mark as connected
        self.device_status = "online"
        self.metrics["last_connection_time"] = datetime.now()
        self.logger.info(f"Connected to MycoBrain via Gateway: {self.gateway_url}")
    
    async def _disconnect(self) -> None:
        """Close device connection."""
        if self.serial_writer:
            self.serial_writer.close()
            await self.serial_writer.wait_closed()
            self.serial_reader = None
            self.serial_writer = None
        
        self.device_status = "offline"
        self.logger.info("Disconnected from MycoBrain device")
    
    async def _process_incoming_data(self) -> None:
        """Process incoming data from device."""
        buffer = bytearray()
        
        while self.is_running:
            try:
                if self.connection_type == ConnectionType.UART:
                    if not self.serial_reader:
                        await asyncio.sleep(0.1)
                        continue
                    
                    # Read data (with timeout)
                    try:
                        data = await asyncio.wait_for(
                            self.serial_reader.read(1024),
                            timeout=1.0
                        )
                        if not data:
                            await asyncio.sleep(0.1)
                            continue
                    except asyncio.TimeoutError:
                        continue
                    
                    buffer.extend(data)
                    
                    # Look for COBS frame delimiter (0x00)
                    while 0x00 in buffer:
                        delimiter_index = buffer.index(0x00)
                        frame_data = bytes(buffer[:delimiter_index + 1])
                        buffer = buffer[delimiter_index + 1:]
                        
                        if len(frame_data) > 1:
                            await self._handle_frame(frame_data)
                
                elif self.connection_type == ConnectionType.GATEWAY:
                    # Gateway would provide NDJSON stream
                    # For now, simulate periodic telemetry
                    await asyncio.sleep(10)
                
            except Exception as e:
                self.logger.error(f"Error processing incoming data: {str(e)}")
                self.metrics["connection_errors"] += 1
                await asyncio.sleep(1)
    
    async def _handle_frame(self, frame_data: bytes) -> None:
        """Handle a decoded MDP frame."""
        try:
            frame, parsed = self.decoder.decode(frame_data)
            
            if frame.message_type == MDPMessageType.TELEMETRY:
                await self._handle_telemetry(frame, parsed)
            elif frame.message_type == MDPMessageType.ACK:
                await self._handle_ack(frame, parsed)
            elif frame.message_type == MDPMessageType.EVENT:
                await self._handle_event(frame, parsed)
            
        except Exception as e:
            self.logger.error(f"Error handling frame: {str(e)}")
    
    async def _handle_telemetry(self, frame: Any, telemetry: MDPTelemetry) -> None:
        """Handle telemetry message."""
        self.last_telemetry = telemetry
        self.last_telemetry_time = datetime.now()
        self.firmware_version = telemetry.firmware_version
        self.uptime_seconds = telemetry.uptime_seconds
        self.metrics["telemetry_received"] += 1
        
        # Save telemetry to file
        telemetry_file = self.data_dir / f"telemetry_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(telemetry_file, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "sequence": frame.sequence,
                "telemetry": telemetry.to_dict()
            }) + "\n")
        
        # Emit event for other agents/services
        await self._emit_event("telemetry_received", {
            "device_id": self.device_id,
            "telemetry": telemetry.to_dict(),
            "sequence": frame.sequence
        })
    
    async def _handle_ack(self, frame: Any, ack_data: Dict[str, Any]) -> None:
        """Handle acknowledgment message."""
        ack_sequence = ack_data.get("ack_sequence")
        success = ack_data.get("success", True)
        
        if ack_sequence in self.pending_commands:
            command_info = self.pending_commands.pop(ack_sequence)
            if success:
                self.metrics["commands_acked"] += 1
                self.logger.debug(f"Command {ack_sequence} acknowledged")
            else:
                self.metrics["commands_failed"] += 1
                self.logger.warning(f"Command {ack_sequence} failed")
            
            # Resolve any waiting futures
            if "future" in command_info:
                command_info["future"].set_result(success)
    
    async def _handle_event(self, frame: Any, event: MDPEvent) -> None:
        """Handle event message."""
        self.logger.info(f"Device event: {event.event_type} - {event.message}")
        
        # Emit event for other agents/services
        await self._emit_event("device_event", {
            "device_id": self.device_id,
            "event": event.to_dict(),
            "sequence": frame.sequence
        })
    
    async def send_command(
        self,
        command_type: str,
        parameters: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> bool:
        """
        Send a command to the device.
        
        Args:
            command_type: Type of command (e.g., "set_mosfet", "set_telemetry_interval")
            parameters: Command parameters
            timeout: Optional timeout in seconds (defaults to command_timeout)
        
        Returns:
            True if command was acknowledged, False otherwise
        """
        command = MDPCommand(
            command_id=len(self.pending_commands),
            command_type=command_type,
            parameters=parameters
        )
        
        # Encode command
        command_bytes = self.encoder.encode_command(command)
        
        # Create future for async waiting
        future = asyncio.Future()
        sequence = (self.encoder.sequence_counter - 1) % 65536
        
        # Track pending command
        self.pending_commands[sequence] = {
            "command": command,
            "sent_time": datetime.now(),
            "retries": 0,
            "future": future
        }
        
        # Send command
        await self._send_bytes(command_bytes)
        self.metrics["commands_sent"] += 1
        
        # Wait for ACK with timeout
        timeout = timeout or self.command_timeout
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            # Retry logic
            command_info = self.pending_commands.get(sequence)
            if command_info and command_info["retries"] < self.max_retries:
                command_info["retries"] += 1
                await self._send_bytes(command_bytes)
                try:
                    result = await asyncio.wait_for(future, timeout=timeout)
                    return result
                except asyncio.TimeoutError:
                    pass
            
            self.pending_commands.pop(sequence, None)
            self.metrics["commands_failed"] += 1
            return False
    
    async def _send_bytes(self, data: bytes) -> None:
        """Send bytes to device."""
        if self.connection_type == ConnectionType.UART:
            if self.serial_writer:
                self.serial_writer.write(data)
                await self.serial_writer.drain()
        elif self.connection_type == ConnectionType.GATEWAY:
            # Send via Gateway API
            # Implementation depends on Gateway API
            pass
    
    async def _process_command_queue(self) -> None:
        """Process queued commands."""
        while self.is_running:
            try:
                command = await asyncio.wait_for(
                    self.command_queue.get(),
                    timeout=1.0
                )
                await self.send_command(
                    command["command_type"],
                    command["parameters"],
                    command.get("timeout")
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing command: {str(e)}")
    
    async def _monitor_connection(self) -> None:
        """Monitor device connection health."""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Check if we've received telemetry recently
                if self.last_telemetry_time:
                    time_since_telemetry = (datetime.now() - self.last_telemetry_time).total_seconds()
                    if time_since_telemetry > 120:  # No telemetry for 2 minutes
                        self.logger.warning(f"No telemetry received for {time_since_telemetry:.0f} seconds")
                        self.device_status = "degraded"
                
                # Check connection
                if self.device_status == "offline":
                    self.logger.info("Attempting to reconnect...")
                    try:
                        await self._connect()
                    except Exception as e:
                        self.logger.error(f"Reconnection failed: {str(e)}")
                
            except Exception as e:
                self.logger.error(f"Error in connection monitor: {str(e)}")
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit event for other agents/services."""
        # This would integrate with MAS event bus
        # For now, just log
        self.logger.debug(f"Event: {event_type} - {data}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get device status."""
        return {
            "device_id": self.device_id,
            "serial_number": self.serial_number,
            "status": self.device_status,
            "connection_type": self.connection_type.value,
            "firmware_version": self.firmware_version,
            "uptime_seconds": self.uptime_seconds,
            "last_telemetry_time": self.last_telemetry_time.isoformat() if self.last_telemetry_time else None,
            "metrics": self.metrics,
        }
