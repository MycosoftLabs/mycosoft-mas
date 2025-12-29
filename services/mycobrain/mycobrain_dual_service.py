#!/usr/bin/env python3
"""
MycoBrain Dual ESP32 Service
Handles both Side-A (Sensor MCU) and Side-B (Router MCU)
Enhanced with MDP protocol support, MAC address registration, and I2C detection
"""
import os
import sys
import json
import time
import struct
import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Try to import MDP protocol
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mycosoft_mas"))
    from protocols.mdp_v1 import (
        MDPEncoder, MDPDecoder, MDPTelemetry, MDPCommand, 
        MDPMessageType, MDPFrame
    )
    MDP_AVAILABLE = True
except ImportError:
    logger.warning("MDP protocol not available, using basic JSON mode")
    MDP_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="MycoBrain Dual ESP32 Service", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Device storage with enhanced metadata
devices: Dict[str, Dict[str, Any]] = {}

# Telemetry cache (latest telemetry per device)
telemetry_cache: Dict[str, Dict[str, Any]] = {}

# Background reader threads
reader_threads: Dict[str, threading.Thread] = {}

class DeviceConnectionRequest(BaseModel):
    port: str
    side: str = "auto"
    baudrate: int = 115200

class CommandRequest(BaseModel):
    command: Dict[str, Any]
    use_mdp: bool = False

def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return crc

def cobs_encode(data: bytes) -> bytes:
    out = bytearray([0])
    code_i, code = 0, 1
    for b in data:
        if b == 0:
            out[code_i] = code
            code_i = len(out)
            out.append(0)
            code = 1
        else:
            out.append(b)
            code += 1
            if code == 0xFF:
                out[code_i] = code
                code_i = len(out)
                out.append(0)
                code = 1
    out[code_i] = code
    out.append(0)
    return bytes(out)

@app.get("/health")
async def health():
    side_a = sum(1 for d in devices.values() if d.get("side") == "side-a")
    side_b = sum(1 for d in devices.values() if d.get("side") == "side-b")
    return {"status": "ok", "service": "mycobrain-dual", "version": "2.0.0", 
            "devices_connected": len(devices), "side_a_connected": side_a, "side_b_connected": side_b,
            "timestamp": datetime.now().isoformat()}

@app.get("/devices")
async def list_devices():
    return {"devices": [{"device_id": d["device_id"], "port": d["port"], "side": d.get("side", "unknown"), 
                         "status": d["status"], "connected_at": d.get("connected_at")} for d in devices.values()],
            "count": len(devices), "timestamp": datetime.now().isoformat()}

def _get_ports():
    """Helper to get available ports"""
    try:
        import serial.tools.list_ports
        return [{"port": p.device, "description": p.description, "vid": hex(p.vid) if p.vid else None,
                 "pid": hex(p.pid) if p.pid else None, "likely_esp32": p.vid == 0x303A or "USB Serial" in p.description,
                 "is_mycobrain": "USB Serial" in p.description}
                for p in serial.tools.list_ports.comports()]
    except Exception as e:
        logger.error(f"Error scanning ports: {e}")
        return []

@app.get("/ports")
async def get_ports():
    """Get available serial ports (website compatibility)"""
    ports = _get_ports()
    return {"ports": ports, "discovery_running": False, "timestamp": datetime.now().isoformat()}

@app.post("/devices/scan")
async def scan_ports():
    ports = _get_ports()
    return {"status": "ok", "ports": ports}

