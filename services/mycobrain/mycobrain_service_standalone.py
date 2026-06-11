#!/usr/bin/env python3
"""MycoBrain Service - Full Implementation with Proper Command Mapping and Network Heartbeat"""
import os
import sys
import json
import time
import logging
import threading
import asyncio
import httpx
import re
import struct
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Dict, Any, List
import secrets
from fastapi import FastAPI, Header, HTTPException, Query, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated

# Import authentication. Fail CLOSED when MYCOBRAIN_API_KEY is configured:
# the old silent "no-auth" fallback left /flash and /devices/*/command open
# (security audit JUN09_2026, finding M-7).
try:
    from auth import verify_api_key
    AUTH_ENABLED = True
except ImportError:
    AUTH_ENABLED = False

    def verify_api_key(x_api_key: str = Header(default=None, alias="X-API-Key")):
        expected = os.environ.get("MYCOBRAIN_API_KEY", "").strip()
        if expected:
            if not x_api_key or not secrets.compare_digest(x_api_key, expected):
                raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
            return x_api_key
        logging.getLogger("mycobrain").warning(
            "MYCOBRAIN_API_KEY unset - device control endpoints UNAUTHENTICATED"
        )
        return "no-auth"

# Import Tailscale utilities (optional)
try:
    from tailscale_utils import get_reachable_address, get_tailscale_ip
    TAILSCALE_UTILS_AVAILABLE = True
except ImportError:
    TAILSCALE_UTILS_AVAILABLE = False
    def get_reachable_address(public_host=None, port=8003):
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip, "lan"
        except Exception:
            return "127.0.0.1", "lan"

import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === Heartbeat Configuration ===
MAS_REGISTRY_URL = os.getenv("MAS_REGISTRY_URL", "http://192.168.0.188:8001")
DEVICE_NAME = os.getenv("MYCOBRAIN_DEVICE_NAME", "Local MycoBrain")
DEVICE_ROLE = os.getenv("MYCOBRAIN_DEVICE_ROLE", "standalone")  # mushroom1, sporebase, hyphae1, alarm, gateway, mycodrone, standalone
DEVICE_DISPLAY_NAME = os.getenv("MYCOBRAIN_DEVICE_DISPLAY_NAME")  # Optional UI name, e.g. "Mushroom 1"
DEVICE_LOCATION = os.getenv("MYCOBRAIN_DEVICE_LOCATION", "Unknown")
PUBLIC_HOST = os.getenv("MYCOBRAIN_PUBLIC_HOST")  # Optional: explicit host/URL
HEARTBEAT_INTERVAL = int(os.getenv("MYCOBRAIN_HEARTBEAT_INTERVAL", "30"))  # seconds
HEARTBEAT_ENABLED = os.getenv("MYCOBRAIN_HEARTBEAT_ENABLED", "true").lower() == "true"
ACTUATORS_ENABLED = os.getenv("MYCOBRAIN_ENABLE_ACTUATORS", "true").lower() in ("1", "true", "yes")
# Stable registry/portal id when USB port changes (e.g. COM3 hardware, COM4 UI id)
MYCOBRAIN_REGISTRY_ID = os.getenv("MYCOBRAIN_REGISTRY_ID", "").strip()

# Telemetry ingest bridge: push to website ingest API for Supabase/Device Manager
TELEMETRY_INGEST_URL = os.getenv("TELEMETRY_INGEST_URL", "")  # e.g. http://localhost:3010/api/devices/ingest
TELEMETRY_INGEST_API_KEY = os.getenv("TELEMETRY_INGEST_API_KEY", "")
MYCOBRAIN_MINDEX_ENVELOPE = os.getenv("MYCOBRAIN_MINDEX_ENVELOPE", "true").lower() in ("1", "true", "yes")

try:
    from envelope_bridge import extract_mindex_envelope, publish_envelope_async
except ImportError:
    extract_mindex_envelope = None  # type: ignore
    publish_envelope_async = None  # type: ignore


def _post_telemetry_ingest(url: str, payload: dict, headers: dict) -> None:
    """Fire-and-forget POST to ingest API. Runs in a daemon thread."""
    try:
        base = url.rstrip("/")
        ingest_url = f"{base}/api/devices/ingest" if "/api/devices/ingest" not in base else base
        resp = httpx.post(ingest_url, json=payload, headers=headers, timeout=10.0)
        if resp.status_code >= 400:
            logger.warning("Telemetry ingest returned %s: %s", resp.status_code, resp.text[:200])
    except Exception as ex:
        logger.warning("Telemetry ingest POST failed: %s", ex)


