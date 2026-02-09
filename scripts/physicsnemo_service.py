#!/usr/bin/env python3
"""
PhysicsNeMo Local API Service - February 9, 2026

Runs inside an NVIDIA PhysicsNeMo container and exposes a constrained API
for physics-oriented simulation workloads used by MAS simulators.
"""

from __future__ import annotations

import math
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class DiffusionRequest(BaseModel):
    field: List[List[float]]
    diffusion_coefficient: float = Field(gt=0.0, le=10.0)
    dt: float = Field(default=0.1, gt=0.0, le=1.0)
    steps: int = Field(default=5, ge=1, le=200)


class HeatTransferRequest(BaseModel):
    temperature_field: List[List[float]]
    thermal_diffusivity: float = Field(default=0.01, gt=0.0, le=10.0)
    dt: float = Field(default=0.1, gt=0.0, le=1.0)
    steps: int = Field(default=5, ge=1, le=200)


class FluidFlowRequest(BaseModel):
    velocity_u: List[List[float]]
    velocity_v: List[List[float]]
    viscosity: float = Field(gt=0.0, le=10.0)
    dt: float = Field(default=0.05, gt=0.0, le=1.0)
    steps: int = Field(default=5, ge=1, le=200)


class ReactionRequest(BaseModel):
    concentrations: Dict[str, float]
    rate_constants: Dict[str, float]
    dt: float = Field(default=0.1, gt=0.0, le=1.0)
    steps: int = Field(default=10, ge=1, le=1000)


class NeuralOperatorRequest(BaseModel):
    input_vector: List[float]
    weight_matrix: List[List[float]]
    bias: Optional[List[float]] = None
    activation: str = Field(default="tanh")


class PINNRequest(BaseModel):
    equation: str = Field(description="heat|diffusion|laplace")
    x: List[float]
    y: List[float]
    boundary_value: float = 0.0
    source_term: float = 0.0


class ModelManager:
    def __init__(self) -> None:
        self.loaded_models: Dict[str, Dict[str, Any]] = {}

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "model_id": model_id,
                "loaded_at": payload["loaded_at"],
                "kind": payload["kind"],
            }
            for model_id, payload in self.loaded_models.items()
        ]

    def load_model(self, model_id: str, kind: str) -> None:
        self.loaded_models[model_id] = {
            "kind": kind,
            "loaded_at": datetime.utcnow().isoformat() + "Z",
        }

    def unload_model(self, model_id: str) -> bool:
        if model_id not in self.loaded_models:
            return False
        del self.loaded_models[model_id]
        return True


model_manager = ModelManager()
app = FastAPI(title="PhysicsNeMo Local API", version="1.0.0")


def _to_tensor_2d(values: List[List[float]]) -> torch.Tensor:
    try:
        tensor = torch.tensor(values, dtype=torch.float32)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid 2D input array: {exc}") from exc
    if tensor.ndim != 2:
        raise HTTPException(status_code=400, detail="Input must be a 2D array")
    return tensor


def _laplacian_2d(field: torch.Tensor) -> torch.Tensor:
    padded = torch.nn.functional.pad(field.unsqueeze(0).unsqueeze(0), (1, 1, 1, 1), mode="replicate")
    center = padded[:, :, 1:-1, 1:-1]
    left = padded[:, :, 1:-1, 0:-2]
    right = padded[:, :, 1:-1, 2:]
    up = padded[:, :, 0:-2, 1:-1]
    down = padded[:, :, 2:, 1:-1]
    return (left + right + up + down - 4.0 * center).squeeze(0).squeeze(0)


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "service": "physicsnemo-local-api",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "gpu_available": torch.cuda.is_available(),
        "loaded_models": len(model_manager.loaded_models),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/gpu/status")
async def gpu_status() -> Dict[str, Any]:
    if not torch.cuda.is_available():
        return {"available": False}

    device = torch.cuda.current_device()
    props = torch.cuda.get_device_properties(device)
    free_bytes, total_bytes = torch.cuda.mem_get_info(device)
    return {
        "available": True,
        "device": props.name,
        "total_memory_gb": round(total_bytes / (1024 ** 3), 2),
        "free_memory_gb": round(free_bytes / (1024 ** 3), 2),
        "allocated_memory_gb": round(torch.cuda.memory_allocated(device) / (1024 ** 3), 2),
        "cuda_version": torch.version.cuda,
    }


@app.get("/physics/models")
async def list_physics_models() -> Dict[str, Any]:
    return {"models": model_manager.list_models()}


@app.post("/physics/models/load")
async def load_physics_model(payload: Dict[str, str]) -> Dict[str, Any]:
    model_id = payload.get("model_id", "").strip()
    kind = payload.get("kind", "").strip() or "generic"
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")
    model_manager.load_model(model_id=model_id, kind=kind)
    return {"status": "loaded", "model_id": model_id, "kind": kind}


