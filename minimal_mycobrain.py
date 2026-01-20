"""Minimal MycoBrain service (Windows-hosted) used by sandbox via Cloudflare tunnel.

This service is intended to run on the Windows LAN host with the MycoBrain attached
over a COM port. The sandbox VM's `cloudflared` routes `/api/mycobrain*` to this host.
"""
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import serial
import serial.tools.list_ports
import json
import time
import threading
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

app = FastAPI(title="MycoBrain Minimal Service")
api = APIRouter(prefix="/api/mycobrain")

# Runtime config
APP_HOST = os.getenv("MYCOBRAIN_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("MYCOBRAIN_PORT", "8003"))
DEFAULT_BAUD_RATE = int(os.getenv("BAUD_RATE", "115200"))

# Thread pool for port enumeration (can block on Windows)
executor = ThreadPoolExecutor(max_workers=2)

# Cache for port enumeration (to avoid blocking)
_port_cache = {"ports": [], "last_updated": 0}
_port_cache_ttl = 5  # seconds

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store connected devices
devices = {}

@app.get("/")
def root():
    return {"status": "ok", "service": "MycoBrain Minimal"}

@app.get("/health")
@api.get("/health")
def health():
    return {"status": "healthy", "service": "MycoBrain", "version": "2.3.0", "features": ["bsec2", "smell_detection", "aqi"]}

@app.get("/devices")
@api.get("/devices")
def list_devices():
    # Return only serializable data (exclude serial object)
    safe_devices = []
    for port, dev in devices.items():
        # Check if serial connection is still open
        is_connected = False
        try:
            ser = dev.get("serial")
            if ser and ser.is_open:
                is_connected = True
        except:
            pass
        
        safe_devices.append({
            "device_id": dev.get("device_id"),
            "port": dev.get("port"),
            "status": dev.get("status"),
            "protocol": dev.get("protocol"),
            "connected": is_connected,  # Add explicit connected flag
            "is_mycobrain": True,  # Mark as verified MycoBrain device
            "verified": True,
            "device_info": dev.get("device_info", {}),
        })
    return {"devices": safe_devices, "count": len(devices)}

def _enumerate_ports():
    """Enumerate ports in a separate thread to avoid blocking"""
    try:
        ports = serial.tools.list_ports.comports()
        return [{"port": p.device, "description": p.description, "vid": p.vid, "pid": p.pid} for p in ports]
    except Exception as e:
        return []

@app.get("/ports")
@api.get("/ports")
def list_ports():
    global _port_cache
    current_time = time.time()
    
    # Return cached result if fresh enough
    if current_time - _port_cache["last_updated"] < _port_cache_ttl:
        return {"ports": _port_cache["ports"]}
    
    # Try to enumerate ports with timeout
    try:
        future = executor.submit(_enumerate_ports)
        ports = future.result(timeout=2.0)
        _port_cache["ports"] = ports
        _port_cache["last_updated"] = current_time
        return {"ports": ports}
    except FuturesTimeoutError:
        # Return cached data on timeout
        return {"ports": _port_cache["ports"], "cached": True}
    except Exception as e:
        return {"ports": [], "error": str(e)}

def verify_mycobrain_device(ser) -> dict:
    """
    Verify that a serial device is actually a MycoBrain board by sending
    a 'status' command and checking for expected response fields.
    Returns dict with 'is_mycobrain', 'device_info', 'error' fields.
    """
    try:
        ser.reset_input_buffer()
        ser.write(b'status\n')
        time.sleep(1.0)
        
        lines = []
        while ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                lines.append(line)
        
        # Look for JSON response with MycoBrain-specific fields
        for line in lines:
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    # MycoBrain firmware returns 'ok', 'side', or 'mdp_version'
                    is_mycobrain = any([
                        data.get("ok") is True,
                        data.get("side") in ["A", "B", "a", "b"],
                        data.get("mdp_version") is not None,
                        data.get("bme688_count") is not None,
                        data.get("bme1") is not None,
                        data.get("uptime_ms") is not None,
                    ])
                    if is_mycobrain:
                        return {
                            "is_mycobrain": True,
                            "device_info": data,
                            "error": None
                        }
                except json.JSONDecodeError:
                    pass
        
        # Check for known CLI responses (text-based firmware)
        response_text = "\n".join(lines).lower()
        if any([
            "mycobrain" in response_text,
            "bme688" in response_text,
            "mycoboard" in response_text,
            "neopixel" in response_text,
            "buzzer" in response_text,
            "lora" in response_text,
        ]):
            return {
                "is_mycobrain": True,
                "device_info": {"raw_response": "\n".join(lines)},
                "error": None
            }
        
        return {
            "is_mycobrain": False,
            "device_info": None,
            "error": "Device did not respond as MycoBrain board"
        }
    except Exception as e:
        return {
            "is_mycobrain": False,
            "device_info": None,
            "error": str(e)
        }


def _infer_device_id(port: str, device_info: dict | None) -> str:
    """Best-effort stable-ish device id.

    We prefer an explicit device identifier from firmware when present; otherwise we
    fall back to the port-based id (ephemeral). This avoids pretending we have a
    stable id when we do not.
    """
    if isinstance(device_info, dict):
        for key in ("device_id", "board_id", "chip_id", "serial", "mac", "uid"):
            value = device_info.get(key)
            if isinstance(value, str) and value.strip():
                return f"mycobrain-{value.strip()}"
            if isinstance(value, (int, float)) and str(value).strip():
                return f"mycobrain-{str(value).strip()}"
    return f"mycobrain-port-{port}"

@app.post("/devices/connect/{port}")
@api.post("/devices/connect/{port}")
def connect_device(port: str):
    if port in devices:
        return {"status": "already_connected", "device_id": f"mycobrain-{port}"}
    
    try:
        ser = serial.Serial(port, DEFAULT_BAUD_RATE, timeout=2)
        
        # Verify this is actually a MycoBrain device
        verification = verify_mycobrain_device(ser)
        
        if not verification["is_mycobrain"]:
            ser.close()
            return {
                "status": "error",
                "error": f"Not a MycoBrain device: {verification.get('error', 'Unknown device')}",
                "port": port,
                "is_mycobrain": False
            }
        
        device_info = verification.get("device_info", {})
        device_id = _infer_device_id(port=port, device_info=device_info)
        devices[port] = {
            "device_id": device_id,
            "port": port,
            "status": "connected",
            "serial": ser,
            "protocol": "MDP v1",
            "verified": True,
            "connected_at": time.time(),
            "last_seen_at": time.time(),
            "device_info": device_info,
        }
        return {
            "status": "connected",
            "device_id": device_id,
            "port": port,
            "is_mycobrain": True,
            "device_info": device_info
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/devices/disconnect/{port}")
@api.post("/devices/disconnect/{port}")
def disconnect_device(port: str):
    if port in devices:
        try:
            devices[port]["serial"].close()
        except:
            pass
        del devices[port]
        return {"status": "disconnected", "port": port}
    return {"status": "not_connected"}

@app.get("/devices/{device_id}/telemetry")
@api.get("/devices/{device_id}/telemetry")
def get_telemetry(device_id: str):
    port = device_id.replace("mycobrain-port-", "").replace("mycobrain-", "")
    if port not in devices:
        return {"error": "Device not connected"}
    
    try:
        ser = devices[port]["serial"]
        # Clear any pending data
        ser.reset_input_buffer()
        # Send CLI-style status command (not JSON - Chris firmware uses text CLI)
        ser.write(b'status\n')
        # Read multiple lines of response (firmware outputs multi-line)
        time.sleep(0.5)
        lines = []
        while ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                lines.append(line)
        devices[port]["last_seen_at"] = time.time()
        return {"raw": "\n".join(lines), "lines": lines, "status": "ok"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/devices/{device_id}/command")
@api.post("/devices/{device_id}/command")
def send_command(device_id: str, body: dict):
    port = device_id.replace("mycobrain-port-", "").replace("mycobrain-", "")
    if port not in devices:
        return {"error": "Device not connected"}
    
    try:
        ser = devices[port]["serial"]
        # Support both CLI text commands and MDP commands
        
        # Check if it's a raw CLI command (string) or structured command
        cmd_data = body.get("data", body.get("command", ""))
        
        # Handle nested format from website: { command: { cmd: "..." } }
        if isinstance(cmd_data, dict) and "cmd" in cmd_data:
            cmd_data = cmd_data["cmd"]
        
        if isinstance(cmd_data, str):
            # CLI text command (for Chris's firmware)
            ser.reset_input_buffer()
            ser.write((cmd_data + "\n").encode())
            time.sleep(1.5)  # Wait longer for sensor reads
            lines = []
            while ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    lines.append(line)
            devices[port]["last_seen_at"] = time.time()
            return {"response": "\n".join(lines), "lines": lines, "status": "ok"}
        else:
            # JSON/MDP protocol command
            cmd = json.dumps(cmd_data) + "\n"
        ser.write(cmd.encode())
        response = ser.readline().decode('utf-8', errors='ignore').strip()
        devices[port]["last_seen_at"] = time.time()
        return {"response": response, "status": "ok"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/devices/{device_id}/cli")
@api.post("/devices/{device_id}/cli")
def send_cli_command(device_id: str, body: dict):
    """Send a CLI text command to the device (for Chris's firmware)"""
    port = device_id.replace("mycobrain-port-", "").replace("mycobrain-", "")
    if port not in devices:
        return {"error": "Device not connected"}
    
    try:
        ser = devices[port]["serial"]
        
        cmd = body.get("command", "help")
        ser.reset_input_buffer()
        ser.write((cmd + "\n").encode())
        time.sleep(2.0)  # Give more time for sensor initialization and multi-line response
        
        lines = []
        while ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                lines.append(line)
        devices[port]["last_seen_at"] = time.time()
        
        return {"command": cmd, "response": "\n".join(lines), "lines": lines, "status": "ok"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/devices/{device_id}/smell")
@api.get("/devices/{device_id}/smell")
def get_smell_detection(device_id: str):
    """Get smell detection data from BSEC2-enabled device"""
    port = device_id.replace("mycobrain-port-", "").replace("mycobrain-", "")
    if port not in devices:
        return {"error": "Device not connected"}
    
    try:
        ser = devices[port]["serial"]
        ser.reset_input_buffer()
        ser.write(b'smell\n')
        time.sleep(1.5)
        
        lines = []
        while ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                lines.append(line)
        
        # Parse JSON response if available
        for line in lines:
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    devices[port]["last_seen_at"] = time.time()
                    return {"status": "ok", "data": data}
                except:
                    pass
        
        devices[port]["last_seen_at"] = time.time()
        return {"status": "ok", "raw": "\n".join(lines), "lines": lines}
    except Exception as e:
        return {"error": str(e)}

@app.get("/devices/{device_id}/bsec")
@api.get("/devices/{device_id}/bsec")
def get_bsec_status(device_id: str):
    """Get BSEC2 mode status"""
    port = device_id.replace("mycobrain-port-", "").replace("mycobrain-", "")
    if port not in devices:
        return {"error": "Device not connected"}
    
    try:
        ser = devices[port]["serial"]
        ser.reset_input_buffer()
        ser.write(b'bsec\n')
        time.sleep(1.0)
        
        lines = []
        while ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                lines.append(line)
        
        # Parse JSON response if available
        for line in lines:
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    devices[port]["last_seen_at"] = time.time()
                    return {"status": "ok", "data": data}
                except:
                    pass
        
        devices[port]["last_seen_at"] = time.time()
        return {"status": "ok", "raw": "\n".join(lines), "lines": lines}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)


app.include_router(api)
