"""
MMP (Mycosoft Messaging Protocol) Envelope

Normalized semantic envelope for all MycoBrain device data.
Sits above MDP (transport framing) and below Mycorrhizae (cloud/topic routing).

Protocol Stack:
  Layer 3: Mycorrhizae  — Cloud/topic/schema contract (MQTT topics, Redis pub/sub)
  Layer 2: MMP          — Normalized semantic envelope (this module)
  Layer 1: MDP          — Framed transport (COBS, CRC16, ACK/retry)
  Layer 0: Physical     — UART, USB-CDC, LoRa, Wi-Fi, BLE

Created: March 9, 2026
"""

import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

MMP_SCHEMA_VERSION = "org.mycosoft.mmp/1"


class MMPKind(str, Enum):
    """MMP envelope kinds — what the message represents."""
    CAPABILITY = "capability"
    SAMPLE_RAW = "sample_raw"
    SAMPLE_NORM = "sample_norm"
    EVENT = "event"
    PATTERN = "pattern"
    HEALTH = "health"
    COMMAND = "command"
    COMMAND_RESULT = "command_result"


class MMPProducer(str, Enum):
    """Who produced this envelope."""
    SIDE_A = "side_a"
    JETSON = "jetson"
    SIDE_B = "side_b"
    GATEWAY = "gateway"
    MAS = "mas"


class MeasurementClass(str, Enum):
    """Standardized measurement classes for capability-driven widget mapping."""
    ENV_AIR = "env.air"
    ENV_SOIL = "env.soil"
    ENV_WATER = "env.water"
    ENV_LIGHT = "env.light"
    BIO_ELECTRIC = "bio.electric"
    BIO_CHEMICAL = "bio.chemical"
    BIO_GROWTH = "bio.growth"
    MOTION_IMU = "motion.imu"
    MOTION_LIDAR = "motion.lidar"
    VISION_RGB = "vision.rgb"
    VISION_DEPTH = "vision.depth"
    VISION_THERMAL = "vision.thermal"
    AUDIO_MIC = "audio.mic"
    AUDIO_ULTRASONIC = "audio.ultrasonic"
    ACTUATOR_MOSFET = "actuator.mosfet"
    ACTUATOR_SERVO = "actuator.servo"
    ACTUATOR_LED = "actuator.led"
    ACTUATOR_HAPTIC = "actuator.haptic"
    ACTUATOR_BUZZER = "actuator.buzzer"
    COMMS_LORA = "comms.lora"
    COMMS_WIFI = "comms.wifi"
    COMMS_BLE = "comms.ble"
    COMMS_LTE = "comms.lte"
    COMPUTE_NLM = "compute.nlm"
    COMPUTE_LLM = "compute.llm"
    COMPUTE_VISION = "compute.vision"
    COMPUTE_IK = "compute.ik"
    SYSTEM_POWER = "system.power"
    SYSTEM_HEALTH = "system.health"
    UNKNOWN = "unknown"


@dataclass
class MMPEnvelope:
    """
    Mycosoft Messaging Protocol envelope.

    Every piece of data flowing through the MycoBrain stack gets wrapped in this
    envelope before crossing layer boundaries. MDP moves the bytes, MMP names
    the meaning, Mycorrhizae carries it across the network.
    """
    schema: str = MMP_SCHEMA_VERSION
    kind: str = MMPKind.SAMPLE_RAW.value
    device_id: str = ""
    producer: str = MMPProducer.SIDE_A.value
    ts: str = ""
    capability_id: str = ""
    measurement_class: str = MeasurementClass.UNKNOWN.value
    fields: Dict[str, Any] = field(default_factory=dict)
    features: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.ts:
            self.ts = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MMPEnvelope":
        return cls(
            schema=data.get("schema", MMP_SCHEMA_VERSION),
            kind=data.get("kind", MMPKind.SAMPLE_RAW.value),
            device_id=data.get("device_id", ""),
            producer=data.get("producer", MMPProducer.SIDE_A.value),
            ts=data.get("ts", ""),
            capability_id=data.get("capability_id", ""),
            measurement_class=data.get("measurement_class", MeasurementClass.UNKNOWN.value),
            fields=data.get("fields", {}),
            features=data.get("features", {}),
            provenance=data.get("provenance", {}),
        )

    @classmethod
    def from_json(cls, raw: str) -> "MMPEnvelope":
        return cls.from_dict(json.loads(raw))

    def to_mycorrhizae_topic(self) -> str:
        """Generate MQTT topic for Mycorrhizae routing."""
        return f"mycosoft/devices/{self.device_id}/{self.kind}/{self.capability_id}"

    def to_mycorrhizae_payload(self) -> Dict[str, Any]:
        """Full payload for MQTT/Redis publish via Mycorrhizae."""
        return self.to_dict()


