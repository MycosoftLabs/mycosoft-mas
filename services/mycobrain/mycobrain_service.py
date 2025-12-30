#!/usr/bin/env python3
"""
MycoBrain Service

FastAPI service for managing MycoBrain ESP32 devices via serial communication.
Provides REST API for device control, telemetry, and firmware management.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

MAS_AVAILABLE = False
try:
    # Try to import from MAS
    from mycosoft_mas.agents.mycobrain.device_agent import MycoBrainDeviceAgent, ConnectionType
    from mycosoft_mas.protocols.mdp_v1 import MDPEncoder, MDPDecoder, MDPTelemetry, MDPCommand
    MAS_AVAILABLE = True
    logger.info("MAS modules loaded successfully")
except ImportError as e:
    # Fallback if MAS modules not available - service will work in simple mode
    logger.warning(f"MAS modules not available: {e}. Service will run in simple mode.")
    MDPEncoder = None
    MDPDecoder = None
    MycoBrainDeviceAgent = None

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

# Global device manager
device_agents: Dict[str, Any] = {}
default_port = os.getenv("MYCOBRAIN_PORT", "COM4")
default_baudrate = int(os.getenv("MYCOBRAIN_BAUDRATE", "115200"))


class DeviceConnectionRequest(BaseModel):
    port: str = default_port
    baudrate: int = default_baudrate
    device_id: Optional[str] = None


class CommandRequest(BaseModel):
    command: Dict[str, Any]
    device_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    devices_connected: int
    timestamp: str


@app.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        service="mycobrain",
        version="1.0.0",
        devices_connected=len(device_agents),
        timestamp=datetime.now().isoformat()
    )


@app.get("/devices")
async def list_devices() -> Dict[str, Any]:
    """List all connected devices"""
    devices = []
    for device_id, agent in device_agents.items():
        devices.append({
            "device_id": device_id,
            "port": agent.uart_port if hasattr(agent, 'uart_port') else None,
            "status": agent.device_status if hasattr(agent, 'device_status') else "unknown",
            "firmware_version": agent.firmware_version if hasattr(agent, 'firmware_version') else None,
            "last_telemetry": agent.last_telemetry_time.isoformat() if hasattr(agent, 'last_telemetry_time') and agent.last_telemetry_time else None
        })
    
    return {
        "devices": devices,
        "count": len(devices),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/devices/connect/{port}")
async def connect_device(port: str, request: Optional[DeviceConnectionRequest] = None) -> Dict[str, Any]:
    """Connect to a MycoBrain device on the specified port"""
    try:
        device_id = request.device_id if request else f"mycobrain-{port}"
        baudrate = request.baudrate if request else default_baudrate
        
        if device_id in device_agents:
            return {
                "status": "already_connected",
                "device_id": device_id,
                "port": port
            }
        
        if not MAS_AVAILABLE or MycoBrainDeviceAgent is None:
            # Simple connection without MAS agent
            import serial
            try:
                ser = serial.Serial(port, baudrate, timeout=2)
                ser.close()
                return {
                    "status": "connected",
                    "device_id": device_id,
                    "port": port,
                    "mode": "simple",
                    "message": "Port accessible (MAS agent not available)",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                if "Access is denied" in error_msg or "in use" in error_msg.lower():
                    raise HTTPException(
                        status_code=403,
                        detail=f"Port {port} is locked. Close serial monitors, Arduino IDE, or other applications using this port."
                    )
                raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")
        
        # Create device agent
        config = {
            "device_id": device_id,
            "connection_type": "uart",
            "uart_port": port,
            "uart_baudrate": baudrate,
            "command_timeout": 5.0,
            "max_retries": 3
        }
        
        agent = MycoBrainDeviceAgent(
            agent_id=f"mycobrain-agent-{device_id}",
            name=f"MycoBrain Device Agent - {device_id}",
            config=config
        )
        
        # Start agent
        await agent.start()
        
        # Wait a moment for connection
        await asyncio.sleep(2)
        
        # Store agent
        device_agents[device_id] = agent
        
        # Get diagnostics
        diagnostics = {
            "device_id": device_id,
            "port": port,
            "status": agent.device_status,
            "firmware_version": agent.firmware_version,
            "connection_time": datetime.now().isoformat()
        }
        
        logger.info(f"Connected to MycoBrain device {device_id} on {port}")
        
        return {
            "status": "connected",
            "device_id": device_id,
            "port": port,
            "diagnostics": diagnostics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        error_msg = str(e)
        if "Access is denied" in error_msg or "in use" in error_msg.lower():
            raise HTTPException(
                status_code=403,
                detail=f"Port {port} is locked. Close serial monitors, Arduino IDE, or other applications using this port."
            )
        logger.error(f"Failed to connect to device on {port}: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")


@app.post("/devices/{device_id}/disconnect")
async def disconnect_device(device_id: str) -> Dict[str, Any]:
    """Disconnect from a device"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    if hasattr(agent, 'stop'):
        await agent.stop()
    del device_agents[device_id]
    
    return {
        "status": "disconnected",
        "device_id": device_id,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, request: CommandRequest) -> Dict[str, Any]:
    """Send a command to a device"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    
    try:
        if MAS_AVAILABLE and hasattr(agent, 'send_command'):
            # Create command
            command = MDPCommand(**request.command) if MDPCommand else request.command
            # Send command
            result = await agent.send_command(command)
        else:
            # Simple mode - just echo the command
            result = {"echo": request.command}
        
        return {
            "status": "sent",
            "device_id": device_id,
            "command": request.command,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to send command to {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Command failed: {str(e)}")


@app.get("/devices/{device_id}/telemetry")
async def get_telemetry(device_id: str) -> Dict[str, Any]:
    """Get latest telemetry from a device"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    
    if not hasattr(agent, 'last_telemetry') or not agent.last_telemetry:
        return {
            "status": "no_data",
            "device_id": device_id,
            "message": "No telemetry received yet"
        }
    
    telemetry = agent.last_telemetry
    
    return {
        "status": "ok",
        "device_id": device_id,
        "telemetry": {
            "temperature": telemetry.temperature if hasattr(telemetry, 'temperature') else None,
            "humidity": telemetry.humidity if hasattr(telemetry, 'humidity') else None,
            "ai1_voltage": telemetry.ai1_voltage if hasattr(telemetry, 'ai1_voltage') else None,
            "timestamp": agent.last_telemetry_time.isoformat() if hasattr(agent, 'last_telemetry_time') and agent.last_telemetry_time else None
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/devices/{device_id}/status")
async def get_device_status(device_id: str) -> Dict[str, Any]:
    """Get device status and diagnostics"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    
    return {
        "device_id": device_id,
        "status": agent.device_status if hasattr(agent, 'device_status') else "unknown",
        "firmware_version": agent.firmware_version if hasattr(agent, 'firmware_version') else None,
        "uptime_seconds": agent.uptime_seconds if hasattr(agent, 'uptime_seconds') else None,
        "metrics": agent.metrics if hasattr(agent, 'metrics') else {},
        "last_telemetry_time": agent.last_telemetry_time.isoformat() if hasattr(agent, 'last_telemetry_time') and agent.last_telemetry_time else None,
        "timestamp": datetime.now().isoformat()
    }


def main():
    """Main entry point"""
    port = int(os.getenv("MYCOBRAIN_SERVICE_PORT", "8003"))
    host = os.getenv("MYCOBRAIN_SERVICE_HOST", "0.0.0.0")
    
    logger.info(f"Starting MycoBrain service on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()







#!/usr/bin/env python3
"""
MycoBrain Service

FastAPI service for managing MycoBrain ESP32 devices via serial communication.
Provides REST API for device control, telemetry, and firmware management.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

MAS_AVAILABLE = False
try:
    # Try to import from MAS
    from mycosoft_mas.agents.mycobrain.device_agent import MycoBrainDeviceAgent, ConnectionType
    from mycosoft_mas.protocols.mdp_v1 import MDPEncoder, MDPDecoder, MDPTelemetry, MDPCommand
    MAS_AVAILABLE = True
    logger.info("MAS modules loaded successfully")
except ImportError as e:
    # Fallback if MAS modules not available - service will work in simple mode
    logger.warning(f"MAS modules not available: {e}. Service will run in simple mode.")
    MDPEncoder = None
    MDPDecoder = None
    MycoBrainDeviceAgent = None

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

# Global device manager
device_agents: Dict[str, Any] = {}
default_port = os.getenv("MYCOBRAIN_PORT", "COM4")
default_baudrate = int(os.getenv("MYCOBRAIN_BAUDRATE", "115200"))


class DeviceConnectionRequest(BaseModel):
    port: str = default_port
    baudrate: int = default_baudrate
    device_id: Optional[str] = None


class CommandRequest(BaseModel):
    command: Dict[str, Any]
    device_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    devices_connected: int
    timestamp: str


@app.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        service="mycobrain",
        version="1.0.0",
        devices_connected=len(device_agents),
        timestamp=datetime.now().isoformat()
    )


@app.get("/devices")
async def list_devices() -> Dict[str, Any]:
    """List all connected devices"""
    devices = []
    for device_id, agent in device_agents.items():
        devices.append({
            "device_id": device_id,
            "port": agent.uart_port if hasattr(agent, 'uart_port') else None,
            "status": agent.device_status if hasattr(agent, 'device_status') else "unknown",
            "firmware_version": agent.firmware_version if hasattr(agent, 'firmware_version') else None,
            "last_telemetry": agent.last_telemetry_time.isoformat() if hasattr(agent, 'last_telemetry_time') and agent.last_telemetry_time else None
        })
    
    return {
        "devices": devices,
        "count": len(devices),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/devices/connect/{port}")
async def connect_device(port: str, request: Optional[DeviceConnectionRequest] = None) -> Dict[str, Any]:
    """Connect to a MycoBrain device on the specified port"""
    try:
        device_id = request.device_id if request else f"mycobrain-{port}"
        baudrate = request.baudrate if request else default_baudrate
        
        if device_id in device_agents:
            return {
                "status": "already_connected",
                "device_id": device_id,
                "port": port
            }
        
        if not MAS_AVAILABLE or MycoBrainDeviceAgent is None:
            # Simple connection without MAS agent
            import serial
            try:
                ser = serial.Serial(port, baudrate, timeout=2)
                ser.close()
                return {
                    "status": "connected",
                    "device_id": device_id,
                    "port": port,
                    "mode": "simple",
                    "message": "Port accessible (MAS agent not available)",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                if "Access is denied" in error_msg or "in use" in error_msg.lower():
                    raise HTTPException(
                        status_code=403,
                        detail=f"Port {port} is locked. Close serial monitors, Arduino IDE, or other applications using this port."
                    )
                raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")
        
        # Create device agent
        config = {
            "device_id": device_id,
            "connection_type": "uart",
            "uart_port": port,
            "uart_baudrate": baudrate,
            "command_timeout": 5.0,
            "max_retries": 3
        }
        
        agent = MycoBrainDeviceAgent(
            agent_id=f"mycobrain-agent-{device_id}",
            name=f"MycoBrain Device Agent - {device_id}",
            config=config
        )
        
        # Start agent
        await agent.start()
        
        # Wait a moment for connection
        await asyncio.sleep(2)
        
        # Store agent
        device_agents[device_id] = agent
        
        # Get diagnostics
        diagnostics = {
            "device_id": device_id,
            "port": port,
            "status": agent.device_status,
            "firmware_version": agent.firmware_version,
            "connection_time": datetime.now().isoformat()
        }
        
        logger.info(f"Connected to MycoBrain device {device_id} on {port}")
        
        return {
            "status": "connected",
            "device_id": device_id,
            "port": port,
            "diagnostics": diagnostics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        error_msg = str(e)
        if "Access is denied" in error_msg or "in use" in error_msg.lower():
            raise HTTPException(
                status_code=403,
                detail=f"Port {port} is locked. Close serial monitors, Arduino IDE, or other applications using this port."
            )
        logger.error(f"Failed to connect to device on {port}: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")


@app.post("/devices/{device_id}/disconnect")
async def disconnect_device(device_id: str) -> Dict[str, Any]:
    """Disconnect from a device"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    if hasattr(agent, 'stop'):
        await agent.stop()
    del device_agents[device_id]
    
    return {
        "status": "disconnected",
        "device_id": device_id,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, request: CommandRequest) -> Dict[str, Any]:
    """Send a command to a device"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    
    try:
        if MAS_AVAILABLE and hasattr(agent, 'send_command'):
            # Create command
            command = MDPCommand(**request.command) if MDPCommand else request.command
            # Send command
            result = await agent.send_command(command)
        else:
            # Simple mode - just echo the command
            result = {"echo": request.command}
        
        return {
            "status": "sent",
            "device_id": device_id,
            "command": request.command,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to send command to {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Command failed: {str(e)}")


@app.get("/devices/{device_id}/telemetry")
async def get_telemetry(device_id: str) -> Dict[str, Any]:
    """Get latest telemetry from a device"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    
    if not hasattr(agent, 'last_telemetry') or not agent.last_telemetry:
        return {
            "status": "no_data",
            "device_id": device_id,
            "message": "No telemetry received yet"
        }
    
    telemetry = agent.last_telemetry
    
    return {
        "status": "ok",
        "device_id": device_id,
        "telemetry": {
            "temperature": telemetry.temperature if hasattr(telemetry, 'temperature') else None,
            "humidity": telemetry.humidity if hasattr(telemetry, 'humidity') else None,
            "ai1_voltage": telemetry.ai1_voltage if hasattr(telemetry, 'ai1_voltage') else None,
            "timestamp": agent.last_telemetry_time.isoformat() if hasattr(agent, 'last_telemetry_time') and agent.last_telemetry_time else None
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/devices/{device_id}/status")
async def get_device_status(device_id: str) -> Dict[str, Any]:
    """Get device status and diagnostics"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    
    return {
        "device_id": device_id,
        "status": agent.device_status if hasattr(agent, 'device_status') else "unknown",
        "firmware_version": agent.firmware_version if hasattr(agent, 'firmware_version') else None,
        "uptime_seconds": agent.uptime_seconds if hasattr(agent, 'uptime_seconds') else None,
        "metrics": agent.metrics if hasattr(agent, 'metrics') else {},
        "last_telemetry_time": agent.last_telemetry_time.isoformat() if hasattr(agent, 'last_telemetry_time') and agent.last_telemetry_time else None,
        "timestamp": datetime.now().isoformat()
    }


def main():
    """Main entry point"""
    port = int(os.getenv("MYCOBRAIN_SERVICE_PORT", "8003"))
    host = os.getenv("MYCOBRAIN_SERVICE_HOST", "0.0.0.0")
    
    logger.info(f"Starting MycoBrain service on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()








#!/usr/bin/env python3
"""
MycoBrain Service

FastAPI service for managing MycoBrain ESP32 devices via serial communication.
Provides REST API for device control, telemetry, and firmware management.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

MAS_AVAILABLE = False
try:
    # Try to import from MAS
    from mycosoft_mas.agents.mycobrain.device_agent import MycoBrainDeviceAgent, ConnectionType
    from mycosoft_mas.protocols.mdp_v1 import MDPEncoder, MDPDecoder, MDPTelemetry, MDPCommand
    MAS_AVAILABLE = True
    logger.info("MAS modules loaded successfully")
except ImportError as e:
    # Fallback if MAS modules not available - service will work in simple mode
    logger.warning(f"MAS modules not available: {e}. Service will run in simple mode.")
    MDPEncoder = None
    MDPDecoder = None
    MycoBrainDeviceAgent = None

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

# Global device manager
device_agents: Dict[str, Any] = {}
default_port = os.getenv("MYCOBRAIN_PORT", "COM4")
default_baudrate = int(os.getenv("MYCOBRAIN_BAUDRATE", "115200"))


class DeviceConnectionRequest(BaseModel):
    port: str = default_port
    baudrate: int = default_baudrate
    device_id: Optional[str] = None


class CommandRequest(BaseModel):
    command: Dict[str, Any]
    device_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    devices_connected: int
    timestamp: str


@app.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        service="mycobrain",
        version="1.0.0",
        devices_connected=len(device_agents),
        timestamp=datetime.now().isoformat()
    )


@app.get("/devices")
async def list_devices() -> Dict[str, Any]:
    """List all connected devices"""
    devices = []
    for device_id, agent in device_agents.items():
        devices.append({
            "device_id": device_id,
            "port": agent.uart_port if hasattr(agent, 'uart_port') else None,
            "status": agent.device_status if hasattr(agent, 'device_status') else "unknown",
            "firmware_version": agent.firmware_version if hasattr(agent, 'firmware_version') else None,
            "last_telemetry": agent.last_telemetry_time.isoformat() if hasattr(agent, 'last_telemetry_time') and agent.last_telemetry_time else None
        })
    
    return {
        "devices": devices,
        "count": len(devices),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/devices/connect/{port}")
async def connect_device(port: str, request: Optional[DeviceConnectionRequest] = None) -> Dict[str, Any]:
    """Connect to a MycoBrain device on the specified port"""
    try:
        device_id = request.device_id if request else f"mycobrain-{port}"
        baudrate = request.baudrate if request else default_baudrate
        
        if device_id in device_agents:
            return {
                "status": "already_connected",
                "device_id": device_id,
                "port": port
            }
        
        if not MAS_AVAILABLE or MycoBrainDeviceAgent is None:
            # Simple connection without MAS agent
            import serial
            try:
                ser = serial.Serial(port, baudrate, timeout=2)
                ser.close()
                return {
                    "status": "connected",
                    "device_id": device_id,
                    "port": port,
                    "mode": "simple",
                    "message": "Port accessible (MAS agent not available)",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                if "Access is denied" in error_msg or "in use" in error_msg.lower():
                    raise HTTPException(
                        status_code=403,
                        detail=f"Port {port} is locked. Close serial monitors, Arduino IDE, or other applications using this port."
                    )
                raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")
        
        # Create device agent
        config = {
            "device_id": device_id,
            "connection_type": "uart",
            "uart_port": port,
            "uart_baudrate": baudrate,
            "command_timeout": 5.0,
            "max_retries": 3
        }
        
        agent = MycoBrainDeviceAgent(
            agent_id=f"mycobrain-agent-{device_id}",
            name=f"MycoBrain Device Agent - {device_id}",
            config=config
        )
        
        # Start agent
        await agent.start()
        
        # Wait a moment for connection
        await asyncio.sleep(2)
        
        # Store agent
        device_agents[device_id] = agent
        
        # Get diagnostics
        diagnostics = {
            "device_id": device_id,
            "port": port,
            "status": agent.device_status,
            "firmware_version": agent.firmware_version,
            "connection_time": datetime.now().isoformat()
        }
        
        logger.info(f"Connected to MycoBrain device {device_id} on {port}")
        
        return {
            "status": "connected",
            "device_id": device_id,
            "port": port,
            "diagnostics": diagnostics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        error_msg = str(e)
        if "Access is denied" in error_msg or "in use" in error_msg.lower():
            raise HTTPException(
                status_code=403,
                detail=f"Port {port} is locked. Close serial monitors, Arduino IDE, or other applications using this port."
            )
        logger.error(f"Failed to connect to device on {port}: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")


@app.post("/devices/{device_id}/disconnect")
async def disconnect_device(device_id: str) -> Dict[str, Any]:
    """Disconnect from a device"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    if hasattr(agent, 'stop'):
        await agent.stop()
    del device_agents[device_id]
    
    return {
        "status": "disconnected",
        "device_id": device_id,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, request: CommandRequest) -> Dict[str, Any]:
    """Send a command to a device"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    
    try:
        if MAS_AVAILABLE and hasattr(agent, 'send_command'):
            # Create command
            command = MDPCommand(**request.command) if MDPCommand else request.command
            # Send command
            result = await agent.send_command(command)
        else:
            # Simple mode - just echo the command
            result = {"echo": request.command}
        
        return {
            "status": "sent",
            "device_id": device_id,
            "command": request.command,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to send command to {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Command failed: {str(e)}")


@app.get("/devices/{device_id}/telemetry")
async def get_telemetry(device_id: str) -> Dict[str, Any]:
    """Get latest telemetry from a device"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    
    if not hasattr(agent, 'last_telemetry') or not agent.last_telemetry:
        return {
            "status": "no_data",
            "device_id": device_id,
            "message": "No telemetry received yet"
        }
    
    telemetry = agent.last_telemetry
    
    return {
        "status": "ok",
        "device_id": device_id,
        "telemetry": {
            "temperature": telemetry.temperature if hasattr(telemetry, 'temperature') else None,
            "humidity": telemetry.humidity if hasattr(telemetry, 'humidity') else None,
            "ai1_voltage": telemetry.ai1_voltage if hasattr(telemetry, 'ai1_voltage') else None,
            "timestamp": agent.last_telemetry_time.isoformat() if hasattr(agent, 'last_telemetry_time') and agent.last_telemetry_time else None
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/devices/{device_id}/status")
async def get_device_status(device_id: str) -> Dict[str, Any]:
    """Get device status and diagnostics"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    
    return {
        "device_id": device_id,
        "status": agent.device_status if hasattr(agent, 'device_status') else "unknown",
        "firmware_version": agent.firmware_version if hasattr(agent, 'firmware_version') else None,
        "uptime_seconds": agent.uptime_seconds if hasattr(agent, 'uptime_seconds') else None,
        "metrics": agent.metrics if hasattr(agent, 'metrics') else {},
        "last_telemetry_time": agent.last_telemetry_time.isoformat() if hasattr(agent, 'last_telemetry_time') and agent.last_telemetry_time else None,
        "timestamp": datetime.now().isoformat()
    }


def main():
    """Main entry point"""
    port = int(os.getenv("MYCOBRAIN_SERVICE_PORT", "8003"))
    host = os.getenv("MYCOBRAIN_SERVICE_HOST", "0.0.0.0")
    
    logger.info(f"Starting MycoBrain service on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()







#!/usr/bin/env python3
"""
MycoBrain Service

FastAPI service for managing MycoBrain ESP32 devices via serial communication.
Provides REST API for device control, telemetry, and firmware management.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

MAS_AVAILABLE = False
try:
    # Try to import from MAS
    from mycosoft_mas.agents.mycobrain.device_agent import MycoBrainDeviceAgent, ConnectionType
    from mycosoft_mas.protocols.mdp_v1 import MDPEncoder, MDPDecoder, MDPTelemetry, MDPCommand
    MAS_AVAILABLE = True
    logger.info("MAS modules loaded successfully")
except ImportError as e:
    # Fallback if MAS modules not available - service will work in simple mode
    logger.warning(f"MAS modules not available: {e}. Service will run in simple mode.")
    MDPEncoder = None
    MDPDecoder = None
    MycoBrainDeviceAgent = None

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

# Global device manager
device_agents: Dict[str, Any] = {}
default_port = os.getenv("MYCOBRAIN_PORT", "COM4")
default_baudrate = int(os.getenv("MYCOBRAIN_BAUDRATE", "115200"))


class DeviceConnectionRequest(BaseModel):
    port: str = default_port
    baudrate: int = default_baudrate
    device_id: Optional[str] = None


class CommandRequest(BaseModel):
    command: Dict[str, Any]
    device_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    devices_connected: int
    timestamp: str


@app.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        service="mycobrain",
        version="1.0.0",
        devices_connected=len(device_agents),
        timestamp=datetime.now().isoformat()
    )


@app.get("/devices")
async def list_devices() -> Dict[str, Any]:
    """List all connected devices"""
    devices = []
    for device_id, agent in device_agents.items():
        devices.append({
            "device_id": device_id,
            "port": agent.uart_port if hasattr(agent, 'uart_port') else None,
            "status": agent.device_status if hasattr(agent, 'device_status') else "unknown",
            "firmware_version": agent.firmware_version if hasattr(agent, 'firmware_version') else None,
            "last_telemetry": agent.last_telemetry_time.isoformat() if hasattr(agent, 'last_telemetry_time') and agent.last_telemetry_time else None
        })
    
    return {
        "devices": devices,
        "count": len(devices),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/devices/connect/{port}")
async def connect_device(port: str, request: Optional[DeviceConnectionRequest] = None) -> Dict[str, Any]:
    """Connect to a MycoBrain device on the specified port"""
    try:
        device_id = request.device_id if request else f"mycobrain-{port}"
        baudrate = request.baudrate if request else default_baudrate
        
        if device_id in device_agents:
            return {
                "status": "already_connected",
                "device_id": device_id,
                "port": port
            }
        
        if not MAS_AVAILABLE or MycoBrainDeviceAgent is None:
            # Simple connection without MAS agent
            import serial
            try:
                ser = serial.Serial(port, baudrate, timeout=2)
                ser.close()
                return {
                    "status": "connected",
                    "device_id": device_id,
                    "port": port,
                    "mode": "simple",
                    "message": "Port accessible (MAS agent not available)",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                if "Access is denied" in error_msg or "in use" in error_msg.lower():
                    raise HTTPException(
                        status_code=403,
                        detail=f"Port {port} is locked. Close serial monitors, Arduino IDE, or other applications using this port."
                    )
                raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")
        
        # Create device agent
        config = {
            "device_id": device_id,
            "connection_type": "uart",
            "uart_port": port,
            "uart_baudrate": baudrate,
            "command_timeout": 5.0,
            "max_retries": 3
        }
        
        agent = MycoBrainDeviceAgent(
            agent_id=f"mycobrain-agent-{device_id}",
            name=f"MycoBrain Device Agent - {device_id}",
            config=config
        )
        
        # Start agent
        await agent.start()
        
        # Wait a moment for connection
        await asyncio.sleep(2)
        
        # Store agent
        device_agents[device_id] = agent
        
        # Get diagnostics
        diagnostics = {
            "device_id": device_id,
            "port": port,
            "status": agent.device_status,
            "firmware_version": agent.firmware_version,
            "connection_time": datetime.now().isoformat()
        }
        
        logger.info(f"Connected to MycoBrain device {device_id} on {port}")
        
        return {
            "status": "connected",
            "device_id": device_id,
            "port": port,
            "diagnostics": diagnostics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        error_msg = str(e)
        if "Access is denied" in error_msg or "in use" in error_msg.lower():
            raise HTTPException(
                status_code=403,
                detail=f"Port {port} is locked. Close serial monitors, Arduino IDE, or other applications using this port."
            )
        logger.error(f"Failed to connect to device on {port}: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {error_msg}")


@app.post("/devices/{device_id}/disconnect")
async def disconnect_device(device_id: str) -> Dict[str, Any]:
    """Disconnect from a device"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    if hasattr(agent, 'stop'):
        await agent.stop()
    del device_agents[device_id]
    
    return {
        "status": "disconnected",
        "device_id": device_id,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, request: CommandRequest) -> Dict[str, Any]:
    """Send a command to a device"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    
    try:
        if MAS_AVAILABLE and hasattr(agent, 'send_command'):
            # Create command
            command = MDPCommand(**request.command) if MDPCommand else request.command
            # Send command
            result = await agent.send_command(command)
        else:
            # Simple mode - just echo the command
            result = {"echo": request.command}
        
        return {
            "status": "sent",
            "device_id": device_id,
            "command": request.command,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to send command to {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Command failed: {str(e)}")


@app.get("/devices/{device_id}/telemetry")
async def get_telemetry(device_id: str) -> Dict[str, Any]:
    """Get latest telemetry from a device"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    
    if not hasattr(agent, 'last_telemetry') or not agent.last_telemetry:
        return {
            "status": "no_data",
            "device_id": device_id,
            "message": "No telemetry received yet"
        }
    
    telemetry = agent.last_telemetry
    
    return {
        "status": "ok",
        "device_id": device_id,
        "telemetry": {
            "temperature": telemetry.temperature if hasattr(telemetry, 'temperature') else None,
            "humidity": telemetry.humidity if hasattr(telemetry, 'humidity') else None,
            "ai1_voltage": telemetry.ai1_voltage if hasattr(telemetry, 'ai1_voltage') else None,
            "timestamp": agent.last_telemetry_time.isoformat() if hasattr(agent, 'last_telemetry_time') and agent.last_telemetry_time else None
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/devices/{device_id}/status")
async def get_device_status(device_id: str) -> Dict[str, Any]:
    """Get device status and diagnostics"""
    if device_id not in device_agents:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    agent = device_agents[device_id]
    
    return {
        "device_id": device_id,
        "status": agent.device_status if hasattr(agent, 'device_status') else "unknown",
        "firmware_version": agent.firmware_version if hasattr(agent, 'firmware_version') else None,
        "uptime_seconds": agent.uptime_seconds if hasattr(agent, 'uptime_seconds') else None,
        "metrics": agent.metrics if hasattr(agent, 'metrics') else {},
        "last_telemetry_time": agent.last_telemetry_time.isoformat() if hasattr(agent, 'last_telemetry_time') and agent.last_telemetry_time else None,
        "timestamp": datetime.now().isoformat()
    }


def main():
    """Main entry point"""
    port = int(os.getenv("MYCOBRAIN_SERVICE_PORT", "8003"))
    host = os.getenv("MYCOBRAIN_SERVICE_HOST", "0.0.0.0")
    
    logger.info(f"Starting MycoBrain service on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()










