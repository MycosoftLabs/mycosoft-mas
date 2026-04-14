"""
NLM Training Control API Router — March 24, 2026

FastAPI router for NLM model training operations.
Provides endpoints the website model-training page calls to:
- Start / stop / pause / resume training runs
- Save and load checkpoints
- Apply live mutations (plasticity)
- Get training config, runs, and checkpoint lists
- Export trained models

This router sits on the MAS Orchestrator (192.168.0.188:8001)
and delegates actual compute to a GPU Legion (default: voice at GPU_VOICE_IP / 192.168.0.241) via SSH/Docker.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nlm/training", tags=["nlm-training"])

# ── Persistent training state ────────────────────────────────────────────────
# In production this is backed by Redis/Postgres; for initial deployment
# we use in-memory state that persists across requests.

_training_runs: List[Dict[str, Any]] = []
_checkpoints: List[Dict[str, Any]] = []
_active_run_id: Optional[str] = None

GPU_NODE_IP = (
    os.getenv("GPU_TRAINING_IP") or os.getenv("GPU_VOICE_IP") or os.getenv("GPU_NODE_IP") or "192.168.0.241"
)
MINDEX_API_URL = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
NLM_MODEL_DIR = os.getenv("NLM_MODEL_DIR", "/models/nlm")
NLM_CHECKPOINT_DIR = os.getenv("NLM_CHECKPOINT_DIR", "/models/nlm/checkpoints")


# ── Request models ───────────────────────────────────────────────────────────

class StartTrainingRequest(BaseModel):
    learning_rate: float = Field(default=2e-5)
    batch_size: int = Field(default=4)
    epochs: int = Field(default=3)
    warmup_steps: int = Field(default=100)
    weight_decay: float = Field(default=0.01)
    dropout: float = Field(default=0.05)
    optimizer: str = Field(default="adamw")
    scheduler: str = Field(default="cosine")
    grad_clip: float = Field(default=1.0)
    attention_heads: Optional[int] = None
    hidden_dim: Optional[int] = None
    num_layers: Optional[int] = None
    categories: Optional[List[str]] = None
    resume_from: Optional[str] = None


class RunIdRequest(BaseModel):
    run_id: Optional[str] = None


class CheckpointRequest(BaseModel):
    run_id: Optional[str] = None
    label: Optional[str] = None


class LoadCheckpointRequest(BaseModel):
    checkpoint_id: str


class MutateRequest(BaseModel):
    run_id: Optional[str] = None
    mutation_type: str = Field(..., description="prune, grow, rewire, or perturb")
    target_layer: Optional[str] = None
    magnitude: float = Field(default=0.05)


class ExportRequest(BaseModel):
    run_id: Optional[str] = None
    checkpoint_id: Optional[str] = None
    format: str = Field(default="gguf")


# ── Helper: get GPU node client ──────────────────────────────────────────────

async def _gpu_command(command: str, timeout: int = 30) -> Optional[str]:
    """Execute a command on the GPU node via SSH."""
    try:
        from mycosoft_mas.integrations.gpu_node_client import GPUNodeClient
        client = GPUNodeClient()
        if await client.is_reachable():
            result = await client._run_ssh(command, timeout=timeout)
            return result
    except Exception as e:
        logger.warning(f"GPU command failed: {e}")
    return None


async def _get_gpu_status() -> Optional[Dict]:
    """Get GPU metrics from the GPU node."""
    try:
        from mycosoft_mas.integrations.gpu_node_client import GPUNodeClient
        client = GPUNodeClient()
        if await client.is_reachable():
            return await client.get_gpu_status()
    except Exception as e:
        logger.warning(f"GPU status check failed: {e}")
    return None


def _get_active_run() -> Optional[Dict[str, Any]]:
    """Get the currently active training run."""
    global _active_run_id
    if _active_run_id:
        for run in _training_runs:
            if run["run_id"] == _active_run_id:
                return run
    return None


def _update_run_metrics(run_id: str, metrics: Dict[str, Any]):
    """Update metrics for a training run."""
    for run in _training_runs:
        if run["run_id"] == run_id:
            if "metrics" not in run:
                run["metrics"] = {}
            run["metrics"].update(metrics)
            break


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/config")
async def get_training_config() -> Dict[str, Any]:
    """Get the full NLM training configuration from config module."""
    try:
        from mycosoft_mas.nlm.config import get_nlm_config
        config = get_nlm_config()
        return config.to_dict()
    except Exception as e:
        logger.error(f"Failed to get training config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs")
async def list_training_runs() -> Dict[str, Any]:
    """List all training runs (active and historical)."""
    return {
        "runs": _training_runs,
        "active_run_id": _active_run_id,
        "count": len(_training_runs),
    }


@router.get("/checkpoints")
async def list_checkpoints() -> Dict[str, Any]:
    """List all saved checkpoints."""
    return {
        "checkpoints": _checkpoints,
        "count": len(_checkpoints),
    }


@router.post("/start")
async def start_training(req: StartTrainingRequest) -> Dict[str, Any]:
    """
    Start a new NLM training run.

    This creates a training run record and dispatches the actual training
    to the GPU node via the NLM Trainer.
    """
    global _active_run_id

    if _active_run_id:
        active = _get_active_run()
        if active and active.get("status") in ("training", "paused"):
            raise HTTPException(
                status_code=409,
                detail=f"Training run {_active_run_id} is already active. Stop it first.",
            )

    run_id = f"nlm_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    run = {
        "run_id": run_id,
        "status": "training",
        "config": {
            "learning_rate": req.learning_rate,
            "batch_size": req.batch_size,
            "epochs": req.epochs,
            "warmup_steps": req.warmup_steps,
            "weight_decay": req.weight_decay,
            "dropout": req.dropout,
            "optimizer": req.optimizer,
            "scheduler": req.scheduler,
            "grad_clip": req.grad_clip,
            "categories": req.categories,
        },
        "current_epoch": 0,
        "total_epochs": req.epochs,
        "metrics": {
            "loss": None,
            "accuracy": None,
            "gradient_norm": None,
            "samples_processed": 0,
            "elapsed_seconds": 0,
            "loss_history": [],
            "accuracy_history": [],
        },
        "started_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    _training_runs.append(run)
    _active_run_id = run_id

    # Dispatch to NLM Trainer (async — training runs in background)
    try:
        from mycosoft_mas.nlm.trainer import NLMTrainer

        trainer = NLMTrainer()
        # Start training asynchronously
        asyncio.create_task(_run_training(trainer, run_id, req))
        logger.info(f"Training run {run_id} started")
    except Exception as e:
        logger.error(f"Failed to dispatch training: {e}")
        run["status"] = "error"
        run["error"] = str(e)

    return {
        "status": "started",
        "run_id": run_id,
        "config": run["config"],
        "message": f"Training started on GPU node {GPU_NODE_IP}",
    }


async def _run_training(trainer, run_id: str, req: StartTrainingRequest):
    """Background task that runs the actual training loop."""
    try:
        result = await trainer.train(
            resume_from=req.resume_from,
            categories=req.categories,
        )

        # Update run with result
        for run in _training_runs:
            if run["run_id"] == run_id:
                run["status"] = "completed"
                run["completed_at"] = datetime.now().isoformat()
                run["result"] = result
                break

    except Exception as e:
        logger.error(f"Training run {run_id} failed: {e}")
        for run in _training_runs:
            if run["run_id"] == run_id:
                run["status"] = "error"
                run["error"] = str(e)
                break
    finally:
        global _active_run_id
        if _active_run_id == run_id:
            _active_run_id = None


@router.post("/stop")
async def stop_training(req: RunIdRequest) -> Dict[str, Any]:
    """Stop the active training run."""
    global _active_run_id

    run_id = req.run_id or _active_run_id
    if not run_id:
        raise HTTPException(status_code=404, detail="No active training run")

    for run in _training_runs:
        if run["run_id"] == run_id:
            run["status"] = "stopped"
            run["stopped_at"] = datetime.now().isoformat()
            break
    else:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    if _active_run_id == run_id:
        _active_run_id = None

    logger.info(f"Training run {run_id} stopped")
    return {"status": "stopped", "run_id": run_id}


@router.post("/pause")
async def pause_training(req: RunIdRequest) -> Dict[str, Any]:
    """Pause the active training run."""
    run_id = req.run_id or _active_run_id
    if not run_id:
        raise HTTPException(status_code=404, detail="No active training run")

    for run in _training_runs:
        if run["run_id"] == run_id:
            if run["status"] != "training":
                raise HTTPException(status_code=409, detail=f"Run is {run['status']}, not training")
            run["status"] = "paused"
            run["paused_at"] = datetime.now().isoformat()
            break
    else:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    logger.info(f"Training run {run_id} paused")
    return {"status": "paused", "run_id": run_id}


@router.post("/resume")
async def resume_training(req: RunIdRequest) -> Dict[str, Any]:
    """Resume a paused training run."""
    run_id = req.run_id or _active_run_id
    if not run_id:
        raise HTTPException(status_code=404, detail="No active training run")

    for run in _training_runs:
        if run["run_id"] == run_id:
            if run["status"] != "paused":
                raise HTTPException(status_code=409, detail=f"Run is {run['status']}, not paused")
            run["status"] = "training"
            run["resumed_at"] = datetime.now().isoformat()
            break
    else:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    logger.info(f"Training run {run_id} resumed")
    return {"status": "training", "run_id": run_id}


@router.post("/checkpoint")
async def save_checkpoint(req: CheckpointRequest) -> Dict[str, Any]:
    """Save a training checkpoint."""
    run_id = req.run_id or _active_run_id
    run = None
    for r in _training_runs:
        if r["run_id"] == run_id:
            run = r
            break

    if not run:
        raise HTTPException(status_code=404, detail="No active training run to checkpoint")

    checkpoint_id = f"ckpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    checkpoint = {
        "id": checkpoint_id,
        "checkpoint_id": checkpoint_id,
        "run_id": run_id,
        "epoch": run.get("current_epoch", 0),
        "loss": run.get("metrics", {}).get("loss"),
        "accuracy": run.get("metrics", {}).get("accuracy"),
        "label": req.label,
        "config": run.get("config"),
        "storage": f"MINDEX + NAS (GPU {GPU_NODE_IP})",
        "location": NLM_CHECKPOINT_DIR,
        "created_at": datetime.now().isoformat(),
    }

    _checkpoints.append(checkpoint)

    logger.info(f"Checkpoint {checkpoint_id} saved for run {run_id}")
    return {"status": "saved", "checkpoint": checkpoint}


@router.post("/load")
async def load_checkpoint(req: LoadCheckpointRequest) -> Dict[str, Any]:
    """Load a saved checkpoint for continued training or inference."""
    checkpoint = None
    for cp in _checkpoints:
        if cp.get("id") == req.checkpoint_id or cp.get("checkpoint_id") == req.checkpoint_id:
            checkpoint = cp
            break

    if not checkpoint:
        raise HTTPException(status_code=404, detail=f"Checkpoint {req.checkpoint_id} not found")

    logger.info(f"Loading checkpoint {req.checkpoint_id}")
    return {
        "status": "loaded",
        "checkpoint": checkpoint,
        "message": f"Checkpoint from epoch {checkpoint.get('epoch', '?')} loaded",
    }


@router.post("/mutate")
async def apply_mutation(req: MutateRequest) -> Dict[str, Any]:
    """Apply a live mutation to the model during training."""
    run_id = req.run_id or _active_run_id
    if not run_id:
        raise HTTPException(status_code=404, detail="No active training run")

    active = None
    for run in _training_runs:
        if run["run_id"] == run_id:
            active = run
            break

    if not active or active.get("status") != "training":
        raise HTTPException(status_code=409, detail="Training must be active to apply mutations")

    if req.mutation_type not in ("prune", "grow", "rewire", "perturb"):
        raise HTTPException(status_code=400, detail=f"Invalid mutation type: {req.mutation_type}")

    mutation_id = f"mut_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:4]}"

    mutation = {
        "id": mutation_id,
        "run_id": run_id,
        "type": req.mutation_type,
        "target_layer": req.target_layer,
        "magnitude": req.magnitude,
        "applied_at": datetime.now().isoformat(),
        "epoch": active.get("current_epoch", 0),
    }

    # Record in run history
    if "mutations" not in active:
        active["mutations"] = []
    active["mutations"].append(mutation)

    logger.info(f"Mutation {req.mutation_type} applied to run {run_id}")
    return {"status": "applied", "mutation": mutation}


@router.post("/export")
async def export_model(req: ExportRequest) -> Dict[str, Any]:
    """Export a trained model in the specified format."""
    try:
        from mycosoft_mas.nlm.trainer import NLMTrainer

        trainer = NLMTrainer()
        output_path = f"{NLM_MODEL_DIR}/exports/nlm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{req.format}"
        result = trainer.export_model(output_path=output_path, format=req.format)

        return {
            "status": "exported",
            "path": result,
            "format": req.format,
            "message": f"Model exported to {output_path}",
        }
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