@dataclass
class CapabilityManifestEntry:
    """
    Single capability declared by a Side A driver on boot or bus rescan.
    The website uses this to resolve widgets by measurement_class.
    """
    capability_id: str
    sensor_type: str
    bus: str = "i2c0"
    address: str = ""
    measurement_class: str = MeasurementClass.UNKNOWN.value
    channels: List[str] = field(default_factory=list)
    units: Dict[str, str] = field(default_factory=dict)
    controls: List[str] = field(default_factory=list)
    preferred_widget: str = "generic_timeseries"
    sample_hz: float = 1.0
    calibration_state: str = "uncalibrated"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityManifestEntry":
        return cls(
            capability_id=data.get("capability_id", ""),
            sensor_type=data.get("sensor_type", "unknown"),
            bus=data.get("bus", "i2c0"),
            address=data.get("address", ""),
            measurement_class=data.get("measurement_class", MeasurementClass.UNKNOWN.value),
            channels=data.get("channels", []),
            units=data.get("units", {}),
            controls=data.get("controls", []),
            preferred_widget=data.get("preferred_widget", "generic_timeseries"),
            sample_hz=data.get("sample_hz", 1.0),
            calibration_state=data.get("calibration_state", "uncalibrated"),
        )


@dataclass
class CapabilityManifest:
    """Full capability manifest emitted by Side A on boot and bus_rescan."""
    device_id: str
    firmware_version: str = ""
    capabilities: List[CapabilityManifestEntry] = field(default_factory=list)
    ts: str = ""

    def __post_init__(self):
        if not self.ts:
            self.ts = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "firmware_version": self.firmware_version,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "ts": self.ts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityManifest":
        return cls(
            device_id=data.get("device_id", ""),
            firmware_version=data.get("firmware_version", ""),
            capabilities=[
                CapabilityManifestEntry.from_dict(c)
                for c in data.get("capabilities", [])
            ],
            ts=data.get("ts", ""),
        )


# ---------------------------------------------------------------------------
# Converters: MDP telemetry → MMP envelope
# ---------------------------------------------------------------------------

def mdp_telemetry_to_mmp(
    device_id: str,
    telemetry: Dict[str, Any],
    producer: str = MMPProducer.SIDE_A.value,
) -> List[MMPEnvelope]:
    """
    Convert a raw MDP telemetry dict (as emitted by Side A NDJSON) into
    one or more MMP envelopes — one per logical capability.
    """
    envelopes: List[MMPEnvelope] = []
    ts = datetime.now(timezone.utc).isoformat()

    # BME688 environmental data
    env_fields = {}
    for key in ("temperature", "humidity", "pressure", "gas_resistance"):
        if key in telemetry and telemetry[key] is not None:
            env_fields[key] = telemetry[key]
    if env_fields:
        envelopes.append(MMPEnvelope(
            kind=MMPKind.SAMPLE_RAW.value,
            device_id=device_id,
            producer=producer,
            ts=ts,
            capability_id="bme688_0",
            measurement_class=MeasurementClass.ENV_AIR.value,
            fields=env_fields,
        ))

    # Analog inputs
    analog_fields = {}
    for key in ("ai1_voltage", "ai2_voltage", "ai3_voltage", "ai4_voltage"):
        if key in telemetry and telemetry[key] is not None:
            analog_fields[key] = telemetry[key]
    if analog_fields:
        envelopes.append(MMPEnvelope(
            kind=MMPKind.SAMPLE_RAW.value,
            device_id=device_id,
            producer=producer,
            ts=ts,
            capability_id="analog_inputs",
            measurement_class=MeasurementClass.BIO_ELECTRIC.value,
            fields=analog_fields,
        ))

    # MOSFET states
    if "mosfet_states" in telemetry:
        envelopes.append(MMPEnvelope(
            kind=MMPKind.SAMPLE_RAW.value,
            device_id=device_id,
            producer=producer,
            ts=ts,
            capability_id="mosfet_ctrl",
            measurement_class=MeasurementClass.ACTUATOR_MOSFET.value,
            fields={"states": telemetry["mosfet_states"]},
        ))

    # System health
    health_fields = {}
    for key in ("firmware_version", "uptime_seconds"):
        if key in telemetry:
            health_fields[key] = telemetry[key]
    if health_fields:
        envelopes.append(MMPEnvelope(
            kind=MMPKind.HEALTH.value,
            device_id=device_id,
            producer=producer,
            ts=ts,
            capability_id="system",
            measurement_class=MeasurementClass.SYSTEM_HEALTH.value,
            fields=health_fields,
        ))

    return envelopes