def _read_device_telemetry(device_id: str, port: str, baudrate: int, side: str):
    """Background thread to continuously read telemetry from device."""
    import serial
    buffer = bytearray()
    decoder = MDPDecoder() if MDP_AVAILABLE else None
    
    while device_id in devices and devices[device_id].get("status") == "connected":
        try:
            ser = devices[device_id].get("serial_handle")
            if not ser or not ser.is_open:
                break
            
            # Read available data
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                buffer.extend(data)
                
                # Try to parse MDP frames or JSON lines
                if MDP_AVAILABLE and decoder:
                    # Look for COBS frame delimiter (0x00)
                    while 0x00 in buffer:
                        delimiter_index = buffer.index(0x00)
                        frame_data = bytes(buffer[:delimiter_index + 1])
                        buffer = buffer[delimiter_index + 1:]
                        
                        if len(frame_data) > 1:
                            try:
                                frame, parsed = decoder.decode(frame_data)
                                if isinstance(parsed, MDPTelemetry):
                                    telemetry_cache[device_id] = {
                                        "device_id": device_id,
                                        "side": side,
                                        "timestamp": datetime.now().isoformat(),
                                        "telemetry": parsed.to_dict(),
                                        "sequence": frame.sequence
                                    }
                                    logger.debug(f"Received telemetry from {device_id}: {parsed.temperature}°C")
                            except Exception as e:
                                logger.debug(f"Failed to decode MDP frame: {e}")
                
                # Also try JSON lines (fallback)
                while b'\n' in buffer:
                    line_end = buffer.index(b'\n')
                    line = bytes(buffer[:line_end])
                    buffer = buffer[line_end + 1:]
                    
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if isinstance(data, dict):
                                telemetry_cache[device_id] = {
                                    "device_id": device_id,
                                    "side": side,
                                    "timestamp": datetime.now().isoformat(),
                                    "telemetry": data,
                                    "raw": True
                                }
                        except:
                            pass
            
            time.sleep(0.1)  # Small delay to avoid CPU spinning
            
        except Exception as e:
            logger.error(f"Error reading from {device_id}: {e}")
            time.sleep(1)
    
    logger.info(f"Reader thread stopped for {device_id}")


def _query_device_info(ser, side: str) -> Dict[str, Any]:
    """Query device for MAC address, firmware version, and I2C sensors."""
    info = {
        "mac_address": None,
        "firmware_version": None,
        "i2c_sensors": [],
        "device_type": "mycobrain",
        "side": side
    }
    
    try:
        # Try to get device info via commands
        commands = [
            {"cmd": "get_mac"},
            {"cmd": "get_version"},
            {"cmd": "i2c_scan"},
        ]
        
        for cmd in commands:
            try:
                ser.reset_input_buffer()
                cmd_str = json.dumps(cmd) + "\n"
                ser.write(cmd_str.encode('utf-8'))
                ser.flush()
                time.sleep(0.3)
                
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting).decode('utf-8', errors='replace').strip()
                    if response:
                        try:
                            data = json.loads(response)
                            if "mac" in data:
                                info["mac_address"] = data["mac"]
                            if "version" in data or "firmware" in data:
                                info["firmware_version"] = data.get("version") or data.get("firmware")
                            if "i2c" in data or "sensors" in data:
                                sensors = data.get("i2c", data.get("sensors", []))
                                if isinstance(sensors, list):
                                    info["i2c_sensors"] = sensors
                                elif isinstance(sensors, dict):
                                    info["i2c_sensors"] = list(sensors.keys())
                        except:
                            # Try to extract MAC from raw response
                            if "mac" in response.lower() or ":" in response:
                                parts = response.split()
                                for part in parts:
                                    if ":" in part and len(part.split(":")) == 6:
                                        info["mac_address"] = part.upper()
                                        break
            except:
                continue
    except Exception as e:
        logger.warning(f"Could not query device info: {e}")
    
    return info


@app.post("/devices/connect/{port}")
async def connect_device(port: str, request: Optional[DeviceConnectionRequest] = None):
    try:
        import serial
        side = request.side if request and request.side != "auto" else "side-a"
        baudrate = request.baudrate if request else 115200
        device_id = f"mycobrain-{side}-{port}"
        
        if device_id in devices and devices[device_id].get("status") == "connected":
            return {"status": "already_connected", "device_id": device_id, "port": port, "side": side}
        
        ser = serial.Serial(port, baudrate, timeout=2)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Send initial ping
        ser.write(b'\n')
        time.sleep(0.2)
        
        # Query device information
        device_info = _query_device_info(ser, side)
        
        # Store device
        devices[device_id] = {
            "device_id": device_id,
            "port": port,
            "side": side,
            "baudrate": baudrate,
            "status": "connected",
            "connected_at": datetime.now().isoformat(),
            "serial_handle": ser,
            "mac_address": device_info.get("mac_address"),
            "firmware_version": device_info.get("firmware_version"),
            "i2c_sensors": device_info.get("i2c_sensors", []),
            "device_type": "mycobrain"
        }
        
        # Start background reader thread
        reader_thread = threading.Thread(
            target=_read_device_telemetry,
            args=(device_id, port, baudrate, side),
            daemon=True
        )
        reader_thread.start()
        reader_threads[device_id] = reader_thread
        
        logger.info(f"Connected to {device_id} on {port} (MAC: {device_info.get('mac_address', 'unknown')})")
        return {
            "status": "connected",
            "device_id": device_id,
            "port": port,
            "side": side,
            "mac_address": device_info.get("mac_address"),
            "firmware_version": device_info.get("firmware_version"),
            "i2c_sensors": device_info.get("i2c_sensors", [])
        }
    except Exception as e:
        error_msg = str(e)
        if "Access is denied" in error_msg or "in use" in error_msg.lower():
            raise HTTPException(status_code=403, detail=f"Port {port} is locked. Close other applications using it.")
        raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")

