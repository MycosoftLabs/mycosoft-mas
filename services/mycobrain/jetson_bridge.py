#!/usr/bin/env python3
"""
MycoBrain Jetson Bridge — Embedded on Jetson

Reads Side A over USB-C serial (NDJSON/MDP), assembles NaturePackets,
runs NLM embeddings, wraps results in MMP envelopes, and heartbeats
to MAS with Jetson-specific capabilities.

This service runs ON the Jetson device itself (Mushroom 1 AGX Orin or
Hyphae 1 Orin Nano). It reads Side A directly and pushes upstream.

Data flow:
  Side A (USB-CDC serial) → Jetson Bridge → MAS heartbeat + MQTT publish

Created: March 9, 2026
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

logger = logging.getLogger("JetsonBridge")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SIDE_A_SERIAL_PORT = os.getenv("SIDE_A_SERIAL_PORT", "/dev/ttyACM0")
SIDE_A_BAUD_RATE = int(os.getenv("SIDE_A_BAUD_RATE", "115200"))
MAS_URL = os.getenv("MAS_URL", "http://192.168.0.188:8001")
NLM_URL = os.getenv("NLM_URL", f"{MAS_URL}/api/nlm/embeddings/nature")
HEARTBEAT_INTERVAL_S = int(os.getenv("HEARTBEAT_INTERVAL_S", "30"))
DEVICE_ROLE = os.getenv("DEVICE_ROLE", "mushroom1")  # mushroom1 or hyphae1
JETSON_MODEL = os.getenv("JETSON_MODEL", "orin_nano")  # agx_orin or orin_nano
DEVICE_ID = os.getenv("DEVICE_ID", "")  # Auto-detected from Side A if empty
MQTT_BROKER = os.getenv("MQTT_BROKER", "192.168.0.189")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))


class JetsonBridge:
    """
    Middle-layer bridge that sits between Side A (sensors) and MAS (cloud).

    On Mushroom 1 (AGX Orin / J501):
      - Full NLM embeddings + anomaly scoring
      - Camera/depth inference (GMSL2 or USB)
      - Local LLM for edge queries
      - Pinocchio IK for arm control (if SO-ARM101 attached)
      - CAN/RS-485 motor bus management

    On Hyphae 1 (Orin Nano):
      - NLM embeddings only
      - Single USB camera (optional)
      - Lightweight inference
      - Battery-conscious polling
    """

    def __init__(self):
        self.device_id: str = DEVICE_ID
        self.device_role: str = DEVICE_ROLE
        self.jetson_model: str = JETSON_MODEL
        self.running: bool = False
        self.serial_conn = None
        self.last_telemetry: Dict[str, Any] = {}
        self.peripherals: List[Dict[str, Any]] = []
        self.capability_manifest: List[Dict[str, Any]] = []
        self._nlm_client: Optional[httpx.AsyncClient] = None
        self._mas_client: Optional[httpx.AsyncClient] = None
        self._side_a_buffer: str = ""
        self._telemetry_count: int = 0
        self._last_heartbeat: float = 0

    # ------------------------------------------------------------------
    # Jetson capability detection
    # ------------------------------------------------------------------

    def detect_jetson_capabilities(self) -> List[str]:
        """Detect available Jetson capabilities based on model and hardware."""
        caps = ["nlm_edge", "mmp_bridge"]

        if self.jetson_model == "agx_orin":
            caps.extend([
                "camera_gmsl",
                "depth_stereo",
                "local_llm",
                "pinocchio_ik",
                "can_bus",
                "rs485_bus",
                "high_power_inference",
            ])
        elif self.jetson_model == "orin_nano":
            caps.extend([
                "camera_usb",
                "lightweight_inference",
                "battery_mode",
            ])

        # Check for specific hardware
        if os.path.exists("/dev/video0"):
            if "camera_usb" not in caps and "camera_gmsl" not in caps:
                caps.append("camera_usb")

        return caps

    def build_jetson_peripherals(self) -> List[Dict[str, Any]]:
        """Build peripheral manifest entries for Jetson-side capabilities."""
        peripherals = []

        if self.jetson_model == "agx_orin":
            peripherals.extend([
                {
                    "capability_id": "nlm_edge",
                    "sensor_type": "nlm_encoder",
                    "bus": "internal",
                    "measurement_class": "compute.nlm",
                    "channels": ["embedding", "anomaly_score"],
                    "preferred_widget": "nlm_dashboard",
                    "sample_hz": 10.0,
                },
                {
                    "capability_id": "local_llm",
                    "sensor_type": "llm_runtime",
                    "bus": "internal",
                    "measurement_class": "compute.llm",
                    "channels": ["response"],
                    "preferred_widget": "llm_console",
                    "sample_hz": 0.0,
                },
            ])
            if os.path.exists("/dev/video0"):
                peripherals.append({
                    "capability_id": "camera_rgb",
                    "sensor_type": "camera",
                    "bus": "gmsl2" if self.jetson_model == "agx_orin" else "usb",
                    "measurement_class": "vision.rgb",
                    "channels": ["frame"],
                    "preferred_widget": "camera_feed",
                    "sample_hz": 30.0,
                })
        else:
            # Orin Nano — lighter set
            peripherals.append({
                "capability_id": "nlm_edge",
                "sensor_type": "nlm_encoder",
                "bus": "internal",
                "measurement_class": "compute.nlm",
                "channels": ["embedding", "anomaly_score"],
                "preferred_widget": "nlm_dashboard",
                "sample_hz": 5.0,
            })
            if os.path.exists("/dev/video0"):
                peripherals.append({
                    "capability_id": "camera_rgb",
                    "sensor_type": "camera",
                    "bus": "usb",
                    "measurement_class": "vision.rgb",
                    "channels": ["frame"],
                    "preferred_widget": "camera_feed",
                    "sample_hz": 15.0,
                })

        return peripherals

    # ------------------------------------------------------------------
    # Serial communication with Side A
    # ------------------------------------------------------------------

    async def connect_side_a(self) -> bool:
        """Open USB-CDC serial to Side A."""
        try:
            import serial as pyserial
            self.serial_conn = pyserial.Serial(
                port=SIDE_A_SERIAL_PORT,
                baudrate=SIDE_A_BAUD_RATE,
                timeout=0.1,
            )
            logger.info("Connected to Side A on %s @ %d", SIDE_A_SERIAL_PORT, SIDE_A_BAUD_RATE)

            # Initialize machine mode
            await asyncio.sleep(0.5)
            self.serial_conn.write(b"mode machine\n")
            await asyncio.sleep(0.3)
            self.serial_conn.write(b"dbg off\n")
            await asyncio.sleep(0.3)
            self.serial_conn.write(b"fmt json\n")
            await asyncio.sleep(0.3)

            # Request initial scan to get peripherals
            self.serial_conn.write(b"scan\n")
            await asyncio.sleep(1.0)

            # Read any buffered responses
            self._drain_serial()

            return True
        except ImportError:
            logger.error("pyserial not installed — run: pip install pyserial")
            return False
        except Exception as e:
            logger.error("Failed to connect to Side A: %s", e)
            return False

    def _drain_serial(self):
        """Read and process all buffered serial data."""
        if not self.serial_conn or not self.serial_conn.is_open:
            return
        while self.serial_conn.in_waiting > 0:
            try:
                raw = self.serial_conn.readline().decode("utf-8", errors="replace").strip()
                if raw:
                    self._process_side_a_line(raw)
            except Exception as e:
                logger.debug("Serial drain error: %s", e)

    def _process_side_a_line(self, line: str):
        """Parse one NDJSON line from Side A."""
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            logger.debug("Non-JSON from Side A: %s", line[:80])
            return

        msg_type = data.get("type", "")

        if msg_type == "telemetry":
            self.last_telemetry = data
            self._telemetry_count += 1
            if not self.device_id and "board_id" in data:
                mac = data["board_id"].replace(":", "")
                self.device_id = f"MYCOBRAIN-{mac[-6:].upper()}"
                logger.info("Auto-detected device_id: %s", self.device_id)

        elif msg_type == "periph_list":
            self.peripherals = data.get("peripherals", [])
            if not self.device_id and "board_id" in data:
                mac = data["board_id"].replace(":", "")
                self.device_id = f"MYCOBRAIN-{mac[-6:].upper()}"
            self._build_capability_manifest()

        elif msg_type == "ack":
            logger.debug("Side A ACK: %s", data.get("cmd", ""))

        elif msg_type == "err":
            logger.warning("Side A error: %s", data.get("error", ""))

    def _build_capability_manifest(self):
        """Build MMP capability manifest from Side A peripherals + Jetson capabilities."""
        from mycosoft_mas.protocols.mmp import MeasurementClass

        # I2C address to measurement class mapping
        addr_to_class = {
            0x76: ("bme688_0", "bme688", MeasurementClass.ENV_AIR.value, "environmental_sensor"),
            0x77: ("bme688_1", "bme688", MeasurementClass.ENV_AIR.value, "environmental_sensor"),
            0x3c: ("oled_0", "oled", MeasurementClass.ACTUATOR_LED.value, "display"),
            0x3d: ("oled_1", "oled", MeasurementClass.ACTUATOR_LED.value, "display"),
            0x29: ("lidar_0", "vl53l0x", MeasurementClass.MOTION_LIDAR.value, "lidar"),
            0x52: ("lidar_1", "vl53l1x", MeasurementClass.MOTION_LIDAR.value, "lidar"),
            0x48: ("adc_0", "ads1115", MeasurementClass.BIO_ELECTRIC.value, "adc_timeseries"),
            0x57: ("heartrate_0", "max30102", MeasurementClass.BIO_CHEMICAL.value, "heartrate"),
        }

        manifest = []
        for p in self.peripherals:
            addr = p.get("address", 0)
            if addr in addr_to_class:
                cap_id, sensor_type, mclass, widget = addr_to_class[addr]
                manifest.append({
                    "capability_id": cap_id,
                    "sensor_type": sensor_type,
                    "bus": "i2c0",
                    "address": f"0x{addr:02x}",
                    "measurement_class": mclass,
                    "preferred_widget": widget,
                    "sample_hz": 0.1,
                })
            else:
                manifest.append({
                    "capability_id": f"i2c_{addr:02x}",
                    "sensor_type": "unknown",
                    "bus": "i2c0",
                    "address": f"0x{addr:02x}",
                    "measurement_class": MeasurementClass.UNKNOWN.value,
                    "preferred_widget": "generic_timeseries",
                    "sample_hz": 0.1,
                })

        # Add built-in Side A capabilities
        manifest.extend([
            {
                "capability_id": "analog_inputs",
                "sensor_type": "adc_internal",
                "bus": "gpio",
                "measurement_class": MeasurementClass.BIO_ELECTRIC.value,
                "channels": ["ai1", "ai2", "ai3", "ai4"],
                "units": {"voltage": "V"},
                "preferred_widget": "analog_timeseries",
                "sample_hz": 0.1,
            },
            {
                "capability_id": "mosfet_ctrl",
                "sensor_type": "mosfet",
                "bus": "gpio",
                "measurement_class": MeasurementClass.ACTUATOR_MOSFET.value,
                "channels": ["ch0", "ch1", "ch2"],
                "controls": ["set_mosfet"],
                "preferred_widget": "switch_panel",
            },
            {
                "capability_id": "neopixel",
                "sensor_type": "sk6805",
                "bus": "gpio",
                "measurement_class": MeasurementClass.ACTUATOR_LED.value,
                "controls": ["led_rgb", "led_off", "pixel_pattern"],
                "preferred_widget": "color_picker",
            },
            {
                "capability_id": "buzzer",
                "sensor_type": "piezo",
                "bus": "gpio",
                "measurement_class": MeasurementClass.ACTUATOR_BUZZER.value,
                "controls": ["buzzer_tone", "buzzer_pattern"],
                "preferred_widget": "tone_control",
            },
        ])

        # Add Jetson capabilities
        manifest.extend(self.build_jetson_peripherals())

        self.capability_manifest = manifest
        logger.info("Built capability manifest: %d entries", len(manifest))

    # ------------------------------------------------------------------
    # NLM embedding
    # ------------------------------------------------------------------

    async def compute_nlm_embedding(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Send telemetry to NLM for embedding + anomaly scoring."""
        try:
            if self._nlm_client is None:
                self._nlm_client = httpx.AsyncClient(timeout=10.0)

            nature_input = {
                "bme688": {
                    k: telemetry.get(k)
                    for k in ("temperature", "humidity", "pressure", "gas_resistance")
                    if telemetry.get(k) is not None
                },
            }
            if telemetry.get("ai1_voltage") is not None:
                nature_input["analog"] = {
                    "ai1": telemetry.get("ai1_voltage"),
                    "ai2": telemetry.get("ai2_voltage"),
                    "ai3": telemetry.get("ai3_voltage"),
                    "ai4": telemetry.get("ai4_voltage"),
                }

            response = await self._nlm_client.post(NLM_URL, json=nature_input)
            if response.status_code == 200:
                return response.json()
            else:
                logger.debug("NLM returned %d", response.status_code)
                return {}
        except Exception as e:
            logger.debug("NLM embedding failed: %s", e)
            return {}

    # ------------------------------------------------------------------
    # MMP envelope creation
    # ------------------------------------------------------------------

    def wrap_telemetry_as_mmp(
        self,
        telemetry: Dict[str, Any],
        nlm_result: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Wrap Side A telemetry into MMP envelopes."""
        from mycosoft_mas.protocols.mmp import mdp_telemetry_to_mmp, nature_packet_to_mmp

        envelopes = [e.to_dict() for e in mdp_telemetry_to_mmp(
            device_id=self.device_id,
            telemetry=telemetry,
            producer="side_a",
        )]

        if nlm_result:
            nature_env = nature_packet_to_mmp(
                device_id=self.device_id,
                nature_packet={
                    "raw": telemetry,
                    "features": nlm_result,
                    "nlm_version": nlm_result.get("version", "unknown"),
                    "sources": ["bme688", "analog"],
                },
            )
            envelopes.append(nature_env.to_dict())

        return envelopes

    # ------------------------------------------------------------------
    # MAS heartbeat
    # ------------------------------------------------------------------

    async def send_heartbeat(self):
        """Send heartbeat to MAS device registry."""
        if not self.device_id:
            logger.debug("No device_id yet, skipping heartbeat")
            return

        try:
            if self._mas_client is None:
                self._mas_client = httpx.AsyncClient(timeout=10.0)

            jetson_caps = self.detect_jetson_capabilities()
            all_caps = ["temperature", "humidity", "pressure", "gas_resistance", "voc"]
            all_caps.extend(jetson_caps)
            if self.device_role == "mushroom1":
                all_caps.extend(["bioelectric", "lora", "wifi"])
            else:
                all_caps.extend(["lora", "wifi"])

            heartbeat = {
                "device_id": self.device_id,
                "device_name": f"MycoBrain {self.device_role.title()}",
                "device_role": self.device_role,
                "device_display_name": "Mushroom 1" if self.device_role == "mushroom1" else "Hyphae 1",
                "host": self._get_local_ip(),
                "port": 8003,
                "firmware_version": self.last_telemetry.get("firmware_version", "unknown"),
                "board_type": f"esp32s3+{self.jetson_model}",
                "sensors": list({
                    p.get("sensor_type", "unknown")
                    for p in self.capability_manifest
                    if p.get("sensor_type") != "unknown"
                }),
                "capabilities": all_caps,
                "peripherals": self.capability_manifest,
                "connection_type": "lan",
                "ingestion_source": "serial",
                "extra": {
                    "jetson_present": True,
                    "jetson_model": self.jetson_model,
                    "jetson_capabilities": jetson_caps,
                    "telemetry_count": self._telemetry_count,
                },
            }

            response = await self._mas_client.post(
                f"{MAS_URL}/api/devices/heartbeat",
                json=heartbeat,
            )
            if response.status_code == 200:
                logger.debug("Heartbeat sent: %s", response.json().get("status"))
            else:
                logger.warning("Heartbeat failed: %d %s", response.status_code, response.text[:200])
        except Exception as e:
            logger.warning("Heartbeat error: %s", e)

    def _get_local_ip(self) -> str:
        """Get local IP address for heartbeat."""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("192.168.0.188", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self):
        """Main bridge loop."""
        logger.info("Starting Jetson Bridge (model=%s, role=%s)", self.jetson_model, self.device_role)

        connected = await self.connect_side_a()
        if not connected:
            logger.error("Cannot connect to Side A — running in headless mode (heartbeat only)")

        self.running = True

        while self.running:
            now = time.time()

            # Read serial data from Side A
            if self.serial_conn and self.serial_conn.is_open:
                self._drain_serial()

            # Process latest telemetry through NLM
            if self.last_telemetry and self._telemetry_count > 0:
                nlm_result = await self.compute_nlm_embedding(self.last_telemetry)
                envelopes = self.wrap_telemetry_as_mmp(self.last_telemetry, nlm_result)
                # Envelopes are ready for MQTT publish or Side B forwarding
                if envelopes:
                    logger.debug("Produced %d MMP envelopes", len(envelopes))

            # Heartbeat to MAS
            if now - self._last_heartbeat >= HEARTBEAT_INTERVAL_S:
                await self.send_heartbeat()
                self._last_heartbeat = now

            await asyncio.sleep(1.0)

    async def stop(self):
        """Graceful shutdown."""
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        if self._nlm_client:
            await self._nlm_client.aclose()
        if self._mas_client:
            await self._mas_client.aclose()
        logger.info("Jetson Bridge stopped")

    # ------------------------------------------------------------------
    # Command passthrough (MYCA → Side A)
    # ------------------------------------------------------------------

    async def send_command_to_side_a(self, intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an actuation command to Side A.
        Validates against allowed intents before sending.
        """
        from mycosoft_mas.protocols.mmp import validate_actuation_intent

        if not validate_actuation_intent(intent):
            return {"error": f"Blocked intent: {intent}", "allowed": False}

        if not self.serial_conn or not self.serial_conn.is_open:
            return {"error": "Side A not connected"}

        cmd = json.dumps({"cmd": intent, **params}) + "\n"
        self.serial_conn.write(cmd.encode("utf-8"))
        self.serial_conn.flush()

        # Wait briefly for ACK
        await asyncio.sleep(0.5)
        self._drain_serial()

        return {"status": "sent", "intent": intent, "params": params}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    bridge = JetsonBridge()
    try:
        await bridge.run()
    except KeyboardInterrupt:
        pass
    finally:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