def fci_signal_to_mmp(
    device_id: str,
    channel: int,
    signal_data: Dict[str, Any],
    pattern_name: Optional[str] = None,
) -> MMPEnvelope:
    """
    Convert FCI (Fungal-Computer Interface) signal data to MMP envelope.
    Bridges biological telemetry into the same device identity used by MAS.
    """
    fields = {
        "channel": channel,
        **signal_data,
    }
    if pattern_name:
        fields["pattern"] = pattern_name

    kind = MMPKind.PATTERN.value if pattern_name else MMPKind.SAMPLE_RAW.value

    return MMPEnvelope(
        kind=kind,
        device_id=device_id,
        producer=MMPProducer.SIDE_A.value,
        capability_id=f"fci_ch{channel}",
        measurement_class=MeasurementClass.BIO_ELECTRIC.value,
        fields=fields,
        provenance={"source": "fci_driver", "bridge": "mycorrhizae"},
    )


def nature_packet_to_mmp(
    device_id: str,
    nature_packet: Dict[str, Any],
) -> MMPEnvelope:
    """
    Convert a NaturePacket (Jetson-assembled fusion of MycoBrain + camera + audio)
    into an MMP envelope with NLM features.
    """
    return MMPEnvelope(
        kind=MMPKind.SAMPLE_NORM.value,
        device_id=device_id,
        producer=MMPProducer.JETSON.value,
        capability_id="nature_packet",
        measurement_class=MeasurementClass.COMPUTE_NLM.value,
        fields=nature_packet.get("raw", {}),
        features=nature_packet.get("features", {}),
        provenance={
            "nlm_version": nature_packet.get("nlm_version", "unknown"),
            "fusion_sources": nature_packet.get("sources", []),
        },
    )


# ---------------------------------------------------------------------------
# Allowed intents for actuation (Side A enforces local bounds)
# ---------------------------------------------------------------------------

ALLOWED_ACTUATION_INTENTS = [
    "set_sampling_rate",
    "signal_emit",
    "pixel_pattern",
    "servo_target",
    "sensor_rescan",
    "stimulus_pulse",
    "set_mosfet",
    "buzzer_tone",
    "buzzer_pattern",
    "led_rgb",
    "led_off",
    "calibrate",
    "reset",
]


def validate_actuation_intent(intent: str) -> bool:
    """Check if an actuation intent is in the allow-list."""
    return intent in ALLOWED_ACTUATION_INTENTS


def create_command_envelope(
    device_id: str,
    intent: str,
    params: Dict[str, Any],
    producer: str = MMPProducer.MAS.value,
) -> Optional[MMPEnvelope]:
    """
    Create a command envelope for an actuation intent.
    Returns None if intent is not in the allow-list.
    """
    if not validate_actuation_intent(intent):
        logger.warning("Blocked actuation intent '%s' for device %s", intent, device_id)
        return None

    return MMPEnvelope(
        kind=MMPKind.COMMAND.value,
        device_id=device_id,
        producer=producer,
        capability_id=intent,
        measurement_class=MeasurementClass.UNKNOWN.value,
        fields=params,
    )
