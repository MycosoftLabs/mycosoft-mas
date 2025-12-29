#!/usr/bin/env python3
"""
MycoBrain Service - Standalone Version

FastAPI service for managing MycoBrain ESP32 devices.
Works without MAS dependencies for basic functionality.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MycoBrain Service",
    description="Service for managing MycoBrain ESP32 devices",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple device storage - keep serial handles open
devices: Dict[str, Dict[str, Any]] = {}
default_port = os.getenv("MYCOBRAIN_PORT", "COM4")
default_baudrate = int(os.getenv("MYCOBRAIN_BAUDRATE", "115200"))


class DeviceConnectionRequest(BaseModel):
    port: str = default_port
    baudrate: int = default_baudrate
    device_id: Optional[str] = None


class CommandRequest(BaseModel):
    command: Dict[str, Any]
    device_id: Optional[str] = None


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "mycobrain",
        "version": "1.0.0",
        "devices_connected": len(devices),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/devices")
async def list_devices() -> Dict[str, Any]:
    """List all connected devices"""
    device_list = []
    for device_id, device in devices.items():
        device_info = {
            "device_id": device_id,
            "port": device.get("port"),
            "status": device.get("status"),
            "connected_at": device.get("connected_at"),
        }
        device_list.append(device_info)
    
    return {
        "devices": device_list,
        "count": len(device_list),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/devices/connect/{port}")
async def connect_device(port: str, request: Optional[DeviceConnectionRequest] = None) -> Dict[str, Any]:
    """Connect to a MycoBrain device on the specified port"""
    try:
        device_id = request.device_id if request and request.device_id else f"mycobrain-{port}"
        baudrate = request.baudrate if request else default_baudrate
        
        # Check if already connected
        if device_id in devices:
            existing = devices[device_id]
            if existing.get("status") == "connected":
                return {
                    "status": "already_connected",
                    "device_id": device_id,
                    "port": port,
                    "timestamp": datetime.now().isoformat()
                }
        
        # Test port accessibility
        try:
            import serial
            import time
            # Open serial port (Windows requires exclusive access)
            ser = serial.Serial(port, baudrate, timeout=2)
            
            # Clear buffers
            try:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            except:
                pass  # May not be available on all platforms
            
            # Test read/write - send newline to wake device
            try:
                ser.write(b'\n')
                time.sleep(0.1)
            except:
                pass  # Continue even if write fails
            
            # Store device info with serial handle
            devices[device_id] = {
                "device_id": device_id,
                "port": port,
                "baudrate": baudrate,
                "status": "connected",
                "connected_at": datetime.now().isoformat(),
                "serial_handle": ser  # Keep handle open for commands
            }
            
            logger.info(f"Connected to device {device_id} on {port}")
            
            return {
                "status": "connected",
                "device_id": device_id,
                "port": port,
                "message": "Device connected successfully",
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            # pyserial not available
            devices[device_id] = {
                "device_id": device_id,
                "port": port,
                "status": "registered",
                "message": "pyserial not installed - device registered but not tested",
                "connected_at": datetime.now().isoformat()
            }
            return {
                "status": "registered",
                "device_id": device_id,
                "port": port,
                "message": "Device registered (install pyserial for full functionality)",
                "timestamp": datetime.now().isoformat()
            }
        except serial.SerialException as e:
            error_msg = str(e)
            if "Access is denied" in error_msg or "in use" in error_msg.lower() or "could not open port" in error_msg.lower():
                raise HTTPException(
                    status_code=403,
                    detail=f"Port {port} is locked or in use. Close serial monitors, Arduino IDE, or other applications using this port."
                )
            raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to connect to {port}: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect to device on {port}: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


@app.post("/devices/{device_id}/disconnect")
async def disconnect_device(device_id: str) -> Dict[str, Any]:
    """Disconnect from a device"""
    if device_id not in devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    device = devices[device_id]
    # Close serial connection if open
    if "serial_handle" in device:
        try:
            ser = device["serial_handle"]
            if hasattr(ser, "is_open") and ser.is_open:
                ser.close()
        except Exception as e:
            logger.warning(f"Error closing serial connection: {e}")
    
    del devices[device_id]
    logger.info(f"Disconnected device {device_id}")
    
    return {
        "status": "disconnected",
        "device_id": device_id,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, request: CommandRequest) -> Dict[str, Any]:
    """Send a command to a device"""
    if device_id not in devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    device = devices[device_id]
    
    try:
        import serial
        import json
        import time
        
        # Get or create serial connection
        if "serial_handle" in device:
            ser = device["serial_handle"]
            # Check if still open
            if not (hasattr(ser, "is_open") and ser.is_open):
                # Reconnect
                try:
                    ser = serial.Serial(device.get("port"), device.get("baudrate", 115200), timeout=2)
                    devices[device_id]["serial_handle"] = ser
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed to reconnect: {str(e)}")
        else:
            # Create new connection
            try:
                ser = serial.Serial(device.get("port"), device.get("baudrate", 115200), timeout=2)
                devices[device_id]["serial_handle"] = ser
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to connect: {str(e)}")
        
        # Clear buffers
        try:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except:
            pass
        
        # Send command as JSON string
        cmd_str = json.dumps(request.command) + "\n"
        ser.write(cmd_str.encode('utf-8'))
        ser.flush()
        
        # Read response
        time.sleep(0.5)  # Wait for response
        response = ""
        if ser.in_waiting > 0:
            response_bytes = ser.read(ser.in_waiting)
            response = response_bytes.decode('utf-8', errors='replace')
        
        return {
            "status": "sent",
            "device_id": device_id,
            "command": request.command,
            "response": response.strip() if response else None,
            "timestamp": datetime.now().isoformat()
        }
    except ImportError:
        return {
            "status": "echo",
            "device_id": device_id,
            "command": request.command,
            "message": "pyserial not available - command echoed",
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send command to {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Command failed: {str(e)}")


@app.get("/devices/{device_id}/status")
async def get_device_status(device_id: str) -> Dict[str, Any]:
    """Get device status"""
    if device_id not in devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    device = devices[device_id]
    status_info = {
        "device_id": device_id,
        "port": device.get("port"),
        "status": device.get("status"),
        "connected_at": device.get("connected_at"),
        "timestamp": datetime.now().isoformat()
    }
    
    # Check if serial connection is still open
    if "serial_handle" in device:
        ser = device["serial_handle"]
        if hasattr(ser, "is_open"):
            status_info["serial_open"] = ser.is_open
    
    return status_info


@app.get("/devices/{device_id}/telemetry")
async def get_telemetry(device_id: str) -> Dict[str, Any]:
    """Get telemetry from device (request sensor data)"""
    if device_id not in devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    # Request sensor data via command
    try:
        # Send get_sensors command and return response
        command_request = CommandRequest(command={"cmd": "get_sensors"})
        result = await send_command(device_id, command_request)
        
        # Parse response if available
        response_text = result.get("response")
        if response_text:
            try:
                import json
                telemetry_data = json.loads(response_text)
                return {
                    "status": "ok",
                    "device_id": device_id,
                    "telemetry": telemetry_data,
                    "timestamp": datetime.now().isoformat()
                }
            except:
                pass
        
        return {
            "status": "no_data",
            "device_id": device_id,
            "message": "No telemetry data received",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get telemetry: {e}")
        return {
            "status": "error",
            "device_id": device_id,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Main entry point"""
    port = int(os.getenv("MYCOBRAIN_SERVICE_PORT", "8003"))
    host = os.getenv("MYCOBRAIN_SERVICE_HOST", "0.0.0.0")
    
    logger.info(f"Starting MycoBrain service on {host}:{port}")
    logger.info(f"Service will be available at: http://localhost:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()