app = FastAPI(title="MycoBrain Service", version="2.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

_serial_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mycobrain-serial")

# Global state
devices: Dict[str, Dict] = {}
serial_connections: Dict[str, Any] = {}
telemetry_cache: Dict[str, Dict] = {}
_flash_in_progress = threading.Event()
_serial_locks: Dict[str, threading.Lock] = {}
_mdp_seq = 1
_mdp_seq_lock = threading.Lock()

# Side-A MDP firmware frame format (firmware/common_mdp/include/mdp_codec.h).
MDP_MAGIC = 0xA15A
MDP_VERSION = 0x01
MDP_TELEMETRY = 0x01
MDP_COMMAND = 0x02
MDP_ACK = 0x03
MDP_EVENT = 0x05
MDP_HELLO = 0x06
EP_SIDE_A = 0xA1
EP_GATEWAY = 0xC0
ACK_REQUESTED = 0x01

# Known ESP32/MycoBrain USB VIDs (Espressif, USB Serial adapters)
MYCOBRAIN_VIDS = {0x303A, 0x10C4, 0x1A86, 0x2341, 0x2A03, 0x046B}  # Espressif, Silabs, CH340, Arduino, USB Serial
ALLOWED_PORTS_RAW = os.getenv("MYCOBRAIN_ALLOWED_PORTS", "").strip()
ALLOWED_PORTS = {p.strip() for p in ALLOWED_PORTS_RAW.split(",") if p.strip()}


def _device_lock(device_id: str) -> threading.Lock:
    if device_id not in _serial_locks:
        _serial_locks[device_id] = threading.Lock()
    return _serial_locks[device_id]


def _attach_registry_identity(device: Dict[str, Any]) -> None:
    """Attach stable portal/registry id for UI and MAS heartbeat when port differs."""
    serial_id = str(device.get("device_id") or "")
    registry_id = MYCOBRAIN_REGISTRY_ID or serial_id
    device["registry_id"] = registry_id
    device["portal_device_id"] = registry_id
    device["serial_device_id"] = serial_id
    if DEVICE_ROLE:
        device["device_role"] = DEVICE_ROLE


def _resolve_device_id(requested_id: str) -> str:
    """Map portal ids (e.g. mycobrain-COM4) to the connected serial device (e.g. COM3)."""
    requested = (requested_id or "").strip()
    if not requested:
        return requested_id
    if requested in devices or requested in serial_connections:
        return requested
    requested_lower = requested.lower()
    for serial_id, device in devices.items():
        registry_id = str(
            device.get("registry_id") or device.get("portal_device_id") or serial_id
        )
        if registry_id.lower() == requested_lower:
            return serial_id
    if MYCOBRAIN_REGISTRY_ID and requested_lower == MYCOBRAIN_REGISTRY_ID.lower():
        if len(devices) == 1:
            return next(iter(devices.keys()))
        for serial_id, device in devices.items():
            role = str(device.get("device_role") or DEVICE_ROLE or "").lower()
            if role == "psathyrella":
                return serial_id
    return requested_id


def _registry_device_id(serial_device_id: str) -> str:
    device = devices.get(serial_device_id) or {}
    return str(device.get("registry_id") or device.get("portal_device_id") or serial_device_id)


def _next_mdp_seq() -> int:
    global _mdp_seq
    with _mdp_seq_lock:
        seq = _mdp_seq
        _mdp_seq = (_mdp_seq + 1) & 0xFFFFFFFF
        if _mdp_seq == 0:
            _mdp_seq = 1
    return seq


def _crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def _mdp_cobs_encode(data: bytes) -> bytes:
    out = bytearray([0])
    code_index = 0
    code = 1
    for byte in data:
        if byte == 0:
            out[code_index] = code
            code_index = len(out)
            out.append(0)
            code = 1
        else:
            out.append(byte)
            code += 1
            if code == 0xFF:
                out[code_index] = code
                code_index = len(out)
                out.append(0)
                code = 1
    out[code_index] = code
    return bytes(out)


def _mdp_cobs_decode(data: bytes) -> bytes:
    out = bytearray()
    read_index = 0
    while read_index < len(data):
        code = data[read_index]
        if code == 0:
            raise ValueError("invalid COBS code byte")
        read_index += 1
        for _ in range(1, code):
            if read_index >= len(data):
                raise ValueError("truncated COBS frame")
            out.append(data[read_index])
            read_index += 1
        if code != 0xFF and read_index < len(data):
            out.append(0)
    return bytes(out)


def _encode_mdp_command(cmd: str, params: Optional[Dict[str, Any]] = None) -> bytes:
    payload = json.dumps({"cmd": cmd, "params": params or {}}, separators=(",", ":")).encode("utf-8")
    seq = _next_mdp_seq()
    header = struct.pack(
        "<HBBIIBBBB",
        MDP_MAGIC,
        MDP_VERSION,
        MDP_COMMAND,
        seq,
        0,
        ACK_REQUESTED,
        EP_GATEWAY,
        EP_SIDE_A,
        0,
    )
    frame = header + payload
    crc = _crc16_ccitt_false(frame)
    return _mdp_cobs_encode(frame + struct.pack("<H", crc)) + b"\0"


def _decode_mdp_frame(encoded: bytes) -> Optional[Dict[str, Any]]:
    try:
        decoded = _mdp_cobs_decode(encoded)
        if len(decoded) < 18:
            return None
        magic, version, msg_type, seq, ack, flags, src, dst, rsv = struct.unpack("<HBBIIBBBB", decoded[:16])
        if magic != MDP_MAGIC or version != MDP_VERSION:
            return None
        got_crc = struct.unpack("<H", decoded[-2:])[0]
        expected_crc = _crc16_ccitt_false(decoded[:-2])
        if got_crc != expected_crc:
            return None
        payload_raw = decoded[16:-2]
        payload: Any
        try:
            payload = json.loads(payload_raw.decode("utf-8", errors="replace"))
        except Exception:
            payload = payload_raw.decode("utf-8", errors="replace")
        return {
            "msg_type": msg_type,
            "seq": seq,
            "ack": ack,
            "flags": flags,
            "src": src,
            "dst": dst,
            "payload": payload,
        }
    except Exception:
        return None


def _extract_mdp_frames(raw: bytes) -> List[Dict[str, Any]]:
    frames: List[Dict[str, Any]] = []
    for chunk in raw.split(b"\0"):
        if not chunk:
            continue
        frame = _decode_mdp_frame(chunk)
        if frame:
            frames.append(frame)
    return frames


def _extract_visible_text(raw: bytes) -> str:
    try:
        return raw.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def _mdp_payload_lines(frames: List[Dict[str, Any]], registry_id: Optional[str] = None) -> str:
    lines = []
    reg_id = registry_id or MYCOBRAIN_REGISTRY_ID or "mycobrain-local"
    for frame in frames:
        payload = frame.get("payload")
        if isinstance(payload, (dict, list)):
            lines.append(json.dumps(payload, separators=(",", ":")))
            if (
                MYCOBRAIN_MINDEX_ENVELOPE
                and publish_envelope_async
                and extract_mindex_envelope
                and frame.get("msg_type") == MDP_TELEMETRY
                and isinstance(payload, dict)
            ):
                env = extract_mindex_envelope(payload, reg_id)
                if env:
                    publish_envelope_async(env)
        elif payload is not None:
            lines.append(str(payload))
    return "\n".join(lines)


def _stop_buzzer_device(serial_device_id: str, timeout: float = 2.0) -> str:
    """Stop buzzer; legacy MDP firmware ignored value=0 and kept PWM on."""
    if serial_device_id not in serial_connections:
        raise ValueError(f"Device {serial_device_id} not connected")
    ser = serial_connections[serial_device_id]
    with _device_lock(serial_device_id):
        mdp = _cli_command_to_mdp("buzzer off")
        if mdp:
            mdp_cmd, mdp_params = mdp
            response = _send_mdp_command_sync(ser, mdp_cmd, mdp_params, timeout, serial_device_id)
            # side-a-mdp before timed-off fix: value=0 still calls ledcWriteTone(freq)
            if mdp_params.get("id") == "buzzer" and mdp_params.get("value") == 0:
                if "buzzer_stopped" not in response:
                    _send_mdp_command_sync(ser, "estop", {}, timeout, serial_device_id)
                    time.sleep(0.08)
                    _send_mdp_command_sync(ser, "clear_estop", {}, timeout, serial_device_id)
                    return "buzzer_stopped"
            return response.strip() if response else ""
        ser.reset_input_buffer()
        ser.write(b"buzzer off\r\n")
        ser.flush()
        time.sleep(0.3)
        return _extract_visible_text(ser.read(ser.in_waiting or 0)).strip()


def _schedule_buzzer_off(serial_device_id: str, delay_s: float) -> None:
    """Safety net when firmware lacks timed buzzer stop (pre-2.2.1 MDP builds)."""
    def _off() -> None:
        try:
            time.sleep(max(0.05, delay_s))
            if serial_device_id in serial_connections:
                _stop_buzzer_device(serial_device_id, timeout=2.0)
        except Exception as ex:
            logger.debug("scheduled buzzer off failed for %s: %s", serial_device_id, ex)

    threading.Thread(target=_off, daemon=True, name=f"buzzer-off-{serial_device_id}").start()


def _maybe_schedule_buzzer_off_after_beep(serial_device_id: str, command: str, mdp: Optional[tuple[str, Dict[str, Any]]]) -> None:
    if not mdp:
        return
    mdp_cmd, mdp_params = mdp
    if mdp_cmd != "output_control" or not isinstance(mdp_params, dict):
        return
    if mdp_params.get("id") != "buzzer" or mdp_params.get("value") != 1:
        return
    try:
        dur_ms = int(mdp_params.get("duration_ms") or 200)
    except (TypeError, ValueError):
        dur_ms = 200
    dur_ms = max(20, min(5000, dur_ms))
    _schedule_buzzer_off(serial_device_id, (dur_ms + 200) / 1000.0)


def _cli_command_to_mdp(command: str) -> Optional[tuple[str, Dict[str, Any]]]:
    cmd = command.strip()
    lower = cmd.lower()

    if lower in {"sensors", "sensor read", "read_sensors", "get-sensors", "get sensors"}:
        return "read_sensors", {}
    if lower in {"ping", "health"}:
        return "health", {}
    if lower in {"hello", "info", "get_version", "version"}:
        return "hello", {}

    if lower in {"buzzer off", "beep off", "tone off", "speaker off"}:
        return "output_control", {"id": "buzzer", "value": 0}

    if lower in {"led off", "neopixel off", "neopixel-off", "led mode off"}:
        return "output_control", {"id": "neopixel", "value": 0}

    if lower.startswith("led rgb"):
        parts = cmd.split()
        if len(parts) >= 5:
            try:
                r, g, b = int(parts[2]), int(parts[3]), int(parts[4])
                return "output_control", {"id": "neopixel", "value": 1, "r": r, "g": g, "b": b}
            except ValueError:
                pass

    if lower.startswith("beep "):
        parts = cmd.split()
        if len(parts) >= 3:
            try:
                freq = int(parts[1])
                dur = int(parts[2])
                return "output_control", {
                    "id": "buzzer",
                    "value": 1,
                    "freq": freq,
                    "duration_ms": dur,
                }
            except ValueError:
                pass

    return None


def _normalize_cli_command(command: str) -> str:
    cmd = command.strip()
    lower = cmd.lower()

    # Some legacy firmware builds treat bare "i2c" as "set pins to 0/0".
    if lower == "i2c":
        return "scan"
    if lower.startswith("i2c ") and not lower.startswith("i2c scan"):
        return "__blocked_i2c_reconfig__"

    if lower in {"led off", "neopixel off", "neopixel-off"}:
        return "led mode off"

    if not ACTUATORS_ENABLED:
        if lower.startswith("led ") or lower.startswith("neopixel ") or lower in {"rainbow", "neopixel-rainbow"}:
            return "__blocked_led_command__"
        if lower in {"morgio", "coin", "power", "1up", "bump", "buzzer beep", "beep"} or lower.startswith("beep "):
            return "__blocked_buzzer_command__"
        if lower.startswith("buzzer ") and lower not in {"buzzer off"}:
            return "__blocked_buzzer_command__"

    return cmd


def _send_mdp_command_sync(
    ser, mdp_cmd: str, params: Optional[Dict[str, Any]], timeout: float, serial_device_id: str = ""
) -> str:
    ser.reset_input_buffer()
    ser.write(_encode_mdp_command(mdp_cmd, params))
    ser.flush()

    raw = bytearray()
    end_time = time.time() + timeout
    saw_telemetry = False
    idle_deadline: Optional[float] = None
    want_telemetry = mdp_cmd == "read_sensors"
    while time.time() < end_time:
        waiting = getattr(ser, "in_waiting", 0)
        if waiting > 0:
            raw.extend(ser.read(waiting))
            frames = _extract_mdp_frames(bytes(raw))
            if frames:
                if any(f.get("msg_type") == MDP_TELEMETRY for f in frames):
                    saw_telemetry = True
                    idle_deadline = time.time() + 0.4
                elif not want_telemetry and any(
                    f.get("msg_type") in {MDP_ACK, MDP_HELLO, MDP_EVENT} for f in frames
                ):
                    break
        elif saw_telemetry and idle_deadline is not None and time.time() >= idle_deadline:
            break
        time.sleep(0.05)

    frames = _extract_mdp_frames(bytes(raw))
    if want_telemetry:
        telemetry_frames = [f for f in frames if f.get("msg_type") == MDP_TELEMETRY]
        if telemetry_frames:
            frames = telemetry_frames
    payload_lines = _mdp_payload_lines_for_device(frames, serial_device_id)
    visible = _extract_visible_text(bytes(raw))
    return payload_lines or visible


def _mdp_payload_lines_for_device(frames: List[Dict[str, Any]], serial_device_id: str) -> str:
    return _mdp_payload_lines(frames, _registry_device_id(serial_device_id))

def is_likely_mycobrain_port(p) -> bool:
    """Return True only for real USB serial devices (MycoBrain/ESP32), NOT virtual ACPI ports."""
    if p.vid is None:
        return False  # Virtual ports (COM1, COM2) have no VID
    if "ACPI" in (p.hwid or "").upper() or "PNP0501" in (p.hwid or "").upper():
        return False  # ACPI virtual serial - not a real device
    desc = (p.description or "").upper()
    if "USB" in desc or "SERIAL" in desc or "CH340" in desc or "CP210" in desc:
        return True
    if p.vid in MYCOBRAIN_VIDS:
        return True
    return False

def send_serial_command(device_id: str, command: str, timeout: float = 2.0) -> str:
    """Send a command to the device and return response"""
    if device_id not in serial_connections:
        raise ValueError(f"Device {device_id} not connected")
    
    ser = serial_connections[device_id]
    if not ser.is_open:
        raise ValueError("Serial connection closed")

    command = _normalize_cli_command(command)
    cmd_lower_stripped = command.strip().lower()
    if cmd_lower_stripped in {"buzzer off", "beep off", "tone off", "speaker off"}:
        return _stop_buzzer_device(device_id, timeout=timeout)
    if command == "__blocked_i2c_reconfig__":
        return "I2C pin reconfiguration is disabled in the local bridge because this COM4 firmware build mis-parses i2c pin arguments. Use scan/status/probe only."
    if command == "__blocked_buzzer_command__":
        return "Actuator commands are disabled (MYCOBRAIN_ENABLE_ACTUATORS=false). Set env true for local dev."
    if command == "__blocked_led_command__":
        return "LED commands are disabled (MYCOBRAIN_ENABLE_ACTUATORS=false). Set env true for local dev."
    
    with _device_lock(device_id):
        mdp = _cli_command_to_mdp(command)
        if mdp:
            try:
                mdp_cmd, mdp_params = mdp
                logger.info(f"Sending MDP to {device_id}: {mdp_cmd} {mdp_params}")
                response = _send_mdp_command_sync(ser, mdp_cmd, mdp_params, timeout, device_id)
                logger.info(f"MDP response from {device_id}: {response[:120]}...")
                if response:
                    _maybe_schedule_buzzer_off_after_beep(device_id, command, mdp)
                    return response.strip()
            except Exception as ex:
                logger.warning("MDP command failed for %s (%s), falling back to CLI: %s", device_id, command, ex)

        ser.reset_input_buffer()
        cmd_bytes = (command + "\r\n").encode('utf-8')
        logger.info(f"Sending CLI to {device_id}: {command}")
        try:
            ser.write(cmd_bytes)
        except Exception as write_err:
            logger.warning("Serial write failed for %s (%s): %s", device_id, command, write_err)
            return f"Serial write failed: {write_err}"

        time.sleep(0.5)
        raw = bytearray()
        response = ""
        end_time = time.time() + timeout
        while time.time() < end_time:
            if ser.in_waiting > 0:
                raw.extend(ser.read(ser.in_waiting))
                frames = _extract_mdp_frames(bytes(raw))
                if frames:
                    response = _mdp_payload_lines_for_device(frames, device_id)
                    break
                time.sleep(0.1)
            else:
                if raw:
                    break
                time.sleep(0.1)

        if not response:
            response = _extract_visible_text(bytes(raw))

        logger.info(f"Response from {device_id}: {response[:100]}...")
        return response.strip()

@app.get("/health")
async def health():
    return {
        "status": "ok", 
        "service": "mycobrain", 
        "version": "2.2.0", 
        "devices_connected": len(devices),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/devices")
async def list_devices():
    for device_id in list(devices.keys()):
        if device_id in serial_connections:
            try:
                ser = serial_connections[device_id]
                devices[device_id]["status"] = "connected" if ser.is_open else "disconnected"
            except Exception:
                devices[device_id]["status"] = "error"
        _attach_registry_identity(devices[device_id])
    return {"devices": list(devices.values()), "count": len(devices), "timestamp": datetime.now().isoformat()}

@app.get("/ports")
async def scan_ports():
    try:
        import serial.tools.list_ports
        ports = []
        for p in serial.tools.list_ports.comports():
            ports.append({
                "device": p.device,
                "description": p.description,
                "hwid": p.hwid,
                "vid": p.vid,
                "pid": p.pid,
                "likely_mycobrain": is_likely_mycobrain_port(p),
            })
        return {"ports": ports, "count": len(ports), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"ports": [], "count": 0, "error": str(e), "timestamp": datetime.now().isoformat()}

def _get_mycobrain_port_names() -> set:
    """Return set of port device names that look like MycoBrain (USB serial, not virtual)."""
    try:
        import serial.tools.list_ports
        ports = {p.device for p in serial.tools.list_ports.comports() if is_likely_mycobrain_port(p)}
        if ALLOWED_PORTS:
            return {p for p in ports if p in ALLOWED_PORTS}
        return ports
    except Exception:
        return set()

def _try_connect_port_sync(port: str) -> bool:
    """Sync connect to port. Returns True if connected. Thread-safe for port watcher."""
    import serial
    port = port.replace('-', '/') if port.startswith('COM-') else port
    if ALLOWED_PORTS and port not in ALLOWED_PORTS:
        logger.debug(f"Skipping {port}; not in MYCOBRAIN_ALLOWED_PORTS")
        return False
    device_id = f"mycobrain-{port.replace('/', '-').replace(':', '-')}"
    if device_id in serial_connections and serial_connections[device_id].is_open:
        return True
    try:
        ser = serial.Serial(port, 115200, timeout=2, write_timeout=1.0)
        time.sleep(0.5)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        serial_connections[device_id] = ser
        device_info = {"firmware": "unknown", "board": "MycoBrain ESP32-S3", "raw_status": ""}
        try:
            response = send_serial_command(device_id, "status", timeout=0.5)
            if "ESP32-S3" in response:
                device_info["board"] = "ESP32-S3"
            if "Arduino-ESP32 core:" in response:
                for line in response.split('\n'):
                    if "Arduino-ESP32 core:" in line:
                        device_info["firmware"] = line.split(':')[1].strip()
            device_info["raw_status"] = response[:500]
        except Exception:
            pass
        devices[device_id] = {
            "device_id": device_id,
            "port": port,
            "status": "connected",
            "connected_at": datetime.now().isoformat(),
            "info": device_info,
            "protocol": "MDP v1"
        }
        _attach_registry_identity(devices[device_id])
        try:
            from sensor_identity import refresh_device_identity
            refresh_device_identity(devices[device_id])
        except Exception as exc:
            logger.debug("sensor identity refresh on connect failed: %s", exc)
        logger.info(f"Auto-connected {device_id}")
        return True
    except Exception as e:
        logger.debug(f"Auto-connect {port} failed: {e}")
        return False

def _disconnect_device_sync(device_id: str) -> None:
    """Sync disconnect. Thread-safe for port watcher."""
    if device_id in serial_connections:
        try:
            serial_connections[device_id].close()
        except Exception:
            pass
        del serial_connections[device_id]
    if device_id in devices:
        del devices[device_id]
    logger.info(f"Auto-disconnected {device_id} (port unplugged)")


def _release_port_sync(port_hint: str) -> None:
    """Close serial handle so esptool can exclusive-open the port (Windows)."""
    port_norm = port_hint.replace("-", "/") if port_hint.startswith("COM-") else port_hint
    device_id = f"mycobrain-{port_norm.replace('/', '-').replace(':', '-')}"
    _disconnect_device_sync(device_id)
    time.sleep(0.75)

@app.post("/devices/connect/{port:path}")
async def connect_device(port: str, baudrate: int = 115200, api_key: str = Depends(verify_api_key)):
    import serial
    
    port = port.replace('-', '/') if port.startswith('COM-') else port
    if ALLOWED_PORTS and port not in ALLOWED_PORTS:
        raise HTTPException(
            status_code=400,
            detail=f"Port {port} is not in MYCOBRAIN_ALLOWED_PORTS",
        )
    device_id = f"mycobrain-{port.replace('/', '-').replace(':', '-')}"
    
    logger.info(f"Connecting to {port}")
    
    if device_id in serial_connections:
        ser = serial_connections[device_id]
        if ser.is_open:
            # Keep devices[] in sync without blocking serial I/O here (async worker must stay responsive)
            if device_id not in devices:
                devices[device_id] = {
                    "device_id": device_id,
                    "port": port,
                    "status": "connected",
                    "connected_at": datetime.now().isoformat(),
                    "info": {
                        "firmware": "unknown",
                        "board": "MycoBrain ESP32-S3",
                        "note": "Registry resynced from open serial handle",
                    },
                    "protocol": "MDP v1",
                }
            return {"status": "already_connected", "device_id": device_id, "port": port}
        del serial_connections[device_id]
    
    try:
        ser = serial.Serial(port, baudrate, timeout=2, write_timeout=1.0)
        time.sleep(1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        serial_connections[device_id] = ser
        
        device_info = {"firmware": "unknown", "board": "MycoBrain ESP32-S3"}
        try:
            response = send_serial_command(device_id, "status", timeout=0.5)
            if "ESP32-S3" in response:
                device_info["board"] = "ESP32-S3"
            if "Arduino-ESP32 core:" in response:
                for line in response.split('\n'):
                    if "Arduino-ESP32 core:" in line:
                        device_info["firmware"] = line.split(':')[1].strip()
            device_info["raw_status"] = response[:500]
        except Exception:
            pass
        
        devices[device_id] = {
            "device_id": device_id,
            "port": port,
            "status": "connected",
            "connected_at": datetime.now().isoformat(),
            "info": device_info,
            "protocol": "MDP v1"
        }
        _attach_registry_identity(devices[device_id])
        
        return {
            "status": "connected",
            "device_id": _registry_device_id(device_id),
            "serial_device_id": device_id,
            "port": port,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Connection error: {error_msg}")
        if "Access is denied" in error_msg or "PermissionError" in error_msg:
            raise HTTPException(status_code=403, detail=f"Port {port} is locked or in use.")
        raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")

@app.post("/devices/{device_id}/disconnect")
async def disconnect_device(device_id: str, api_key: str = Depends(verify_api_key)):
    serial_id = _resolve_device_id(device_id)
    if serial_id not in devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    try:
        if serial_id in serial_connections:
            serial_connections[serial_id].close()
            del serial_connections[serial_id]
        del devices[serial_id]
        return {"status": "disconnected", "device_id": _registry_device_id(serial_id), "serial_device_id": serial_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, command: str = Query(None), body: dict = Body(default=None), api_key: str = Depends(verify_api_key)):
    """Send a command to the device - supports both query param and JSON body"""
    serial_id = _resolve_device_id(device_id)
    if serial_id not in devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    cmd = command
    if not cmd and body:
        if "command" in body:
            cmd_data = body["command"]
            if isinstance(cmd_data, dict):
                # Support both "cmd" and "command_type" formats
                cmd_type = cmd_data.get("command_type") or cmd_data.get("cmd", "")
                cmd = map_command(cmd_type, cmd_data)
            else:
                cmd = str(cmd_data)
        elif "raw_command" in body:
            cmd = body["raw_command"]
    
    if not cmd:
        raise HTTPException(status_code=400, detail="No command provided")

    cmd_lower = str(cmd).strip().lower()
    serial_timeout = 8.0 if "read_sensors" in cmd_lower or cmd_lower in {"sensors", "sensor read"} else 2.5
    
    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            _serial_executor, lambda: send_serial_command(serial_id, cmd, timeout=serial_timeout)
        )
        return {
            "status": "ok",
            "device_id": _registry_device_id(serial_id),
            "serial_device_id": serial_id,
            "command": cmd,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def map_command(cmd_type: str, params: dict) -> str:
    """Map frontend command types to device commands"""
    mappings = {
        # System commands - both formats
        "status": lambda p: "status",
        "ping": lambda p: "ping",
        "info": lambda p: "info",
        
        # LED commands
        "neopixel-set": lambda p: f"led rgb {p.get('r', 0)} {p.get('g', 255)} {p.get('b', 0)}",
        "neopixel-rainbow": lambda p: "led pattern rainbow",
        "neopixel-off": lambda p: "led off",
        "led-set": lambda p: f"led rgb {p.get('r', 0)} {p.get('g', 255)} {p.get('b', 0)}",
        "set_led": lambda p: f"led rgb {p.get('r', 0)} {p.get('g', 0)} {p.get('b', 0)}",
        "set_neopixel": lambda p: f"led rgb {p.get('r', 0)} {p.get('g', 0)} {p.get('b', 0)}",
        
        # Buzzer/sound commands
        "buzzer-beep": lambda p: f"beep {p.get('frequency', 1000)} {p.get('duration', p.get('duration_ms', 200))}",
        "buzzer-melody": lambda p: "morgio",
        "buzzer-tone": lambda p: f"beep {p.get('frequency', 1000)} {p.get('duration', p.get('duration_ms', 200))}",
        "set_buzzer": lambda p: f"beep {p.get('frequency', 1000)} {p.get('duration', p.get('duration_ms', 200))}",
        "beep": lambda p: f"beep {p.get('frequency', 1000)} {p.get('duration', p.get('duration_ms', 200))}",
        "play_sound": lambda p: p.get('sound', 'coin'),
        
        # Sensor commands
        "read-bme1": lambda p: "probe amb",
        "read-bme2": lambda p: "probe env",
        "scan-i2c": lambda p: "scan",
        "i2c-scan": lambda p: "scan",
        "get-sensors": lambda p: "read_sensors",
        "read_sensors": lambda p: "read_sensors",
        "read-sensors": lambda p: "read_sensors",
        
        # Live mode
        "live-on": lambda p: "live on",
        "live-off": lambda p: "live off",
        "json-mode": lambda p: "fmt json",
    }
    
    if cmd_type in mappings:
        return mappings[cmd_type](params)
    
    return cmd_type

@app.get("/devices/{device_id}/telemetry")
async def get_telemetry(device_id: str):
    serial_id = _resolve_device_id(device_id)
    if serial_id not in serial_connections:
        raise HTTPException(status_code=400, detail=f"Device {device_id} not connected")
    
    try:
        telemetry: Dict[str, Any]
        raw_status = ""
        read_response = send_serial_command(serial_id, "read_sensors", timeout=10.0)
        raw_status = read_response
        parsed = _telemetry_from_read_sensors_response(read_response)
        if parsed:
            telemetry = parsed
        else:
            response = send_serial_command(serial_id, "status", timeout=2.0)
            raw_status = response
            telemetry = {"raw": response}
            for line in response.split('\n'):
                if "AMB addr=0x77" in line or ("AMB:" in line and "addr=0x77" in line):
                    telemetry["bme1"] = parse_sensor_line(line, "amb")
                    telemetry["bme1"]["i2c_address"] = 0x77
                elif "ENV addr=0x76" in line or ("ENV:" in line and "addr=0x76" in line):
                    telemetry["bme2"] = parse_sensor_line(line, "env")
                    telemetry["bme2"]["i2c_address"] = 0x76
                elif line.strip().startswith("AMB:"):
                    telemetry.setdefault("bme1", {"type": "amb", "i2c_address": 0x77})
                    if "present=NO" in line:
                        telemetry["bme1"]["status"] = "not_detected"
                elif line.strip().startswith("ENV:"):
                    telemetry.setdefault("bme2", {"type": "env", "i2c_address": 0x76})
                    if "present=NO" in line:
                        telemetry["bme2"]["status"] = "not_detected"

        telemetry_cache[serial_id] = telemetry

        try:
            from sensor_identity import refresh_device_identity, attach_sensor_ids_to_readings

            refresh_device_identity(devices.get(serial_id, {"device_id": serial_id, "info": {"raw_status": raw_status[:500]}}), telemetry)
            board_id = devices[serial_id].get("board_id")
        except Exception as exc:
            logger.debug("sensor identity refresh on telemetry failed: %s", exc)
            board_id = None

        # Push to ingest API for Supabase / Device Manager (fire-and-forget)
        if TELEMETRY_INGEST_URL:
            try:
                readings = []
                if "bme1" in telemetry and isinstance(telemetry["bme1"], dict):
                    r = telemetry["bme1"].copy()
                    r["sensor_type"] = r.get("type", "amb")
                    r["sensor_slot"] = "bme688_a"
                    readings.append(r)
                if "bme2" in telemetry and isinstance(telemetry["bme2"], dict):
                    r = telemetry["bme2"].copy()
                    r["sensor_type"] = r.get("type", "env")
                    r["sensor_slot"] = "bme688_b"
                    readings.append(r)
                registry_id = _registry_device_id(serial_id)
                if board_id and readings:
                    readings = attach_sensor_ids_to_readings(board_id, registry_id, readings)
                if readings:
                    ingest_payload = {
                        "deviceId": registry_id,
                        "boardId": board_id,
                        "deviceType": "mycobrain",
                        "timestamp": datetime.now().isoformat(),
                        "readings": readings,
                    }
                    headers = {"Content-Type": "application/json"}
                    if TELEMETRY_INGEST_API_KEY:
                        headers["Authorization"] = f"Bearer {TELEMETRY_INGEST_API_KEY}"
                        headers["x-api-key"] = TELEMETRY_INGEST_API_KEY
                    threading.Thread(
                        target=_post_telemetry_ingest,
                        args=(TELEMETRY_INGEST_URL, ingest_payload, headers),
                        daemon=True,
                    ).start()
            except Exception as ex:
                logger.warning("Telemetry ingest bridge start failed: %s", ex)

        return {
            "status": "ok",
            "device_id": _registry_device_id(serial_id),
            "serial_device_id": serial_id,
            "board_id": devices.get(serial_id, {}).get("board_id"),
            "sensor_instances": devices.get(serial_id, {}).get("sensor_instances", []),
            "telemetry": telemetry,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _bme_slot_from_envelope_pack(pack: Any) -> Optional[Dict[str, Any]]:
    """Map MDP pack[] to bme688_a fields when firmware ids are garbled (use unit + id hints)."""
    if not isinstance(pack, list):
        return None
    slot: Dict[str, Any] = {}
    eco2: Optional[float] = None
    bvoc: Optional[float] = None

    def _num(val: Any) -> Optional[float]:
        try:
            f = float(val)
            return f if f == f else None  # NaN guard
        except (TypeError, ValueError):
            return None

    for item in pack:
        if not isinstance(item, dict):
            continue
        unit = str(item.get("u") or "").strip()
        pid = str(item.get("id") or "").lower()
        val = _num(item.get("v"))
        if val is None:
            continue
        if unit == "C" or pid.endswith(".tc") or "temp" in pid:
            slot["temperature_c"] = val
        elif unit == "%" or pid.endswith(".rh") or "humid" in pid:
            slot["humidity_pct"] = val
        elif unit == "hPa" or pid.endswith(".p") or "press" in pid:
            slot["pressure_hpa"] = val
        elif unit == "Ohm" or pid.endswith(".gas") or "gas" in pid:
            slot["gas_ohm"] = val
        elif unit == "IAQ" or pid.endswith(".iaq"):
            slot["iaq"] = val
        elif unit == "ppm":
            if "eco2" in pid or "co2" in pid:
                eco2 = val
            elif "bvoc" in pid or "voc" in pid:
                bvoc = val
            elif eco2 is None:
                eco2 = val
            elif bvoc is None:
                bvoc = val
    if eco2 is not None:
        slot["co2_equivalent"] = eco2
    if bvoc is not None:
        slot["voc_equivalent"] = bvoc
    return slot if slot else None


def _slot_dict_to_bme_reading(slot: dict, sensor_type: str, i2c_address: int) -> dict:
    """Map firmware bme688.a/b JSON to legacy bme1/bme2 + ingest fields."""
    data: Dict[str, Any] = {"type": sensor_type, "i2c_address": i2c_address}
    for src, dst in (
        ("temperature_c", "temperature"),
        ("humidity_pct", "humidity"),
        ("pressure_hpa", "pressure"),
        ("gas_ohm", "gas_resistance"),
        ("iaq", "iaq"),
        ("co2_equivalent", "co2_equivalent"),
        ("voc_equivalent", "voc_equivalent"),
    ):
        val = slot.get(src)
        if val is not None:
            try:
                data[dst] = float(val)
            except (TypeError, ValueError):
                data[dst] = val
    return data


def _bme_slot_from_envelope_regex(response: str) -> Optional[Dict[str, Any]]:
    """When MDP JSON is truncated on the wire, extract BME readings by unit from raw text."""
    if "mycosoft.envelope.v1" not in response:
        return None

    def _unit_value(unit: str) -> Optional[float]:
        match = re.search(
            rf'"v"\s*:\s*([-+0-9.eE]+)\s*,\s*"u"\s*:\s*"{re.escape(unit)}"',
            response,
            re.IGNORECASE,
        )
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    slot: Dict[str, Any] = {}
    for key, unit in (
        ("temperature_c", "C"),
        ("humidity_pct", "%"),
        ("pressure_hpa", "hPa"),
        ("gas_ohm", "Ohm"),
        ("iaq", "IAQ"),
    ):
        val = _unit_value(unit)
        if val is not None:
            slot[key] = val
    ppm_matches = list(
        re.finditer(r'"v"\s*:\s*([-+0-9.eE]+)\s*,\s*"u"\s*:\s*"ppm"', response, re.IGNORECASE)
    )
    if ppm_matches:
        try:
            slot["co2_equivalent"] = float(ppm_matches[0].group(1))
        except ValueError:
            pass
        if len(ppm_matches) > 1:
            try:
                slot["voc_equivalent"] = float(ppm_matches[1].group(1))
            except ValueError:
                pass
    return slot if slot else None


def _telemetry_from_read_sensors_response(response: str) -> Optional[Dict[str, Any]]:
    """Parse MDP read_sensors / telemetry JSON (bme688.a/b) from mixed serial text."""
    if not response:
        return None
    if "mycosoft.envelope.v1" in response:
        slot_a = _bme_slot_from_envelope_regex(response)
        if slot_a:
            telemetry: Dict[str, Any] = {"raw": response, "schema": "mycosoft.envelope.v1"}
            telemetry["bme688"] = {"a": slot_a}
            telemetry["bme1"] = _slot_dict_to_bme_reading(slot_a, "amb", 0x77)
            return telemetry
    for line in response.splitlines():
        chunk = line.strip()
        if not chunk.startswith("{"):
            continue
        try:
            obj = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("schema") == "mycosoft.envelope.v1" and MYCOBRAIN_MINDEX_ENVELOPE:
            reg_id = MYCOBRAIN_REGISTRY_ID or "mycobrain-local"
            if extract_mindex_envelope and publish_envelope_async:
                env = extract_mindex_envelope(obj, reg_id)
                if env:
                    publish_envelope_async(env)
            telemetry: Dict[str, Any] = {"raw": response, "envelope": obj, "schema": "mycosoft.envelope.v1"}
            slot_a = _bme_slot_from_envelope_pack(obj.get("pack"))
            if slot_a:
                telemetry["bme688"] = {"a": slot_a}
                telemetry["bme1"] = _slot_dict_to_bme_reading(slot_a, "amb", 0x77)
            return telemetry
        bme = obj.get("bme688")
        if not isinstance(bme, dict):
            continue
        telemetry: Dict[str, Any] = {"raw": response, "bme688": bme}
        a = bme.get("a")
        if isinstance(a, dict):
            telemetry["bme1"] = _slot_dict_to_bme_reading(a, "amb", 0x77)
        b = bme.get("b")
        if isinstance(b, dict):
            telemetry["bme2"] = _slot_dict_to_bme_reading(b, "env", 0x76)
        if telemetry.get("bme1") or telemetry.get("bme2"):
            return telemetry
    return None


def parse_sensor_line(line: str, sensor_type: str) -> dict:
    """Parse sensor data from status output line"""
    data = {"type": sensor_type}
    try:
        if "T=" in line:
            t_part = line.split("T=")[1].split("C")[0]
            data["temperature"] = float(t_part)
        if "RH=" in line:
            rh_part = line.split("RH=")[1].split("%")[0]
            data["humidity"] = float(rh_part)
        if "P=" in line:
            p_part = line.split("P=")[1].split("hPa")[0]
            data["pressure"] = float(p_part)
        if "Gas=" in line:
            gas_part = line.split("Gas=")[1].split("Ohm")[0]
            data["gas_resistance"] = float(gas_part)
        if "IAQ=" in line:
            iaq_part = line.split("IAQ=")[1].split(" ")[0]
            data["iaq"] = float(iaq_part)
    except Exception:
        pass
    return data

@app.get("/devices/{device_id}/sensors")
async def get_device_sensors(device_id: str):
    serial_id = _resolve_device_id(device_id)
    if serial_id not in devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    device = devices[serial_id]
    try:
        from sensor_identity import refresh_device_identity

        cached = telemetry_cache.get(serial_id)
        refresh_device_identity(device, cached if isinstance(cached, dict) else None)
    except Exception as exc:
        logger.debug("sensor identity refresh on /sensors failed: %s", exc)
    return {
        "status": "ok",
        "device_id": _registry_device_id(serial_id),
        "serial_device_id": serial_id,
        "board_id": device.get("board_id"),
        "sensor_instances": device.get("sensor_instances", []),
        "timestamp": datetime.now().isoformat(),
    }

class FlashRequest(BaseModel):
    profile: str
    version: Optional[str] = None
    artifact_url: Optional[str] = None
    artifact_path: Optional[str] = None
    port: Optional[str] = None
    confirm: bool = False
    dry_run: bool = True
    sha256: Optional[str] = None


@app.post("/flash")
async def flash_device(body: FlashRequest = Body(...), api_key: str = Depends(verify_api_key)):
    """
    Host-side esptool flash for allowlisted serial port (Phase 0 COM4).
    Destructive write requires confirm=true AND APPROVE_FLASH=true in service env.
    """
    import sys
    from pathlib import Path

    svc_dir = Path(__file__).resolve().parent
    if str(svc_dir) not in sys.path:
        sys.path.insert(0, str(svc_dir))
    import flash_executor

    port_hint = body.port or os.getenv("MYCOBRAIN_SERIAL_PORT", "COM4")
    device_id = f"mycobrain-{port_hint.replace('/', '-').replace(':', '-')}"
    had_connection = device_id in serial_connections
    _flash_in_progress.set()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: _release_port_sync(port_hint))

    try:
        result = await loop.run_in_executor(
            None,
            lambda: flash_executor.create_flash_job(
                profile=body.profile,
                version=body.version,
                artifact_url=body.artifact_url,
                artifact_path=body.artifact_path,
                port=body.port,
                confirm=body.confirm,
                dry_run=body.dry_run,
                sha256_expected=body.sha256,
            ),
        )
        return result
    finally:
        _flash_in_progress.clear()
        if had_connection and not body.dry_run:
            port_norm = port_hint.replace("-", "/") if port_hint.startswith("COM-") else port_hint
            await loop.run_in_executor(None, lambda p=port_norm: _try_connect_port_sync(p))


@app.get("/flash/jobs/{job_id}")
async def get_flash_job(job_id: str):
    import flash_executor

    job = flash_executor.get_flash_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")
    return job


@app.get("/flash/jobs")
async def list_flash_jobs(limit: int = Query(20, ge=1, le=100)):
    import flash_executor

    return {
        "jobs": flash_executor.list_flash_jobs(limit=limit),
        "esptool_available": flash_executor.esptool_available(),
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/clear-locks")
async def clear_locks(api_key: str = Depends(verify_api_key)):
    disconnected = []
    for device_id in list(serial_connections.keys()):
        try:
            serial_connections[device_id].close()
            del serial_connections[device_id]
            if device_id in devices:
                del devices[device_id]
            disconnected.append(device_id)
        except Exception:
            pass
    return {"status": "ok", "disconnected": disconnected}


# === Heartbeat System ===

def parse_device_role_from_status(raw_status: str) -> tuple:
    """Parse device_role and device_display_name from device status response (if firmware provides it)."""
    role = None
    display_name = None
    try:
        # Look for role= or device_role= in status output
        for line in raw_status.split('\n'):
            line_lower = line.lower()
            if 'device_role=' in line_lower or 'role=' in line_lower:
                parts = line.split('=')
                if len(parts) >= 2:
                    role = parts[1].strip().split()[0].strip('"\'')
            if 'device_display_name=' in line_lower or 'display_name=' in line_lower:
                # Handle display_name which may have spaces
                if '=' in line:
                    display_name = line.split('=', 1)[1].strip().strip('"\'')
        # Try JSON parsing if status is JSON
        if raw_status.strip().startswith('{'):
            import json
            try:
                data = json.loads(raw_status)
                role = data.get('device_role') or data.get('role') or role
                display_name = data.get('device_display_name') or data.get('display_name') or display_name
            except Exception:
                pass
    except Exception:
        pass
    return role, display_name


async def send_heartbeat(device_id: str, device: Dict[str, Any], host: str, port: int, connection_type: str):
    """Send a heartbeat registration to the MAS device registry."""
    try:
        # Try to get device_role and display_name from device status (firmware)
        raw_status = device.get("info", {}).get("raw_status", "")
        fw_role, fw_display_name = parse_device_role_from_status(raw_status)
        
        # Priority: firmware-reported > env var > default
        device_role = fw_role or DEVICE_ROLE
        device_display_name = fw_display_name or DEVICE_DISPLAY_NAME  # None if not set

        # Use capability manifest for sensors/capabilities (canonical contract)
        from capability_manifest import get_manifest_for_role, get_default_manifest
        sensors, capabilities = get_manifest_for_role(device_role)
        if not sensors and not capabilities:
            sensors, capabilities = get_default_manifest()

        device_board_id = device.get("board_id")
        sensor_instances = device.get("sensor_instances") or []
        if not sensor_instances:
            try:
                from sensor_identity import refresh_device_identity

                refresh_device_identity(device)
                device_board_id = device.get("board_id")
                sensor_instances = device.get("sensor_instances") or []
            except Exception as exc:
                logger.debug("sensor identity refresh before heartbeat failed: %s", exc)
        
        # Build heartbeat payload (serial ingestion; same format for future LoRa/BT/WiFi gateways)
        registry_id = _registry_device_id(device_id)
        payload = {
            "device_id": registry_id,
            "device_name": DEVICE_NAME,
            "device_role": device_role,
            "device_display_name": device_display_name,
            "host": host,
            "port": port,
            "firmware_version": device.get("info", {}).get("firmware", "unknown"),
            "board_type": device.get("info", {}).get("board", "ESP32-S3"),
            "sensors": sensors,
            "capabilities": capabilities,
            "location": DEVICE_LOCATION,
            "connection_type": connection_type,
            "ingestion_source": "serial",
            "board_id": device_board_id,
            "portal_device_id": registry_id,
            "sensor_instances": sensor_instances,
            "extra": {
                "protocol": device.get("protocol", "MDP v1"),
                "port_name": device.get("port", ""),
                "serial_device_id": device_id,
                "service_version": "2.2.0",
                "board_id": device_board_id,
                "sensor_instances": sensor_instances,
                # All MDP serial ids on this process (same host:port in MAS); used for multi-board gateways
                "mdp_device_ids_on_host": list(devices.keys()),
            }
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{MAS_REGISTRY_URL}/api/devices/heartbeat",
                json=payload,
            )
            
            if response.status_code == 200:
                result = response.json()
                status = result.get("status", "unknown")
                if status == "registered":
                    logger.info(f"Device {device_id} registered with MAS")
                else:
                    logger.debug(f"Device {device_id} heartbeat sent: {status}")
            else:
                logger.warning(f"Heartbeat failed for {device_id}: {response.status_code}")
                
    except httpx.ConnectError:
        logger.debug(f"Cannot connect to MAS registry at {MAS_REGISTRY_URL}")
    except Exception as e:
        logger.warning(f"Heartbeat error for {device_id}: {e}")


async def heartbeat_loop():
    """Background task that sends heartbeats for all connected devices."""
    logger.info(f"Heartbeat loop started (interval: {HEARTBEAT_INTERVAL}s, registry: {MAS_REGISTRY_URL})")
    
    port = int(os.getenv("MYCOBRAIN_SERVICE_PORT", "8003"))
    
    while True:
        try:
            # Get reachable address
            host, connection_type = get_reachable_address(PUBLIC_HOST, port)
            
            # Send heartbeat for each connected device
            for device_id, device in list(devices.items()):
                if device.get("status") == "connected":
                    await send_heartbeat(device_id, device, host, port, connection_type)
            
            # If no devices connected, still send a service heartbeat
            if not devices:
                # Register the service itself as available
                service_payload = {
                    "device_id": f"mycobrain-service-{host.replace('.', '-')}",
                    "device_name": f"{DEVICE_NAME} · HTTP service (no ESP32 in /devices yet)",
                    "device_role": "gateway",
                    "device_display_name": DEVICE_DISPLAY_NAME,
                    "host": host,
                    "port": port,
                    "firmware_version": "service-only",
                    "board_type": "service",
                    "sensors": [],
                    "capabilities": ["service"],
                    "location": DEVICE_LOCATION,
                    "connection_type": connection_type,
                    "ingestion_source": "serial",
                    "extra": {
                        "service_version": "2.2.0",
                        "status": "waiting_for_device",
                        "mdp_device_ids_on_host": [],
                    }
                }
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        await client.post(f"{MAS_REGISTRY_URL}/api/devices/heartbeat", json=service_payload)
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")
        
        await asyncio.sleep(HEARTBEAT_INTERVAL)


_heartbeat_task: Optional[asyncio.Task] = None
_port_watcher_task: Optional[asyncio.Task] = None
PORT_WATCH_INTERVAL = float(os.getenv("MYCOBRAIN_PORT_WATCH_INTERVAL", "2.0"))

async def port_watcher_loop():
    """Periodically scan for MycoBrain ports, auto-connect new ones, auto-disconnect unplugged.
    Only connects to real USB serial devices (COM7, etc.), never virtual ports (COM1, COM2).
    WiFi/BLE/LoRa devices from other machines appear via MAS registry /api/devices."""
    loop = asyncio.get_event_loop()
    logger.info(f"Port watcher started (interval: {PORT_WATCH_INTERVAL}s)")
    while True:
        try:
            if _flash_in_progress.is_set():
                await asyncio.sleep(PORT_WATCH_INTERVAL)
                continue
            real_ports = await loop.run_in_executor(None, _get_mycobrain_port_names)
            # Disconnect devices whose port was unplugged
            for device_id in list(devices.keys()):
                port = devices[device_id].get("port", "")
                if port and port not in real_ports:
                    await loop.run_in_executor(None, lambda d=device_id: _disconnect_device_sync(d))
            # Connect to new MycoBrain ports
            for port in real_ports:
                device_id = f"mycobrain-{port.replace('/', '-').replace(':', '-')}"
                if device_id not in devices or device_id not in serial_connections:
                    await loop.run_in_executor(None, lambda p=port: _try_connect_port_sync(p))
        except Exception as e:
            logger.debug(f"Port watcher tick: {e}")
        await asyncio.sleep(PORT_WATCH_INTERVAL)

@app.on_event("startup")
async def startup_event():
    """Start heartbeat and port watcher on service startup."""
    global _heartbeat_task, _port_watcher_task

    # Disconnect any fake devices (COM1, COM2) that may have been connected before
    real_ports = await asyncio.get_event_loop().run_in_executor(None, _get_mycobrain_port_names)
    for device_id in list(devices.keys()):
        port = devices[device_id].get("port", "")
        if port and port not in real_ports:
            await asyncio.get_event_loop().run_in_executor(None, lambda d=device_id: _disconnect_device_sync(d))

    _port_watcher_task = asyncio.create_task(port_watcher_loop())
    logger.info("Port watcher enabled - instant plug/unplug detection")

    if HEARTBEAT_ENABLED:
        _heartbeat_task = asyncio.create_task(heartbeat_loop())
        logger.info("Heartbeat system enabled")
    else:
        logger.info("Heartbeat system disabled (set MYCOBRAIN_HEARTBEAT_ENABLED=true to enable)")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop heartbeat and port watcher on service shutdown."""
    global _heartbeat_task, _port_watcher_task

    if _port_watcher_task:
        _port_watcher_task.cancel()
        try:
            await _port_watcher_task
        except asyncio.CancelledError:
            pass
        logger.info("Port watcher stopped")

    if _heartbeat_task:
        _heartbeat_task.cancel()
        try:
            await _heartbeat_task
        except asyncio.CancelledError:
            pass
        logger.info("Heartbeat loop stopped")


if __name__ == "__main__":
    port = int(os.getenv("MYCOBRAIN_SERVICE_PORT", "8003"))
    logger.info(f"Starting MycoBrain service v2.2 on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
