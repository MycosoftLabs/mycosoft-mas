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
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated

# Import authentication (optional - graceful fallback if not available)
try:
    from auth import verify_api_key
    AUTH_ENABLED = True
except ImportError:
    AUTH_ENABLED = False
    def verify_api_key():
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
        except:
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

app = FastAPI(title="MycoBrain Service", version="2.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Global state
devices: Dict[str, Dict] = {}
serial_connections: Dict[str, Any] = {}
telemetry_cache: Dict[str, Dict] = {}

def send_serial_command(device_id: str, command: str, timeout: float = 2.0) -> str:
    """Send a command to the device and return response"""
    if device_id not in serial_connections:
        raise ValueError(f"Device {device_id} not connected")
    
    ser = serial_connections[device_id]
    if not ser.is_open:
        raise ValueError("Serial connection closed")
    
    ser.reset_input_buffer()
    cmd_bytes = (command + "\r\n").encode('utf-8')
    logger.info(f"Sending to {device_id}: {command}")
    ser.write(cmd_bytes)
    
    time.sleep(0.5)
    response = ""
    end_time = time.time() + timeout
    while time.time() < end_time:
        if ser.in_waiting > 0:
            response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            time.sleep(0.1)
        else:
            if response:
                break
            time.sleep(0.1)
    
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
            except:
                devices[device_id]["status"] = "error"
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
            })
        return {"ports": ports, "count": len(ports), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"ports": [], "count": 0, "error": str(e), "timestamp": datetime.now().isoformat()}

@app.post("/devices/connect/{port:path}")
async def connect_device(port: str, baudrate: int = 115200, api_key: str = Depends(verify_api_key)):
    import serial
    
    port = port.replace('-', '/') if port.startswith('COM-') else port
    device_id = f"mycobrain-{port.replace('/', '-').replace(':', '-')}"
    
    logger.info(f"Connecting to {port}")
    
    if device_id in serial_connections:
        ser = serial_connections[device_id]
        if ser.is_open:
            return {"status": "already_connected", "device_id": device_id, "port": port}
        del serial_connections[device_id]
    
    try:
        ser = serial.Serial(port, baudrate, timeout=2)
        time.sleep(1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        serial_connections[device_id] = ser
        
        device_info = {"firmware": "unknown", "board": "MycoBrain ESP32-S3"}
        try:
            response = send_serial_command(device_id, "status", timeout=1.0)
            if "ESP32-S3" in response:
                device_info["board"] = "ESP32-S3"
            if "Arduino-ESP32 core:" in response:
                for line in response.split('\n'):
                    if "Arduino-ESP32 core:" in line:
                        device_info["firmware"] = line.split(':')[1].strip()
            device_info["raw_status"] = response[:500]
        except:
            pass
        
        devices[device_id] = {
            "device_id": device_id,
            "port": port,
            "status": "connected",
            "connected_at": datetime.now().isoformat(),
            "info": device_info,
            "protocol": "MDP v1"
        }
        
        return {"status": "connected", "device_id": device_id, "port": port, "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Connection error: {error_msg}")
        if "Access is denied" in error_msg or "PermissionError" in error_msg:
            raise HTTPException(status_code=403, detail=f"Port {port} is locked or in use.")
        raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")

@app.post("/devices/{device_id}/disconnect")
async def disconnect_device(device_id: str, api_key: str = Depends(verify_api_key)):
    if device_id not in devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    try:
        if device_id in serial_connections:
            serial_connections[device_id].close()
            del serial_connections[device_id]
        del devices[device_id]
        return {"status": "disconnected", "device_id": device_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, command: str = Query(None), body: dict = Body(default=None), api_key: str = Depends(verify_api_key)):
    """Send a command to the device - supports both query param and JSON body"""
    if device_id not in devices:
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
    
    try:
        response = send_serial_command(device_id, cmd)
        return {
            "status": "ok",
            "device_id": device_id,
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
        "ping": lambda p: "status",
        "info": lambda p: "status",
        
        # LED commands
        "neopixel-set": lambda p: f"led rgb {p.get('r', 0)} {p.get('g', 255)} {p.get('b', 0)}",
        "neopixel-rainbow": lambda p: "led mode state",
        "neopixel-off": lambda p: "led rgb 0 0 0",
        "led-set": lambda p: f"led rgb {p.get('r', 0)} {p.get('g', 255)} {p.get('b', 0)}",
        "set_led": lambda p: f"led rgb {p.get('r', 0)} {p.get('g', 0)} {p.get('b', 0)}",
        
        # Buzzer/sound commands
        "buzzer-beep": lambda p: "coin",
        "buzzer-melody": lambda p: "morgio",
        "buzzer-tone": lambda p: "coin",
        "beep": lambda p: "coin",
        "play_sound": lambda p: p.get('sound', 'coin'),
        
        # Sensor commands
        "read-bme1": lambda p: "probe amb",
        "read-bme2": lambda p: "probe env",
        "scan-i2c": lambda p: "scan",
        "i2c-scan": lambda p: "scan",
        "get-sensors": lambda p: "status",
        
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
    if device_id not in serial_connections:
        raise HTTPException(status_code=400, detail=f"Device {device_id} not connected")
    
    try:
        response = send_serial_command(device_id, "status", timeout=2.0)
        
        telemetry = {"raw": response}
        
        for line in response.split('\n'):
            if "AMB addr=0x77" in line:
                telemetry["bme1"] = parse_sensor_line(line, "amb")
            elif "ENV addr=0x76" in line:
                telemetry["bme2"] = parse_sensor_line(line, "env")
        
        telemetry_cache[device_id] = telemetry
        
        return {
            "status": "ok",
            "device_id": device_id,
            "telemetry": telemetry,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    except:
        pass
    return data

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
        except:
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
            except:
                pass
    except:
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
        
        # Build heartbeat payload (serial ingestion; same format for future LoRa/BT/WiFi gateways)
        payload = {
            "device_id": device_id,
            "device_name": DEVICE_NAME,
            "device_role": device_role,
            "device_display_name": device_display_name,
            "host": host,
            "port": port,
            "firmware_version": device.get("info", {}).get("firmware", "unknown"),
            "board_type": device.get("info", {}).get("board", "ESP32-S3"),
            "sensors": ["bme688_a", "bme688_b"],
            "capabilities": ["led", "buzzer", "i2c"],
            "location": DEVICE_LOCATION,
            "connection_type": connection_type,
            "ingestion_source": "serial",
            "extra": {
                "protocol": device.get("protocol", "MDP v1"),
                "port_name": device.get("port", ""),
                "service_version": "2.2.0",
            }
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{MAS_REGISTRY_URL}/api/devices/register",
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
                    "device_name": f"{DEVICE_NAME} (No Devices)",
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
                    "extra": {"service_version": "2.2.0", "status": "waiting_for_device"}
                }
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        await client.post(f"{MAS_REGISTRY_URL}/api/devices/register", json=service_payload)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")
        
        await asyncio.sleep(HEARTBEAT_INTERVAL)


_heartbeat_task: Optional[asyncio.Task] = None

@app.on_event("startup")
async def startup_event():
    """Start the heartbeat loop on service startup."""
    global _heartbeat_task
    
    if HEARTBEAT_ENABLED:
        _heartbeat_task = asyncio.create_task(heartbeat_loop())
        logger.info("Heartbeat system enabled")
    else:
        logger.info("Heartbeat system disabled (set MYCOBRAIN_HEARTBEAT_ENABLED=true to enable)")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the heartbeat loop on service shutdown."""
    global _heartbeat_task
    
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
