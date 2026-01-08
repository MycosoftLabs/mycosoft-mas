"""
MycoBrain Machine Mode Handler

Manages board sessions with NDJSON protocol support.
Provides bootstrap, peripheral discovery, and telemetry streaming.
"""

import asyncio
import logging
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import serial
import threading
from queue import Queue, Empty

from .protocol import (
    NDJSONParser,
    CommandBuilder,
    BoardSession,
    PeripheralDescriptor,
    PeripheralRegistry,
    TelemetryEvent,
    TelemetryStore,
    MessageType,
)

logger = logging.getLogger(__name__)


class MachineModeBridge:
    """
    Bridge for communicating with MycoBoard in machine mode.
    Handles:
    - Serial connection management
    - NDJSON parsing
    - Command dispatch
    - Telemetry streaming
    - Peripheral discovery
    """
    
    BOOTSTRAP_SEQUENCE = [
        ("mode machine", 0.3),
        ("dbg off", 0.2),
        ("fmt json", 0.2),
        ("scan", 0.5),
        ("status", 0.5),
    ]
    
    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        device_id: str = None,
        on_telemetry: Callable[[TelemetryEvent], None] = None,
        on_peripheral: Callable[[PeripheralDescriptor], None] = None,
        on_message: Callable[[Dict[str, Any]], None] = None,
    ):
        self.port = port
        self.baudrate = baudrate
        self.device_id = device_id or f"mycobrain-{port.split('/')[-1].replace(':', '-')}"
        
        self.serial: Optional[serial.Serial] = None
        self.parser = NDJSONParser(on_message=self._handle_message)
        self.telemetry_store = TelemetryStore()
        
        self.session: Optional[BoardSession] = None
        self.connected = False
        self.machine_mode_active = False
        
        # Callbacks
        self.on_telemetry = on_telemetry
        self.on_peripheral = on_peripheral
        self.on_message = on_message
        
        # Response queue for synchronous commands
        self._response_queue: Queue = Queue()
        self._pending_command: Optional[str] = None
        
        # Reader thread
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reader = threading.Event()
    
    def connect(self) -> bool:
        """Establish serial connection"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                write_timeout=1,
            )
            self.connected = True
            self.session = BoardSession(
                board_id=self.device_id,
                port=self.port,
                connected_at=datetime.now().isoformat(),
                last_seen=datetime.now().isoformat(),
            )
            
            # Start reader thread
            self._stop_reader.clear()
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()
            
            logger.info(f"Connected to {self.port} as {self.device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.port}: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Close connection"""
        self._stop_reader.set()
        if self._reader_thread:
            self._reader_thread.join(timeout=2)
        
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except Exception as e:
                logger.error(f"Error closing serial: {e}")
        
        self.connected = False
        self.machine_mode_active = False
        logger.info(f"Disconnected from {self.port}")
    
    def bootstrap(self) -> bool:
        """
        Run bootstrap sequence to initialize machine mode.
        """
        if not self.connected:
            return False
        
        logger.info(f"Starting bootstrap sequence for {self.device_id}")
        
        for cmd, delay in self.BOOTSTRAP_SEQUENCE:
            try:
                self.send_raw(cmd)
                # Wait for response
                import time
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Bootstrap command '{cmd}' failed: {e}")
        
        self.machine_mode_active = True
        logger.info(f"Bootstrap complete for {self.device_id}")
        return True
    
    def send_raw(self, command: str) -> bool:
        """Send raw command string"""
        if not self.serial or not self.serial.is_open:
            return False
        
        try:
            if not command.endswith("\n"):
                command += "\n"
            self.serial.write(command.encode("utf-8"))
            self.serial.flush()
            self._pending_command = command.strip()
            logger.debug(f"Sent: {command.strip()}")
            return True
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            return False
    
    def send_command(self, command: str, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        """Send command and wait for response"""
        if not self.send_raw(command):
            return None
        
        try:
            response = self._response_queue.get(timeout=timeout)
            return response
        except Empty:
            logger.warning(f"Command '{command.strip()}' timed out")
            return None
    
    def _read_loop(self):
        """Background thread to read serial data"""
        while not self._stop_reader.is_set():
            if not self.serial or not self.serial.is_open:
                break
            
            try:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting).decode("utf-8", errors="replace")
                    self.parser.feed(data)
                else:
                    import time
                    time.sleep(0.01)
            except Exception as e:
                if not self._stop_reader.is_set():
                    logger.error(f"Read error: {e}")
                break
    
    def _handle_message(self, msg: Dict[str, Any]):
        """Handle parsed NDJSON message"""
        msg_type = msg.get("type", "unknown")
        
        if self.session:
            self.session.last_seen = datetime.now().isoformat()
        
        # Route by message type
        if msg_type == MessageType.TELEMETRY.value:
            self._handle_telemetry(msg)
        elif msg_type == MessageType.PERIPH.value:
            self._handle_peripheral(msg)
        elif msg_type == MessageType.PERIPH_LIST.value:
            self._handle_peripheral_list(msg)
        elif msg_type == MessageType.STATUS.value:
            self._handle_status(msg)
        elif msg_type == MessageType.ACK.value:
            self._response_queue.put(msg)
        elif msg_type == MessageType.ERR.value:
            logger.warning(f"Board error: {msg}")
            self._response_queue.put(msg)
        elif msg_type == MessageType.RAW.value:
            self._handle_raw(msg)
        
        # Notify general callback
        if self.on_message:
            self.on_message(msg)
    
    def _handle_telemetry(self, msg: Dict[str, Any]):
        """Process telemetry message"""
        event = TelemetryEvent(
            board_id=self.device_id,
            sensor=msg.get("sensor", "unknown"),
            timestamp=msg.get("timestamp", datetime.now().isoformat()),
            data=msg.get("data", msg),
        )
        self.telemetry_store.add(event)
        
        if self.on_telemetry:
            self.on_telemetry(event)
    
    def _handle_peripheral(self, msg: Dict[str, Any]):
        """Process single peripheral descriptor"""
        descriptor = PeripheralDescriptor.from_dict(msg)
        descriptor.board_id = self.device_id
        
        if self.session:
            # Update or add peripheral
            existing = next(
                (p for p in self.session.peripherals if p.peripheral_uid == descriptor.peripheral_uid),
                None
            )
            if existing:
                # Update
                idx = self.session.peripherals.index(existing)
                self.session.peripherals[idx] = descriptor
            else:
                self.session.peripherals.append(descriptor)
        
        if self.on_peripheral:
            self.on_peripheral(descriptor)
    
    def _handle_peripheral_list(self, msg: Dict[str, Any]):
        """Process peripheral list"""
        peripherals = msg.get("peripherals", [])
        for p in peripherals:
            self._handle_peripheral({"type": "periph", **p})
    
    def _handle_status(self, msg: Dict[str, Any]):
        """Process status response"""
        if self.session:
            self.session.firmware_version = msg.get("firmware_version", "")
            self.session.arduino_core = msg.get("arduino_core", "")
            self.session.esp_sdk = msg.get("esp_sdk", "")
            self.session.chip_model = msg.get("chip_model", "")
            self.session.capabilities = msg.get("capabilities", [])
        
        self._response_queue.put(msg)
    
    def _handle_raw(self, msg: Dict[str, Any]):
        """
        Handle raw (non-JSON) lines.
        Parse legacy telemetry format if detected.
        """
        content = msg.get("content", "")
        
        # Try to parse legacy sensor data format
        # Example: "AMB addr=0x77 age=2042ms T=20.50C RH=40.29% P=705.71hPa..."
        if "addr=0x" in content and ("T=" in content or "Gas=" in content):
            parsed = self._parse_legacy_sensor(content)
            if parsed:
                self._handle_telemetry({
                    "type": "telemetry",
                    **parsed,
                })
                return
        
        # Check for I2C scan results
        if "found:" in content.lower():
            match = re.search(r"found:\s*(0x[0-9a-fA-F]+)", content, re.IGNORECASE)
            if match:
                address = match.group(1).lower()
                descriptor = PeripheralRegistry.create_descriptor_from_scan(
                    address=address,
                    board_id=self.device_id,
                )
                self._handle_peripheral(descriptor.to_dict())
    
    def _parse_legacy_sensor(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse legacy sensor data format"""
        # Detect sensor type
        sensor = "unknown"
        if line.startswith("AMB"):
            sensor = "amb"
        elif line.startswith("ENV"):
            sensor = "env"
        
        data = {"sensor": sensor}
        
        # Parse fields
        patterns = {
            "address": r"addr=(0x[0-9a-fA-F]+)",
            "temperature": r"T=([\d.]+)C",
            "humidity": r"RH=([\d.]+)%",
            "pressure": r"P=([\d.]+)hPa",
            "gas_resistance": r"Gas=(\d+)Ohm",
            "iaq": r"IAQ=([\d.]+)",
            "iaq_accuracy": r"acc=(\d+)",
            "co2eq": r"CO2eq=([\d.]+)",
            "voc": r"VOC=([\d.]+)",
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, line)
            if match:
                value = match.group(1)
                try:
                    if "." in value:
                        data[field] = float(value)
                    elif value.startswith("0x"):
                        data[field] = value
                    else:
                        data[field] = int(value)
                except ValueError:
                    data[field] = value
        
        if len(data) > 1:  # Has more than just sensor field
            return {"data": data, "sensor": sensor}
        return None
    
    # Convenience command methods
    def set_led_rgb(self, r: int, g: int, b: int) -> bool:
        """Set LED color"""
        return self.send_raw(CommandBuilder.led_rgb(r, g, b))
    
    def led_off(self) -> bool:
        """Turn off LED"""
        return self.send_raw(CommandBuilder.led_off())
    
    def play_buzzer_preset(self, name: str) -> bool:
        """Play buzzer preset"""
        return self.send_raw(CommandBuilder.buzzer_preset(name))
    
    def play_tone(self, hz: int, ms: int) -> bool:
        """Play tone"""
        return self.send_raw(CommandBuilder.buzzer_tone(hz, ms))
    
    def scan_peripherals(self) -> bool:
        """Trigger I2C scan"""
        return self.send_raw(CommandBuilder.scan())
    
    def start_telemetry(self) -> bool:
        """Start live telemetry stream"""
        if self.session:
            self.session.telemetry_enabled = True
        return self.send_raw(CommandBuilder.live_on())
    
    def stop_telemetry(self) -> bool:
        """Stop live telemetry stream"""
        if self.session:
            self.session.telemetry_enabled = False
        return self.send_raw(CommandBuilder.live_off())
    
    def get_session(self) -> Optional[Dict[str, Any]]:
        """Get current session info"""
        if self.session:
            return self.session.to_dict()
        return None
    
    def get_peripherals(self) -> List[Dict[str, Any]]:
        """Get discovered peripherals"""
        if self.session:
            return [p.to_dict() for p in self.session.peripherals]
        return []
    
    def get_telemetry(self, count: int = 100) -> List[Dict[str, Any]]:
        """Get recent telemetry"""
        return self.telemetry_store.get_by_board(self.device_id, count)


# Global bridge registry
_bridges: Dict[str, MachineModeBridge] = {}


def get_bridge(device_id: str) -> Optional[MachineModeBridge]:
    """Get bridge by device ID"""
    return _bridges.get(device_id)


def create_bridge(port: str, device_id: str = None, **kwargs) -> MachineModeBridge:
    """Create and register a new bridge"""
    bridge = MachineModeBridge(port=port, device_id=device_id, **kwargs)
    if bridge.connect():
        _bridges[bridge.device_id] = bridge
    return bridge


def remove_bridge(device_id: str):
    """Remove and disconnect a bridge"""
    bridge = _bridges.pop(device_id, None)
    if bridge:
        bridge.disconnect()


def list_bridges() -> List[Dict[str, Any]]:
    """List all active bridges"""
    return [
        {
            "device_id": b.device_id,
            "port": b.port,
            "connected": b.connected,
            "machine_mode": b.machine_mode_active,
            "session": b.get_session(),
        }
        for b in _bridges.values()
    ]



