@app.post("/physics/models/unload")
async def unload_physics_model(payload: Dict[str, str]) -> Dict[str, Any]:
    model_id = payload.get("model_id", "").strip()
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")
    removed = model_manager.unload_model(model_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not loaded")
    return {"status": "unloaded", "model_id": model_id}


@app.post("/physics/diffusion")
async def run_diffusion(request: DiffusionRequest) -> Dict[str, Any]:
    field = _to_tensor_2d(request.field)
    for _ in range(request.steps):
        field = field + (request.diffusion_coefficient * request.dt) * _laplacian_2d(field)
    return {
        "status": "completed",
        "final_field": field.cpu().tolist(),
        "min": float(field.min().item()),
        "max": float(field.max().item()),
        "mean": float(field.mean().item()),
    }


@app.post("/physics/heat-transfer")
async def run_heat_transfer(request: HeatTransferRequest) -> Dict[str, Any]:
    temperature = _to_tensor_2d(request.temperature_field)
    for _ in range(request.steps):
        temperature = temperature + (request.thermal_diffusivity * request.dt) * _laplacian_2d(temperature)
    return {
        "status": "completed",
        "temperature_field": temperature.cpu().tolist(),
        "max_temperature": float(temperature.max().item()),
        "min_temperature": float(temperature.min().item()),
    }


@app.post("/physics/fluid-flow")
async def run_fluid_flow(request: FluidFlowRequest) -> Dict[str, Any]:
    u = _to_tensor_2d(request.velocity_u)
    v = _to_tensor_2d(request.velocity_v)
    if u.shape != v.shape:
        raise HTTPException(status_code=400, detail="velocity_u and velocity_v must have the same shape")

    for _ in range(request.steps):
        u = u + (request.viscosity * request.dt) * _laplacian_2d(u)
        v = v + (request.viscosity * request.dt) * _laplacian_2d(v)

    speed = torch.sqrt((u * u) + (v * v))
    reynolds = float(speed.mean().item() / max(request.viscosity, 1e-6))
    pressure_proxy = -(u + v)
    return {
        "status": "completed",
        "velocity_u": u.cpu().tolist(),
        "velocity_v": v.cpu().tolist(),
        "velocity_magnitude_mean": float(speed.mean().item()),
        "pressure_field": pressure_proxy.cpu().tolist(),
        "reynolds_number_proxy": reynolds,
    }


@app.post("/physics/reaction")
async def run_reaction(request: ReactionRequest) -> Dict[str, Any]:
    concentrations = {k: max(0.0, float(v)) for k, v in request.concentrations.items()}
    rate_constants = {k: max(0.0, float(v)) for k, v in request.rate_constants.items()}
    history: Dict[str, List[float]] = {k: [v] for k, v in concentrations.items()}

    for _ in range(request.steps):
        for species, value in list(concentrations.items()):
            decay_key = f"{species}_decay"
            growth_key = f"{species}_growth"
            decay = rate_constants.get(decay_key, 0.0) * value
            growth = rate_constants.get(growth_key, 0.0)
            updated = max(0.0, value + (growth - decay) * request.dt)
            concentrations[species] = updated
            history[species].append(updated)

    return {"status": "completed", "final_concentrations": concentrations, "history": history}


@app.post("/physics/neural-operator")
async def run_neural_operator(request: NeuralOperatorRequest) -> Dict[str, Any]:
    input_vec = torch.tensor(request.input_vector, dtype=torch.float32)
    weights = torch.tensor(request.weight_matrix, dtype=torch.float32)
    if weights.ndim != 2:
        raise HTTPException(status_code=400, detail="weight_matrix must be 2D")
    if weights.shape[1] != input_vec.shape[0]:
        raise HTTPException(status_code=400, detail="weight_matrix columns must match input_vector length")

    output = torch.matmul(weights, input_vec)
    if request.bias:
        bias = torch.tensor(request.bias, dtype=torch.float32)
        if bias.shape[0] != output.shape[0]:
            raise HTTPException(status_code=400, detail="bias length must match output size")
        output = output + bias

    activation = request.activation.lower()
    if activation == "relu":
        output = torch.relu(output)
    elif activation == "sigmoid":
        output = torch.sigmoid(output)
    elif activation == "tanh":
        output = torch.tanh(output)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported activation: {request.activation}")

    return {"status": "completed", "output_vector": output.cpu().tolist(), "activation": activation}


@app.post("/physics/pinn")
async def run_pinn(request: PINNRequest) -> Dict[str, Any]:
    if len(request.x) != len(request.y):
        raise HTTPException(status_code=400, detail="x and y must be same length")

    points = []
    for x_val, y_val in zip(request.x, request.y):
        r2 = (x_val * x_val) + (y_val * y_val)
        if request.equation == "laplace":
            value = request.boundary_value * math.exp(-math.sqrt(max(r2, 1e-6)))
        elif request.equation in {"heat", "diffusion"}:
            value = request.boundary_value + request.source_term * math.exp(-r2)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported equation: {request.equation}")
        points.append({"x": x_val, "y": y_val, "u": value})

    return {"status": "completed", "equation": request.equation, "solution": points}


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("PHYSICSNEMO_API_HOST", "0.0.0.0")
    port = int(os.environ.get("PHYSICSNEMO_API_PORT", "8400"))
    uvicorn.run(app, host=host, port=port, log_level="info")
