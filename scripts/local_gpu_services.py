#!/usr/bin/env python3
"""
MYCOSOFT Local GPU Services - February 5, 2026
Unified startup for all GPU-accelerated services on local Windows machine with RTX 5090.

Services:
- Earth2Studio API (port 8220) - Weather model inference
- PersonaPlex/Moshi (port 8998) - Voice AI
- PersonaPlex Bridge (port 8999) - Voice routing
- Unified GPU Gateway (port 8300) - Single entry point for all GPU services

All services are exposed to the dev server at localhost:3010
"""

import asyncio
import os
import socket
import subprocess
import sys
import time
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# =============================================================================
# Configuration
# =============================================================================

MAS_DIR = Path(r"c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas")
EARTH2_VENV = Path(r"C:\Users\admin2\.earth2studio-venv")

# Service Ports
PORTS = {
    "moshi": 8998,
    "bridge": 8999,
    "earth2": 8220,
    "gateway": 8300,
}

# Script paths
SCRIPTS = {
    "moshi": MAS_DIR / "start_personaplex.py",
    "bridge": MAS_DIR / "services" / "personaplex-local" / "personaplex_bridge_nvidia.py",
    "earth2": MAS_DIR / "scripts" / "earth2_api_server.py",
}

# Process handles
processes: Dict[str, subprocess.Popen] = {}


# =============================================================================
# Utilities
# =============================================================================

def log(msg: str, level: str = "INFO"):
    """Log with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "[*]", "OK": "[+]", "FAIL": "[-]", "WAIT": "[~]"}.get(level, "[?]")
    print(f"{ts} {prefix} {msg}")


def check_port(port: int, host: str = "localhost") -> bool:
    """Check if port is open."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            return s.connect_ex((host, port)) == 0
    except:
        return False


def wait_for_port(port: int, host: str = "localhost", timeout: int = 120) -> bool:
    """Wait for port to become available."""
    start = time.time()
    while time.time() - start < timeout:
        if check_port(port, host):
            return True
        time.sleep(1)
        if int(time.time() - start) % 15 == 0:
            log(f"Still waiting for port {port}... ({int(time.time() - start)}s)", "WAIT")
    return False


def start_process(name: str, script: Path, python_exe: Optional[str] = None, extra_args: List[str] = None) -> subprocess.Popen:
    """Start a Python process in a new console window."""
    if python_exe is None:
        python_exe = sys.executable
    
    cmd = [python_exe, str(script)]
    if extra_args:
        cmd.extend(extra_args)
    
    log(f"Starting {name}: {' '.join(cmd)}")
    
    proc = subprocess.Popen(
        cmd,
        cwd=str(MAS_DIR),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    processes[name] = proc
    return proc


def stop_all():
    """Stop all managed processes."""
    for name, proc in processes.items():
        try:
            log(f"Stopping {name}...")
            proc.terminate()
            proc.wait(timeout=5)
        except:
            try:
                proc.kill()
            except:
                pass
    processes.clear()


# =============================================================================
# GPU Check
# =============================================================================

def check_gpu() -> Dict[str, Any]:
    """Check GPU availability."""
    try:
        import torch
        if torch.cuda.is_available():
            return {
                "available": True,
                "name": torch.cuda.get_device_name(0),
                "memory_gb": round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1),
                "cuda_version": torch.version.cuda,
            }
    except:
        pass
    return {"available": False}


# =============================================================================
# Service Starters
# =============================================================================

def start_moshi():
    """Start PersonaPlex/Moshi server."""
    if check_port(PORTS["moshi"]):
        log(f"Moshi already running on port {PORTS['moshi']}", "OK")
        return True
    
    log("Starting PersonaPlex/Moshi server (uses ~23GB VRAM)...")
    start_process("moshi", SCRIPTS["moshi"])
    
    log("Waiting for Moshi to load model...", "WAIT")
    if wait_for_port(PORTS["moshi"], timeout=180):
        log(f"Moshi running on port {PORTS['moshi']}", "OK")
        return True
    else:
        log("Moshi failed to start", "FAIL")
        return False


def start_bridge():
    """Start PersonaPlex Bridge."""
    if check_port(PORTS["bridge"]):
        log(f"Bridge already running on port {PORTS['bridge']}", "OK")
        return True
    
    log("Starting PersonaPlex Bridge...")
    start_process("bridge", SCRIPTS["bridge"])
    
    if wait_for_port(PORTS["bridge"], timeout=30):
        log(f"Bridge running on port {PORTS['bridge']}", "OK")
        return True
    else:
        log("Bridge failed to start", "FAIL")
        return False


def start_earth2():
    """Start Earth2Studio API server."""
    if check_port(PORTS["earth2"]):
        log(f"Earth2 already running on port {PORTS['earth2']}", "OK")
        return True
    
    log("Starting Earth2Studio API server...")
    earth2_python = str(EARTH2_VENV / "Scripts" / "python.exe")
    
    # Verify Earth2Studio venv exists
    if not Path(earth2_python).exists():
        log(f"Earth2Studio venv not found at {EARTH2_VENV}", "FAIL")
        log("Run: python scripts/install_local_earth2.py first", "WAIT")
        return False
    
    start_process("earth2", SCRIPTS["earth2"], python_exe=earth2_python)
    
    if wait_for_port(PORTS["earth2"], timeout=30):
        log(f"Earth2 API running on port {PORTS['earth2']}", "OK")
        return True
    else:
        log("Earth2 API failed to start", "FAIL")
        return False


# =============================================================================
# Unified Gateway Server
# =============================================================================

def create_gateway():
    """Create unified GPU gateway server."""
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel
        import httpx
        import uvicorn
    except ImportError:
        log("Installing FastAPI dependencies...", "WAIT")
        subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "httpx", "pydantic", "-q"], check=True)
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel
        import httpx
        import uvicorn
    
    # Import voice handlers
    try:
        from scripts.voice_command_router import route_voice_command, classify_intent_quick
        from scripts.context_injector import get_context_injector, ContextInjector
        voice_router_available = True
    except ImportError:
        voice_router_available = False
        log("Voice router not available - using passthrough mode", "WAIT")
    
    app = FastAPI(
        title="MYCOSOFT GPU Gateway",
        description="Unified gateway for all local GPU services (RTX 5090)",
        version="1.0.0",
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Pydantic models for API
    class VoiceRouteRequest(BaseModel):
        text: str
        context: Optional[Dict[str, Any]] = None
    
    class ContextUpdateRequest(BaseModel):
        map: Optional[Dict[str, Any]] = None
        crep: Optional[Dict[str, Any]] = None
        earth2: Optional[Dict[str, Any]] = None
    
    @app.get("/")
    async def root():
        """Gateway status and service discovery."""
        gpu = check_gpu()
        services = {
            name: {
                "port": port,
                "url": f"http://localhost:{port}",
                "running": check_port(port),
            }
            for name, port in PORTS.items() if name != "gateway"
        }
        
        return {
            "gateway": "MYCOSOFT GPU Gateway",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "gpu": gpu,
            "services": services,
            "dev_server": "http://localhost:3010",
            "voice_router": voice_router_available,
        }
    
    @app.get("/health")
    async def health():
        """Health check for all services."""
        all_healthy = all(check_port(p) for n, p in PORTS.items() if n != "gateway")
        return {
            "status": "healthy" if all_healthy else "degraded",
            "gpu": check_gpu().get("available", False),
            "services": {n: check_port(p) for n, p in PORTS.items() if n != "gateway"},
        }
    
    @app.get("/gpu/status")
    async def gpu_status():
        """Detailed GPU status."""
        try:
            import torch
            if torch.cuda.is_available():
                return {
                    "available": True,
                    "name": torch.cuda.get_device_name(0),
                    "total_memory_gb": round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2),
                    "allocated_memory_gb": round(torch.cuda.memory_allocated() / (1024**3), 2),
                    "cached_memory_gb": round(torch.cuda.memory_reserved() / (1024**3), 2),
                    "cuda_version": torch.version.cuda,
                    "cudnn_version": torch.backends.cudnn.version(),
                }
        except:
            pass
        return {"available": False}
    
    # =============================================================================
    # Voice Command Routing (Earth2 + Map + CREP)
    # =============================================================================
    
    @app.post("/voice/route")
    async def voice_route(request: VoiceRouteRequest):
        """
        Route a voice command through the unified voice command router.
        
        This endpoint:
        1. Classifies the intent (earth2, map, crep, system, general)
        2. Extracts parameters from the command
        3. Returns frontend commands and spoken response
        """
        if not voice_router_available:
            return {
                "success": False,
                "error": "Voice router not available",
                "needs_llm_response": True,
                "raw_text": request.text,
            }
        
        # Update context if provided
        if request.context:
            injector = get_context_injector()
            if request.context.get("map"):
                map_ctx = request.context["map"]
                injector.update_map_context(
                    center=tuple(map_ctx.get("center", [0, 0])),
                    zoom=map_ctx.get("zoom", 2),
                    bearing=map_ctx.get("bearing", 0),
                    pitch=map_ctx.get("pitch", 0),
                    bounds=map_ctx.get("bounds"),
                )
            if request.context.get("earth2"):
                e2_ctx = request.context["earth2"]
                injector.update_earth2_context(
                    active_model=e2_ctx.get("activeModel"),
                    loaded_models=e2_ctx.get("loadedModels"),
                    active_layers=e2_ctx.get("activeLayers"),
                    last_forecast=e2_ctx.get("lastForecast"),
                    gpu_memory_used_gb=e2_ctx.get("gpuMemoryUsed"),
                )
        
        # Route the command
        try:
            result = await route_voice_command(request.text)
            
            # Record command in context
            if voice_router_available:
                injector = get_context_injector()
                injector.record_command(
                    domain=result.get("domain", "unknown"),
                    action=result.get("action", "unknown"),
                    success=result.get("success", False),
                    raw_text=request.text,
                )
            
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "needs_llm_response": True,
                "raw_text": request.text,
            }
    
    @app.get("/voice/classify")
    async def voice_classify(text: str):
        """Quick intent classification without full processing."""
        if not voice_router_available:
            return {"intent": "unknown", "text": text}
        
        intent = classify_intent_quick(text)
        return {"intent": intent, "text": text}
    
    # =============================================================================
    # Context Management
    # =============================================================================
    
    @app.post("/context/update")
    async def update_context(request: ContextUpdateRequest):
        """Update the current context for voice command processing."""
        if not voice_router_available:
            return {"success": False, "error": "Context injector not available"}
        
        injector = get_context_injector()
        
        if request.map:
            center = request.map.get("center", [0, 0])
            injector.update_map_context(
                center=(center[0], center[1]),
                zoom=request.map.get("zoom", 2),
                bearing=request.map.get("bearing", 0),
                pitch=request.map.get("pitch", 0),
                bounds=request.map.get("bounds"),
            )
        
        if request.crep:
            if "active_layers" in request.crep:
                injector.update_crep_layers(request.crep["active_layers"])
            if "visible_entities" in request.crep:
                injector.update_crep_entities(request.crep["visible_entities"])
            if "active_filters" in request.crep:
                injector.update_crep_filters(request.crep["active_filters"])
            if "selected_entity" in request.crep:
                injector.set_selected_entity(request.crep["selected_entity"])
        
        if request.earth2:
            injector.update_earth2_context(
                active_model=request.earth2.get("active_model"),
                loaded_models=request.earth2.get("loaded_models"),
                active_layers=request.earth2.get("active_layers"),
                last_forecast=request.earth2.get("last_forecast"),
                gpu_memory_used_gb=request.earth2.get("gpu_memory_used_gb"),
            )
        
        return {"success": True, "timestamp": datetime.utcnow().isoformat()}
    
    @app.get("/context")
    async def get_context():
        """Get current context for voice processing."""
        if not voice_router_available:
            return {"error": "Context injector not available"}
        
        injector = get_context_injector()
        return injector.get_context_dict()
    
    @app.get("/context/llm")
    async def get_llm_context():
        """Get context formatted for LLM system prompts."""
        if not voice_router_available:
            return {"context": ""}
        
        injector = get_context_injector()
        return {"context": injector.build_context_for_llm()}
    
    # =============================================================================
    # Proxy Endpoints for Service Discovery
    # =============================================================================
    
    @app.api_route("/earth2/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def proxy_earth2(path: str, request: Request):
        """Proxy to Earth2Studio API."""
        async with httpx.AsyncClient() as client:
            try:
                url = f"http://localhost:{PORTS['earth2']}/{path}"
                method = request.method.lower()
                
                if method == "get":
                    resp = await client.get(url, timeout=30.0)
                elif method == "post":
                    body = await request.body()
                    resp = await client.post(url, content=body, timeout=60.0)
                else:
                    resp = await client.request(method, url, timeout=30.0)
                
                return JSONResponse(content=resp.json(), status_code=resp.status_code)
            except Exception as e:
                raise HTTPException(status_code=502, detail=str(e))
    
    @app.api_route("/bridge/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def proxy_voice_bridge(path: str, request: Request):
        """Proxy to PersonaPlex Bridge."""
        async with httpx.AsyncClient() as client:
            try:
                url = f"http://localhost:{PORTS['bridge']}/{path}"
                method = request.method.lower()
                
                if method == "get":
                    resp = await client.get(url, timeout=30.0)
                elif method == "post":
                    body = await request.body()
                    resp = await client.post(url, content=body, timeout=30.0)
                else:
                    resp = await client.request(method, url, timeout=30.0)
                
                return JSONResponse(content=resp.json(), status_code=resp.status_code)
            except Exception as e:
                raise HTTPException(status_code=502, detail=str(e))
    
    return app, uvicorn


# =============================================================================
# Main
# =============================================================================

async def warmup_moshi():
    """Warmup Moshi CUDA graphs."""
    try:
        import aiohttp
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp", "-q"], check=True)
        import aiohttp
    
    log("Warming up Moshi CUDA graphs (may take 60-90s)...", "WAIT")
    
    try:
        async with aiohttp.ClientSession() as session:
            start = time.time()
            async with session.ws_connect(
                "ws://localhost:8998/api/chat",
                timeout=aiohttp.ClientTimeout(total=120)
            ) as ws:
                msg = await asyncio.wait_for(ws.receive(), timeout=120)
                elapsed = time.time() - start
                log(f"CUDA graphs compiled in {elapsed:.1f}s", "OK")
                return True
    except Exception as e:
        log(f"CUDA warmup failed: {e}", "FAIL")
        return False


def main():
    """Main startup sequence."""
    print()
    print("=" * 70)
    print("  MYCOSOFT LOCAL GPU SERVICES")
    print("  February 5, 2026")
    print("=" * 70)
    print()
    
    # Check GPU
    gpu = check_gpu()
    if gpu.get("available"):
        log(f"GPU: {gpu['name']} ({gpu['memory_gb']} GB, CUDA {gpu['cuda_version']})", "OK")
    else:
        log("No GPU detected!", "FAIL")
        return
    
    print()
    log("Starting GPU services for localhost:3010 dev server...")
    print()
    
    # Start services in order
    results = {}
    
    # 1. Moshi (largest VRAM usage)
    log("=" * 50)
    log("PHASE 1: PersonaPlex/Moshi Voice AI")
    results["moshi"] = start_moshi()
    
    if results["moshi"]:
        # Wait a bit for model to fully initialize
        time.sleep(10)
        # Warmup CUDA graphs
        asyncio.run(warmup_moshi())
    
    # 2. Bridge
    log("=" * 50)
    log("PHASE 2: PersonaPlex Voice Bridge")
    if results["moshi"]:
        results["bridge"] = start_bridge()
    else:
        log("Skipping bridge (Moshi not running)", "FAIL")
        results["bridge"] = False
    
    # 3. Earth2Studio
    log("=" * 50)
    log("PHASE 3: Earth2Studio Weather AI")
    results["earth2"] = start_earth2()
    
    # 4. Gateway
    log("=" * 50)
    log("PHASE 4: Unified GPU Gateway")
    
    print()
    print("=" * 70)
    print("  SERVICE STATUS")
    print("=" * 70)
    
    all_ok = True
    for name, status in results.items():
        port = PORTS.get(name, "N/A")
        status_text = "RUNNING" if status else "FAILED"
        icon = "[+]" if status else "[-]"
        print(f"  {icon} {name.upper():12} : localhost:{port} ({status_text})")
        if not status:
            all_ok = False
    
    print()
    print("=" * 70)
    print("  DEV SERVER INTEGRATION")
    print("=" * 70)
    print()
    print("  Add to your .env.local or environment:")
    print()
    print("    # Local GPU Services")
    print(f"    LOCAL_GPU_GATEWAY=http://localhost:{PORTS['gateway']}")
    print(f"    LOCAL_MOSHI_URL=ws://localhost:{PORTS['moshi']}")
    print(f"    LOCAL_BRIDGE_URL=http://localhost:{PORTS['bridge']}")
    print(f"    LOCAL_EARTH2_URL=http://localhost:{PORTS['earth2']}")
    print()
    print("  API Documentation:")
    print(f"    - Gateway:  http://localhost:{PORTS['gateway']}/docs")
    print(f"    - Earth2:   http://localhost:{PORTS['earth2']}/docs")
    print(f"    - Bridge:   http://localhost:{PORTS['bridge']}/health")
    print(f"    - Moshi UI: http://localhost:{PORTS['moshi']}")
    print()
    print("=" * 70)
    
    # Start gateway in foreground
    log("Starting unified GPU gateway on port 8300...")
    app, uvicorn = create_gateway()
    
    print()
    print(f"  Gateway running at http://localhost:{PORTS['gateway']}")
    print("  Press Ctrl+C to stop all services")
    print()
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=PORTS["gateway"], log_level="info")
    except KeyboardInterrupt:
        pass
    finally:
        log("Shutting down services...")
        stop_all()
        log("All services stopped.", "OK")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        stop_all()
