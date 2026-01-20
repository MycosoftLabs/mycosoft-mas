#!/usr/bin/env python3
"""MycoBrain Service - Full Implementation with Proper Command Mapping"""
import os
import sys
import json
import time
import logging
import threading
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
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

if __name__ == "__main__":
    port = int(os.getenv("MYCOBRAIN_SERVICE_PORT", "8003"))
    logger.info(f"Starting MycoBrain service v2.2 on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
