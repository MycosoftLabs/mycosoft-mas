"""
MycoBrain NDJSON Machine Mode Protocol

Handles communication with MycoBoard in machine mode:
- Line-delimited NDJSON parsing
- Command dispatch
- Telemetry streaming
- Peripheral discovery
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """NDJSON message types from board"""
    ACK = "ack"
    ERR = "err"
    TELEMETRY = "telemetry"
    PERIPH = "periph"
    PERIPH_LIST = "periph_list"
    STATUS = "status"
    EVENT = "event"
    RAW = "raw"  # Non-JSON lines


class PeripheralType(str, Enum):
    """Known peripheral types"""
    MIC = "mic"
    LIDAR = "lidar"
    PIXEL_ARRAY = "pixel_array"
    CAMERA_PROXY = "camera_proxy"
    PHOTODIODE_RX = "photodiode_rx"
    FAST_LED_TX = "fast_led_tx"
    VIBRATOR = "vibrator"
    HAPTIC = "haptic"
    BME688 = "bme688"
    OLED = "oled"
    UNKNOWN = "unknown"


class Capability(str, Enum):
    """Peripheral capabilities"""
    TELEMETRY = "telemetry"
    CONTROL = "control"
    ACOUSTIC_RX = "acoustic_rx"
    ACOUSTIC_TX = "acoustic_tx"
    OPTICAL_RX = "optical_rx"
    OPTICAL_TX = "optical_tx"
    HAPTIC = "haptic"


@dataclass
class PeripheralDescriptor:
    """Describes a peripheral connected to the board"""
    peripheral_uid: str
    peripheral_type: str
    bus: str = "i2c0"
    address: str = ""
    board_id: str = ""
    vendor: str = ""
    product: str = ""
    revision: str = ""
    capabilities: List[str] = field(default_factory=list)
    data_plane: Dict[str, str] = field(default_factory=dict)
    telemetry_schema: Dict[str, Any] = field(default_factory=dict)
    command_schema: Dict[str, Any] = field(default_factory=dict)
    ui_widget: str = ""
    connected: bool = True
    last_seen: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PeripheralDescriptor":
        return cls(
            peripheral_uid=data.get("peripheral_uid", data.get("address", "unknown")),
            peripheral_type=data.get("peripheral_type", "unknown"),
            bus=data.get("bus", "i2c0"),
            address=data.get("address", ""),
            board_id=data.get("board_id", ""),
            vendor=data.get("vendor", ""),
            product=data.get("product", ""),
            revision=data.get("revision", ""),
            capabilities=data.get("capabilities", []),
            data_plane=data.get("data_plane", {}),
            telemetry_schema=data.get("telemetry_schema", {}),
            command_schema=data.get("command_schema", {}),
            ui_widget=data.get("ui_widget", ""),
            connected=data.get("connected", True),
            last_seen=data.get("last_seen", datetime.now().isoformat()),
        )


@dataclass
class BoardSession:
    """Active board connection session"""
    board_id: str
    port: str
    firmware_version: str = ""
    arduino_core: str = ""
    esp_sdk: str = ""
    chip_model: str = ""
    cpu_freq_mhz: int = 240
    connected_at: str = ""
    last_seen: str = ""
    machine_mode: bool = False
    capabilities: List[str] = field(default_factory=list)
    peripherals: List[PeripheralDescriptor] = field(default_factory=list)
    telemetry_enabled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "board_id": self.board_id,
            "port": self.port,
            "firmware_version": self.firmware_version,
            "arduino_core": self.arduino_core,
            "esp_sdk": self.esp_sdk,
            "chip_model": self.chip_model,
            "cpu_freq_mhz": self.cpu_freq_mhz,
            "connected_at": self.connected_at,
            "last_seen": self.last_seen,
            "machine_mode": self.machine_mode,
            "capabilities": self.capabilities,
            "peripherals": [p.to_dict() for p in self.peripherals],
            "telemetry_enabled": self.telemetry_enabled,
        }


@dataclass
class TelemetryEvent:
    """Single telemetry reading"""
    board_id: str
    sensor: str
    timestamp: str
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NDJSONParser:
    """
    Parses NDJSON lines from the board.
    Handles both valid JSON and raw text gracefully.
    """
    
    def __init__(self, on_message: Callable[[Dict[str, Any]], None] = None):
        self.on_message = on_message
        self.buffer = ""
        self.raw_lines: List[str] = []
        
    def feed(self, data: str) -> List[Dict[str, Any]]:
        """
        Feed raw data and parse complete lines.
        Returns list of parsed messages.
        """
        self.buffer += data
        messages = []
        
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            
            if not line:
                continue
                
            msg = self.parse_line(line)
            messages.append(msg)
            
            if self.on_message:
                self.on_message(msg)
                
        return messages
    
    def parse_line(self, line: str) -> Dict[str, Any]:
        """Parse a single line as JSON or raw text"""
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                # Ensure type field exists
                if "type" not in data:
                    data["type"] = "unknown"
                data["_raw"] = line
                return data
            else:
                # Non-dict JSON (array, string, etc.)
                return {
                    "type": MessageType.RAW.value,
                    "content": str(data),
                    "_raw": line,
                }
        except json.JSONDecodeError:
            # Not valid JSON - treat as raw console output
            self.raw_lines.append(line)
            return {
                "type": MessageType.RAW.value,
                "content": line,
                "_raw": line,
            }


class CommandBuilder:
    """
    Builds commands for the board.
    Supports both plaintext and JSON command formats.
    """
    
    @staticmethod
    def mode_machine() -> str:
        return "mode machine\n"
    
    @staticmethod
    def mode_human() -> str:
        return "mode human\n"
    
    @staticmethod
    def debug_off() -> str:
        return "dbg off\n"
    
    @staticmethod
    def debug_on() -> str:
        return "dbg on\n"
    
    @staticmethod
    def periph_scan() -> str:
        return "periph scan\n"
    
    @staticmethod
    def status() -> str:
        return "status\n"
    
    @staticmethod
    def scan() -> str:
        """I2C bus scan"""
        return "scan\n"
    
    @staticmethod
    def live_on() -> str:
        return "live on\n"
    
    @staticmethod
    def live_off() -> str:
        return "live off\n"
    
    @staticmethod
    def led_rgb(r: int, g: int, b: int) -> str:
        """Set LED to RGB color"""
        return f"led rgb {r} {g} {b}\n"
    
    @staticmethod
    def led_mode(mode: str) -> str:
        """Set LED mode: off, state, manual"""
        return f"led mode {mode}\n"
    
    @staticmethod
    def led_off() -> str:
        return "led mode off\n"
    
    @staticmethod
    def buzzer_tone(hz: int, ms: int) -> str:
        """Play a tone at given frequency for duration"""
        return f"tone {hz} {ms}\n"
    
    @staticmethod
    def buzzer_preset(name: str) -> str:
        """Play a preset sound: coin, bump, power, 1up, morgio"""
        return f"{name}\n"
    
    @staticmethod
    def optical_tx_start(profile: str, payload: str, rate_hz: int = 10, repeat: int = 1) -> str:
        """Start optical modem TX"""
        # Encode payload to base64 if needed
        import base64
        payload_b64 = base64.b64encode(payload.encode()).decode()
        return json.dumps({
            "cmd": "optical.tx.start",
            "profile": profile,
            "payload": payload_b64,
            "rate_hz": rate_hz,
            "repeat": repeat,
        }) + "\n"
    
    @staticmethod
    def optical_tx_stop() -> str:
        return json.dumps({"cmd": "optical.tx.stop"}) + "\n"
    
    @staticmethod
    def acoustic_tx_start(
        profile: str, 
        payload: str, 
        symbol_ms: int = 100,
        f0: int = 1000,
        f1: int = 2000,
        repeat: int = 1
    ) -> str:
        """Start acoustic modem TX"""
        import base64
        payload_b64 = base64.b64encode(payload.encode()).decode()
        return json.dumps({
            "cmd": "acoustic.tx.start",
            "profile": profile,
            "payload": payload_b64,
            "symbol_ms": symbol_ms,
            "f0": f0,
            "f1": f1,
            "repeat": repeat,
        }) + "\n"
    
    @staticmethod
    def acoustic_tx_stop() -> str:
        return json.dumps({"cmd": "acoustic.tx.stop"}) + "\n"
    
    @staticmethod
    def lora_send(message: str) -> str:
        """Send LoRa message"""
        return f"lora send {message}\n"
    
    @staticmethod
    def lora_status() -> str:
        return "lora status\n"
    
    @staticmethod
    def custom(cmd: str) -> str:
        """Send custom command"""
        if not cmd.endswith("\n"):
            cmd += "\n"
        return cmd


class PeripheralRegistry:
    """
    Registry mapping peripheral types to widgets and command sets.
    """
    
    # Default widget mappings
    WIDGET_MAP: Dict[str, Dict[str, Any]] = {
        PeripheralType.BME688.value: {
            "widget": "environmental_sensor",
            "icon": "thermometer",
            "controls": [],
            "telemetry_fields": ["temperature", "humidity", "pressure", "iaq", "co2eq", "voc"],
            "charts": ["temperature_timeline", "humidity_timeline", "iaq_gauge"],
        },
        PeripheralType.PIXEL_ARRAY.value: {
            "widget": "led_array",
            "icon": "lightbulb",
            "controls": ["color_picker", "pattern_selector", "brightness_slider"],
            "commands": ["led.rgb", "led.pattern", "led.brightness"],
            "modems": ["optical_tx"],
        },
        PeripheralType.MIC.value: {
            "widget": "microphone",
            "icon": "mic",
            "controls": ["gain_slider", "frequency_band_selector"],
            "telemetry_fields": ["amplitude", "frequency", "fft_bins"],
            "charts": ["waveform", "fft_spectrum"],
            "modems": ["acoustic_rx"],
        },
        PeripheralType.LIDAR.value: {
            "widget": "lidar",
            "icon": "radar",
            "controls": ["sample_rate"],
            "telemetry_fields": ["distance_mm", "signal_strength"],
            "charts": ["distance_timeline"],
        },
        PeripheralType.CAMERA_PROXY.value: {
            "widget": "camera",
            "icon": "camera",
            "controls": ["resolution", "exposure"],
            "telemetry_fields": ["frame_rate", "brightness"],
            "modems": ["optical_rx"],
        },
        PeripheralType.PHOTODIODE_RX.value: {
            "widget": "photodiode",
            "icon": "sun",
            "controls": ["sensitivity"],
            "telemetry_fields": ["light_level", "decoded_bits"],
            "modems": ["optical_rx"],
        },
        PeripheralType.FAST_LED_TX.value: {
            "widget": "led_tx",
            "icon": "zap",
            "controls": ["pattern", "payload_input"],
            "modems": ["optical_tx"],
        },
        PeripheralType.VIBRATOR.value: {
            "widget": "haptic",
            "icon": "vibrate",
            "controls": ["intensity_slider", "pattern_presets"],
            "commands": ["haptic.intensity", "haptic.pattern"],
        },
        PeripheralType.HAPTIC.value: {
            "widget": "haptic",
            "icon": "vibrate",
            "controls": ["intensity_slider", "pattern_presets"],
            "commands": ["haptic.intensity", "haptic.pattern"],
        },
        PeripheralType.OLED.value: {
            "widget": "display",
            "icon": "monitor",
            "controls": ["text_input", "image_upload"],
            "commands": ["display.text", "display.clear"],
        },
        PeripheralType.UNKNOWN.value: {
            "widget": "generic",
            "icon": "help-circle",
            "controls": [],
            "telemetry_fields": [],
        },
    }
    
    # I2C address to peripheral type hints
    I2C_HINTS: Dict[str, str] = {
        "0x76": PeripheralType.BME688.value,
        "0x77": PeripheralType.BME688.value,
        "0x3c": PeripheralType.OLED.value,
        "0x3d": PeripheralType.OLED.value,
        "0x68": "mpu6050",  # Accelerometer
        "0x69": "mpu6050",
        "0x29": PeripheralType.LIDAR.value,  # VL53L0X
        "0x52": PeripheralType.LIDAR.value,  # VL53L1X
        "0x48": "ads1115",  # ADC
        "0x57": "max30102",  # Heart rate sensor
    }
    
    @classmethod
    def get_widget_config(cls, peripheral_type: str) -> Dict[str, Any]:
        """Get widget configuration for a peripheral type"""
        return cls.WIDGET_MAP.get(
            peripheral_type, 
            cls.WIDGET_MAP[PeripheralType.UNKNOWN.value]
        )
    
    @classmethod
    def guess_peripheral_type(cls, address: str) -> str:
        """Guess peripheral type from I2C address"""
        return cls.I2C_HINTS.get(address.lower(), PeripheralType.UNKNOWN.value)
    
    @classmethod
    def create_descriptor_from_scan(
        cls, 
        address: str, 
        board_id: str,
        bus: str = "i2c0"
    ) -> PeripheralDescriptor:
        """Create a peripheral descriptor from I2C scan result"""
        periph_type = cls.guess_peripheral_type(address)
        widget_config = cls.get_widget_config(periph_type)
        
        # Generate stable UID
        uid = hashlib.md5(f"{board_id}:{bus}:{address}".encode()).hexdigest()[:12]
        
        return PeripheralDescriptor(
            peripheral_uid=uid,
            peripheral_type=periph_type,
            bus=bus,
            address=address,
            board_id=board_id,
            capabilities=["telemetry"] if widget_config.get("telemetry_fields") else [],
            ui_widget=widget_config.get("widget", "generic"),
            last_seen=datetime.now().isoformat(),
        )


class TelemetryStore:
    """
    In-memory ring buffer for telemetry with optional persistence.
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer: List[TelemetryEvent] = []
        self.subscribers: List[Callable[[TelemetryEvent], None]] = []
    
    def add(self, event: TelemetryEvent):
        """Add telemetry event to buffer"""
        self.buffer.append(event)
        if len(self.buffer) > self.max_size:
            self.buffer.pop(0)
        
        # Notify subscribers
        for sub in self.subscribers:
            try:
                sub(event)
            except Exception as e:
                logger.error(f"Telemetry subscriber error: {e}")
    
    def subscribe(self, callback: Callable[[TelemetryEvent], None]):
        """Subscribe to telemetry events"""
        self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[TelemetryEvent], None]):
        """Unsubscribe from telemetry events"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def get_recent(self, count: int = 100, sensor: str = None) -> List[Dict[str, Any]]:
        """Get recent telemetry events"""
        if sensor:
            filtered = [e for e in self.buffer if e.sensor == sensor]
        else:
            filtered = self.buffer
        return [e.to_dict() for e in filtered[-count:]]
    
    def get_by_board(self, board_id: str, count: int = 100) -> List[Dict[str, Any]]:
        """Get telemetry for a specific board"""
        filtered = [e for e in self.buffer if e.board_id == board_id]
        return [e.to_dict() for e in filtered[-count:]]



























