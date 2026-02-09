#!/usr/bin/env python3
"""
Earth2Studio Local API Server - February 5, 2026
Exposes Earth2Studio model inference via FastAPI on the Windows machine with RTX 5090.
This allows the Sandbox VM (192.168.0.187) to call GPU-accelerated inference remotely.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

# FastAPI
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("earth2-api")

# ============================================================================
# Global State
# ============================================================================

class ModelState:
    """Manages loaded models and GPU state"""
    def __init__(self):
        self.loaded_models: Dict[str, Any] = {}
        self.gpu_available: bool = False
        self.gpu_name: str = "Unknown"
        self.gpu_memory_gb: float = 0.0
        self.torch = None
        self.earth2studio = None
    
    def check_gpu(self):
        """Check GPU availability"""
        try:
            import torch
            self.torch = torch
            self.gpu_available = torch.cuda.is_available()
            if self.gpu_available:
                self.gpu_name = torch.cuda.get_device_name(0)
                self.gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"GPU: {self.gpu_name} ({self.gpu_memory_gb:.1f} GB)")
        except ImportError:
            logger.warning("PyTorch not available")
    
    def check_earth2studio(self):
        """Check Earth2Studio availability"""
        try:
            import earth2studio
            self.earth2studio = earth2studio
            logger.info(f"Earth2Studio: {earth2studio.__version__}")
        except ImportError:
            logger.warning("Earth2Studio not available")


state = ModelState()

# ============================================================================
# Request/Response Models
# ============================================================================

class HealthResponse(BaseModel):
    status: str
    gpu_available: bool
    gpu_name: str
    gpu_memory_gb: float
    earth2studio_version: Optional[str]
    loaded_models: List[str]
    timestamp: str


class InferenceRequest(BaseModel):
    model: str = Field(..., description="Model name (e.g., 'fcn', 'pangu', 'graphcast')")
    lead_time: int = Field(default=24, description="Forecast lead time in hours")
    initial_time: Optional[str] = Field(default=None, description="Initial time (ISO format)")
    variables: Optional[List[str]] = Field(default=None, description="Variables to forecast")


class InferenceResponse(BaseModel):
    model: str
    lead_time: int
    initial_time: str
    status: str
    forecast_id: str
    message: str


class ModelInfoResponse(BaseModel):
    name: str
    description: str
    supported_variables: List[str]
    max_lead_time: int
    loaded: bool


# ============================================================================
# Available Models Configuration
# ============================================================================

AVAILABLE_MODELS = {
    "fcn": {
        "name": "FourCastNet",
        "description": "NVIDIA's Fourier Neural Operator for weather forecasting",
        "class": "FCN",
        "module": "earth2studio.models.px",
        "max_lead_time": 240,
        "variables": ["t2m", "u10m", "v10m", "msl", "z500", "t850"],
    },
    "pangu": {
        "name": "Pangu-Weather",
        "description": "Huawei's 3D transformer for global weather prediction",
        "class": "Pangu",
        "module": "earth2studio.models.px",
        "max_lead_time": 168,
        "variables": ["t2m", "u10m", "v10m", "msl", "z500", "t850", "q700"],
    },
    "graphcast": {
        "name": "GraphCast",
        "description": "DeepMind's GNN-based weather model",
        "class": "GraphCast",
        "module": "earth2studio.models.px",
        "max_lead_time": 240,
        "variables": ["t2m", "u10m", "v10m", "msl", "z500", "t850"],
    },
    "sfno": {
        "name": "SFNO",
        "description": "Spherical Fourier Neural Operator",
        "class": "SFNO",
        "module": "earth2studio.models.px",
        "max_lead_time": 168,
        "variables": ["t2m", "u10m", "v10m", "msl"],
    },
}

# ============================================================================
# FastAPI App
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    logger.info("Starting Earth2Studio API Server...")
    state.check_gpu()
    state.check_earth2studio()
    yield
    logger.info("Shutting down Earth2Studio API Server...")
    # Cleanup models
    state.loaded_models.clear()
    if state.torch and state.torch.cuda.is_available():
        state.torch.cuda.empty_cache()


app = FastAPI(
    title="Earth2Studio Local API",
    description="GPU-accelerated weather model inference on RTX 5090",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for VM access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with system status"""
    return HealthResponse(
        status="operational",
        gpu_available=state.gpu_available,
        gpu_name=state.gpu_name,
        gpu_memory_gb=round(state.gpu_memory_gb, 2),
        earth2studio_version=state.earth2studio.__version__ if state.earth2studio else None,
        loaded_models=list(state.loaded_models.keys()),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "gpu": state.gpu_available,
        "models_loaded": len(state.loaded_models),
    }