@app.post("/devices/{device_id}/disconnect")
async def disconnect_device(device_id: str):
    if device_id not in devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    device = devices.pop(device_id)
    
    # Stop reader thread
    if device_id in reader_threads:
        # Thread will stop when device is removed from devices dict
        del reader_threads[device_id]
    
    # Close serial connection
    if "serial_handle" in device:
        try:
            device["serial_handle"].close()
        except: pass
    
    # Clear telemetry cache
    if device_id in telemetry_cache:
        del telemetry_cache[device_id]
    
    return {"status": "disconnected", "device_id": device_id}

@app.get("/devices/{device_id}/status")
async def get_device_status(device_id: str):
    if device_id not in devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    d = devices[device_id]
    serial_open = False
    if "serial_handle" in d and hasattr(d["serial_handle"], "is_open"):
        serial_open = d["serial_handle"].is_open
    return {"device_id": device_id, "port": d["port"], "side": d.get("side"), "status": d["status"],
            "serial_open": serial_open, "connected_at": d.get("connected_at")}

@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, request: CommandRequest):
    if device_id not in devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    device = devices[device_id]
    try:
        import serial
        ser = device.get("serial_handle")
        if not ser or not ser.is_open:
            ser = serial.Serial(device["port"], device.get("baudrate", 115200), timeout=2)
            devices[device_id]["serial_handle"] = ser
        
        # Use MDP protocol if available and requested
        if request.use_mdp and MDP_AVAILABLE:
            encoder = MDPEncoder()
            command_type = request.command.get("command_type") or request.command.get("cmd", "unknown")
            parameters = {k: v for k, v in request.command.items() if k not in ["command_type", "cmd"]}
            
            mdp_command = MDPCommand(
                command_id=len(devices[device_id].get("command_history", [])),
                command_type=command_type,
                parameters=parameters
            )
            command_bytes = encoder.encode_command(mdp_command)
            ser.reset_input_buffer()
            ser.write(command_bytes)
            ser.flush()
        else:
            # Fallback to JSON
            ser.reset_input_buffer()
            cmd_str = json.dumps(request.command) + "\n"
            ser.write(cmd_str.encode('utf-8'))
            ser.flush()
        
        time.sleep(0.5)
        
        response = ser.read(ser.in_waiting).decode('utf-8', errors='replace') if ser.in_waiting > 0 else None
        return {"status": "sent", "device_id": device_id, "command": request.command, 
                "response": response.strip() if response else None, "use_mdp": request.use_mdp and MDP_AVAILABLE}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {str(e)}")

@app.get("/devices/{device_id}/telemetry")
async def get_telemetry(device_id: str):
    if device_id not in devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    # Return cached telemetry if available
    if device_id in telemetry_cache:
        return {
            "status": "ok",
            "device_id": device_id,
            **telemetry_cache[device_id]
        }
    
    # Fallback: try to query device directly
    try:
        result = await send_command(device_id, CommandRequest(command={"cmd": "status"}))
        response = result.get("response")
        if response:
            try:
                telemetry_data = json.loads(response)
                return {"status": "ok", "device_id": device_id, "telemetry": telemetry_data, "timestamp": datetime.now().isoformat()}
            except:
                return {"status": "ok", "device_id": device_id, "telemetry": {"raw": response}, "timestamp": datetime.now().isoformat()}
        return {"status": "no_data", "device_id": device_id, "message": "No telemetry received"}
    except Exception as e:
        return {"status": "error", "device_id": device_id, "error": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("MYCOBRAIN_SERVICE_PORT", "8003"))
    logger.info(f"Starting MycoBrain Dual ESP32 service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")




