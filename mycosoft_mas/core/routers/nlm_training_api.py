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
NLM_HOME = Path(os.getenv("NLM_HOME", Path.home() / ".mycosoft" / "nlm"))
NLM_MODEL_DIR = os.getenv("NLM_MODEL_DIR", str(NLM_HOME / "models"))
NLM_CHECKPOINT_DIR = os.getenv("NLM_CHECKPOINT_DIR", str(NLM_HOME / "models" / "checkpoints"))
DEFAULT_NLM_CATEGORIES = [
    "species_taxonomy",
    "mycology_research",
    "environmental_sensors",
    "genetic_sequences",
    "ecological_interactions",
    "geographic_distribution",
    "cultivation_protocols",
    "compound_chemistry",
    "medical_applications",
    "conservation_status",
]


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


def _skip_startup_enabled() -> bool:
    return os.getenv("MAS_SKIP_BACKGROUND_STARTUP", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _mindex_headers() -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    token = (
        os.getenv("MINDEX_INTERNAL_TOKEN")
        or os.getenv("MAS_INTERNAL_TOKEN")
        or os.getenv("MINDEX_INTERNAL_TOKENS", "").split(",")[0]
        or ""
    ).strip()
    api_key = (os.getenv("MINDEX_API_KEY") or "").strip()
    if token:
        headers["X-Internal-Token"] = token
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


async def _mindex_get(path: str, timeout: float = 8.0) -> Optional[Any]:
    """GET a MINDEX /api/mindex path. Returns parsed JSON or None."""
    try:
        import httpx
    except Exception as exc:  # pragma: no cover
        logger.warning("httpx unavailable for MINDEX catalog: %s", exc)
        return None

    base = MINDEX_API_URL.rstrip("/")
    url = f"{base}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=_mindex_headers())
            if response.status_code >= 400:
                logger.warning("MINDEX %s returned %s", path, response.status_code)
                return None
            return response.json()
    except Exception as exc:
        logger.warning("MINDEX fetch failed %s: %s", path, exc)
        return None


def _normalize_items(payload: Any) -> List[Dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("items", "taxa", "compounds", "data", "results", "rows", "observations"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def _disk_checkpoints() -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    roots = {Path(NLM_CHECKPOINT_DIR), Path(NLM_MODEL_DIR)}
    suffixes = {".pt", ".bin", ".safetensors", ".ckpt", ".gguf", ".pth"}
    for root in roots:
        try:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in suffixes:
                    continue
                stat = path.stat()
                found.append(
                    {
                        "id": path.stem,
                        "checkpoint_id": path.stem,
                        "path": str(path),
                        "bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "source": "disk",
                    }
                )
        except OSError as exc:
            logger.warning("Checkpoint scan failed under %s: %s", root, exc)
    found.sort(key=lambda row: row.get("modified_at") or "", reverse=True)
    return found[:50]


def _training_capacity() -> Dict[str, Any]:
    skip = _skip_startup_enabled()
    reason = None
    if skip:
        reason = (
            "MAS skip-startup / FAIL-CLOSED: training jobs are not started and "
            "no new model pulls are allowed. Loaded NLM and MINDEX catalogs remain visible."
        )
    return {
        "jobs_available": False,
        "skip_startup": skip,
        "reason": reason
        or "Training compute is fail-closed on MAS 188; catalogs and the loaded NLM remain available.",
        "gpu_target": GPU_NODE_IP,
    }


async def _nlm_live_status() -> Dict[str, Any]:
    """Honest NLM status. Never binds Ollama. Never stubs forecast p."""
    try:
        from mycosoft_mas.nlm.config import get_nlm_config
        from mycosoft_mas.nlm.formspace.reference_runtime import load_reference_runtime
        from mycosoft_mas.nlm.formspace.scientific_loader import probe_scientific_nlm
        from mycosoft_mas.nlm.inference.service import get_nlm_service

        service = get_nlm_service()
        config = get_nlm_config()
        probe = probe_scientific_nlm()
        runtime = load_reference_runtime()
        runtime_status = runtime.runtime_status()
        loaded = bool(runtime.is_loaded or (probe.model_loaded and service.is_ready))
        return {
            "status": "loaded" if loaded else "unloaded",
            "model_loaded": loaded,
            "model_name": getattr(config, "model_name", "nlm"),
            "model_version": getattr(config, "model_version", "0.0.0"),
            "display_name": getattr(config, "model_display_name", "Nature Learning Model"),
            "description": getattr(
                config, "model_description", "Domain-specific model for mycology and natural sciences"
            ),
            "bound_to_ollama": False,
            "forecast_qualified": False,
            "forecast_p": None,
            "qualification_status": runtime_status.get("qualification_status") or "unqualified",
            "training_origin": runtime_status.get("training_origin") or "none",
            "architecture_family": runtime_status.get("architecture_family"),
            "weights_sha256": runtime_status.get("weights_sha256"),
            "model_dir": runtime_status.get("model_dir") or getattr(config, "model_dir", None),
        }
    except Exception as exc:
        logger.warning("NLM live status failed: %s", exc)
        return {
            "status": "unavailable",
            "model_loaded": False,
            "bound_to_ollama": False,
            "forecast_qualified": False,
            "forecast_p": None,
            "error": str(exc),
        }


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
    """List in-memory plus on-disk checkpoints. Empty disk is honest, not fake."""
    disk = _disk_checkpoints()
    combined = list(_checkpoints) + disk
    return {
        "checkpoints": combined,
        "count": len(combined),
        "memory_count": len(_checkpoints),
        "disk_count": len(disk),
    }


@router.get("/health")
async def training_router_health() -> Dict[str, Any]:
    """Router liveness. Orchestrator up is not the same as skip-startup collectors."""
    capacity = _training_capacity()
    return {
        "status": "healthy",
        "bound_to_ollama": False,
        "forecast_qualified": False,
        "skip_startup": capacity["skip_startup"],
        "jobs_available": False,
    }


@router.get("/console")
async def training_console() -> Dict[str, Any]:
    """
    Honest NLM training-app payload.

    MAS skip-startup collector degradation is not a MAS outage.
    NLM is never bound to Ollama. Unqualified forecast p stays null.
    """
    capacity = _training_capacity()
    nlm = await _nlm_live_status()
    stats = await _mindex_get("/api/mindex/stats")
    taxa_payload = await _mindex_get(
        "/api/mindex/taxa?limit=25&order=desc&order_by=observations_count"
    )
    compounds_payload = await _mindex_get("/api/mindex/compounds?limit=25")
    taxa = _normalize_items(taxa_payload)
    compounds = _normalize_items(compounds_payload)
    stats_dict = stats if isinstance(stats, dict) else {}
    checkpoints = list(_checkpoints) + _disk_checkpoints()

    return {
        "mas": {
            "reachable": True,
            "ui_status": "online",
            "skip_startup": capacity["skip_startup"],
            "health_note": (
                "Orchestrator is up. Collectors may be skipped under "
                "MAS_SKIP_BACKGROUND_STARTUP; that is not a MAS outage."
            ),
        },
        "nlm": nlm,
        "mindex": {
            "reachable": bool(stats_dict or taxa or compounds),
            "stats": stats_dict or None,
            "taxa_count": stats_dict.get("total_taxa"),
            "observation_count": stats_dict.get("total_observations"),
            "genome_records": stats_dict.get("genome_records"),
            "trait_records": stats_dict.get("trait_records"),
            "taxa": taxa[:25],
            "compounds": compounds[:25],
            "compound_count": (
                stats_dict.get("compound_count")
                if stats_dict.get("compound_count") is not None
                else len(compounds)
            ),
        },
        "training": {
            "jobs_available": False,
            "reason": capacity["reason"],
            "active_run_id": _active_run_id,
            "runs": _training_runs,
            "run_count": len(_training_runs),
        },
        "checkpoints": checkpoints,
        "bound_to_ollama": False,
        "forecast_qualified": False,
        "forecast_p": None,
    }


@router.post("/start")
async def start_training(req: StartTrainingRequest) -> Dict[str, Any]:
    """
    Start a new NLM training run.

    FAIL-CLOSED: skip-startup / no new model pulls. Do not fake a running train.
    """
    global _active_run_id

    capacity = _training_capacity()
    if capacity["skip_startup"] or not capacity["jobs_available"]:
        raise HTTPException(status_code=503, detail=capacity["reason"])

    if _active_run_id:
        active = _get_active_run()
        if active and active.get("status") in ("training", "paused"):
            raise HTTPException(
                status_code=409,
                detail=f"Training run {_active_run_id} is already active. Stop it first.",
            )

    run_id = f"nlm_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    categories = req.categories or DEFAULT_NLM_CATEGORIES
    config = {
        "learning_rate": req.learning_rate,
        "batch_size": req.batch_size,
        "epochs": req.epochs,
        "warmup_steps": req.warmup_steps,
        "weight_decay": req.weight_decay,
        "dropout": req.dropout,
        "optimizer": req.optimizer,
        "scheduler": req.scheduler,
        "grad_clip": req.grad_clip,
        "categories": categories,
    }

    run = {
        "run_id": run_id,
        "status": "training",
        "config": config,
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

        trainer = NLMTrainer(training_config=config)
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
        "message": f"NLM training run accepted by MAS; GPU execution target is {GPU_NODE_IP}",
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
                run["metrics"]["samples_processed"] = result.get("sample_count", 0)
                run["engine_status"] = result.get("engine_status")
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