@app.get("/models", response_model=List[ModelInfoResponse])
async def list_models():
    """List available models"""
    models = []
    for key, info in AVAILABLE_MODELS.items():
        models.append(ModelInfoResponse(
            name=key,
            description=info["description"],
            supported_variables=info["variables"],
            max_lead_time=info["max_lead_time"],
            loaded=key in state.loaded_models,
        ))
    return models


@app.get("/models/{model_name}", response_model=ModelInfoResponse)
async def get_model(model_name: str):
    """Get specific model info"""
    if model_name not in AVAILABLE_MODELS:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    
    info = AVAILABLE_MODELS[model_name]
    return ModelInfoResponse(
        name=model_name,
        description=info["description"],
        supported_variables=info["variables"],
        max_lead_time=info["max_lead_time"],
        loaded=model_name in state.loaded_models,
    )


@app.post("/models/{model_name}/load")
async def load_model(model_name: str):
    """Load a model into GPU memory"""
    if model_name not in AVAILABLE_MODELS:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    
    if not state.gpu_available:
        raise HTTPException(status_code=503, detail="GPU not available")
    
    if model_name in state.loaded_models:
        return {"status": "already_loaded", "model": model_name}
    
    try:
        info = AVAILABLE_MODELS[model_name]
        module = __import__(info["module"], fromlist=[info["class"]])
        model_class = getattr(module, info["class"])
        
        logger.info(f"Loading model: {model_name}")
        model = model_class.load()
        state.loaded_models[model_name] = model
        
        return {"status": "loaded", "model": model_name}
    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/{model_name}/unload")
async def unload_model(model_name: str):
    """Unload a model from GPU memory"""
    if model_name not in state.loaded_models:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not loaded")
    
    del state.loaded_models[model_name]
    if state.torch and state.torch.cuda.is_available():
        state.torch.cuda.empty_cache()
    
    return {"status": "unloaded", "model": model_name}


@app.post("/inference", response_model=InferenceResponse)
async def run_inference(request: InferenceRequest, background_tasks: BackgroundTasks):
    """Run model inference (async)"""
    model_name = request.model
    
    if model_name not in AVAILABLE_MODELS:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    
    if not state.gpu_available:
        raise HTTPException(status_code=503, detail="GPU not available")
    
    # Use current time if not specified
    initial_time = request.initial_time or datetime.utcnow().strftime("%Y-%m-%dT%H:00:00")
    
    # Generate forecast ID
    forecast_id = f"{model_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # For now, return placeholder - actual inference would be async
    return InferenceResponse(
        model=model_name,
        lead_time=request.lead_time,
        initial_time=initial_time,
        status="queued",
        forecast_id=forecast_id,
        message=f"Inference queued. Model: {AVAILABLE_MODELS[model_name]['name']}, Lead time: {request.lead_time}h",
    )


@app.get("/gpu/status")
async def gpu_status():
    """Detailed GPU status"""
    if not state.gpu_available or not state.torch:
        return {"available": False}
    
    torch = state.torch
    return {
        "available": True,
        "name": state.gpu_name,
        "total_memory_gb": round(state.gpu_memory_gb, 2),
        "allocated_memory_gb": round(torch.cuda.memory_allocated() / (1024**3), 2),
        "cached_memory_gb": round(torch.cuda.memory_reserved() / (1024**3), 2),
        "free_memory_gb": round((torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated()) / (1024**3), 2),
        "cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
    }


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Default to port 8220 for Earth2 API
    port = int(os.environ.get("EARTH2_API_PORT", 8220))
    host = os.environ.get("EARTH2_API_HOST", "0.0.0.0")
    
    print(f"""
=====================================================================
         EARTH2STUDIO LOCAL API SERVER
         February 5, 2026
=====================================================================
  Host: {host}:{port}
  GPU:  RTX 5090 (31.8 GB VRAM)
  API:  http://localhost:{port}/docs
=====================================================================
""")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )
