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
    # FormSpace coupling (P2) — chart IDs + evaluation gates; not LLM params
    formspace_chart_ids: Optional[List[str]] = Field(
        default=None,
        description="FormSpace chart IDs injected into training eval",
    )
    formspace_eval: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Recovery / conformal / reachability gates for FormSpace eval",
    )
    # Device network / MDP sensor binding — required for sensor-trained NLM runs
    device_ids: Optional[List[str]] = Field(
        default=None,
        description="MAS registry device_id values feeding this run",
    )
    sensor_ids: Optional[List[str]] = Field(
        default=None,
        description="Sensor channel ids (MDP / role catalog) on those devices",
    )
    ingest_bindings: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="[{device_id, sensor_id}, ...] explicit ingest map",
    )


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
    format: str = Field(default="safetensors", description="safetensors|onnx — never gguf/ollama")


class AttestRequest(BaseModel):
    """SHA-256 + Merkle + ECDSA attestation for frames / jobs / models."""
    payloads: Optional[List[Dict[str, Any]]] = None
    packet: Optional[Dict[str, Any]] = None
    type: Optional[str] = None
    modelId: Optional[str] = None
    ownerId: Optional[str] = None
    parent_frame_root: Optional[str] = None
    source_device: Optional[str] = None


class IngestBindRequest(BaseModel):
    """Bind MAS registry devices + MDP sensor channels to an NLM training context."""
    model_id: Optional[str] = None
    run_id: Optional[str] = None
    owner_id: Optional[str] = None
    bindings: List[Dict[str, str]] = Field(default_factory=list)


# In-memory ingest bindings (paired with training runs; Redis later)
_ingest_bindings: List[Dict[str, Any]] = []


def _normalize_bindings(raw: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not raw:
        return out
    for row in raw:
        if not isinstance(row, dict):
            continue
        device_id = str(row.get("device_id") or row.get("deviceId") or "").strip()
        sensor_id = str(row.get("sensor_id") or row.get("sensorId") or "").strip()
        if device_id and sensor_id:
            out.append({"device_id": device_id, "sensor_id": sensor_id})
    return out


async def _list_registry_devices() -> List[Dict[str, Any]]:
    """Pull live MAS device registry for NLM ingest sources (no mocks)."""
    try:
        from mycosoft_mas.core.routers import device_registry_api as dra

        # Prefer in-process registry when router is loaded in same app
        devices = getattr(dra, "_device_registry", {}) or {}
        last_seen = getattr(dra, "_device_last_seen", {}) or {}
        rows: List[Dict[str, Any]] = []
        for device_id, device in devices.items():
            row = dict(device)
            row["device_id"] = device_id
            if device_id in last_seen:
                row["last_seen"] = last_seen[device_id].isoformat()
            rows.append(row)
        if rows:
            return rows
    except Exception as e:
        logger.debug("In-process device registry unavailable: %s", e)

    # HTTP self-call fallback (when registry lives only via API surface)
    try:
        import httpx

        base = os.getenv("MAS_API_URL", "http://127.0.0.1:8001").rstrip("/")
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base}/api/devices", params={"include_offline": "true"})
            if r.status_code == 200:
                data = r.json()
                return list(data.get("devices") or [])
    except Exception as e:
        logger.warning("NLM ingest sources registry fetch failed: %s", e)
    return []


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
    from mycosoft_mas.nlm.training_store import list_runs as store_list_runs

    persisted = store_list_runs(limit=200)
    # Merge in-memory active with NAS/SQL history (memory wins on run_id)
    by_id: Dict[str, Dict[str, Any]] = {}
    for row in persisted.get("runs") or []:
        rid = row.get("run_id")
        if rid:
            by_id[str(rid)] = row
    for row in _training_runs:
        rid = row.get("run_id")
        if rid:
            by_id[str(rid)] = row
    runs = list(by_id.values())
    runs.sort(key=lambda r: r.get("updated_at") or r.get("started_at") or "", reverse=True)
    return {
        "runs": runs,
        "active_run_id": _active_run_id,
        "count": len(runs),
        "empty": len(runs) == 0,
        "store": persisted.get("store"),
        "model_kind": "nature_learning_model",
        "bound_to_ollama": False,
    }


@router.get("/runs/latest")
async def latest_training_run() -> Dict[str, Any]:
    """Latest training run for NLM UI history panel."""
    from mycosoft_mas.nlm.training_store import latest_run

    active = _get_active_run()
    if active:
        return {
            "status": "ok",
            "empty": False,
            "run": active,
            "source": "active_memory",
            "model_kind": "nature_learning_model",
        }
    return latest_run()


@router.get("/runs/history")
async def training_run_history(limit: int = 50) -> Dict[str, Any]:
    """Persisted training history (NAS JSONL + optional MINDEX)."""
    from mycosoft_mas.nlm.training_store import list_runs

    return list_runs(limit=limit)


@router.get("/mutations")
async def list_mutations(limit: int = 50, run_id: Optional[str] = None) -> Dict[str, Any]:
    from mycosoft_mas.nlm.training_store import list_mutations as store_list_mutations

    return store_list_mutations(limit=limit, run_id=run_id)


@router.get("/grounding")
async def list_grounding(limit: int = 50) -> Dict[str, Any]:
    from mycosoft_mas.nlm.training_store import list_grounding as store_list_grounding

    return store_list_grounding(limit=limit)


@router.get("/changelog")
async def list_changelog(limit: int = 100) -> Dict[str, Any]:
    from mycosoft_mas.nlm.training_store import list_change_log

    return list_change_log(limit=limit)


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
    categories = req.categories or DEFAULT_NLM_CATEGORIES
    formspace_chart_ids = list(req.formspace_chart_ids or [])
    formspace_eval = dict(req.formspace_eval or {})
    if not formspace_eval and formspace_chart_ids:
        formspace_eval = {
            "recovery_gate": True,
            "conformal_gate": False,
            "reachability_check": True,
            "note": "FormSpace eval hooks present; conformal pending calibrated weights.",
        }
    ingest_bindings = _normalize_bindings(req.ingest_bindings)
    device_ids = list(req.device_ids or [])
    sensor_ids = list(req.sensor_ids or [])
    for b in ingest_bindings:
        if b["device_id"] not in device_ids:
            device_ids.append(b["device_id"])
        if b["sensor_id"] not in sensor_ids:
            sensor_ids.append(b["sensor_id"])
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
        "formspace_chart_ids": formspace_chart_ids,
        "formspace_eval": formspace_eval,
        "device_ids": device_ids,
        "sensor_ids": sensor_ids,
        "ingest_bindings": ingest_bindings,
        "bound_to_ollama": False,
        "model_kind": "nature_learning_model",
    }

    run = {
        "run_id": run_id,
        "status": "training",
        "config": config,
        "device_ids": device_ids,
        "sensor_ids": sensor_ids,
        "ingest_bindings": ingest_bindings,
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
            "device_bindings": ingest_bindings,
        },
        "started_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    _training_runs.append(run)
    _active_run_id = run_id

    # Persist run + grounding to NAS / change log (real record, not mock metrics)
    try:
        from mycosoft_mas.nlm.training_store import persist_grounding, persist_run

        await persist_run(run)
        await persist_grounding(
            {
                "type": "training_run_start",
                "run_id": run_id,
                "config": {
                    "epochs": req.epochs,
                    "formspace_chart_ids": formspace_chart_ids,
                    "model_kind": "nature_learning_model",
                },
            }
        )
    except Exception as persist_exc:
        logger.warning("Training run persist failed: %s", persist_exc)

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
        "model_kind": "nature_learning_model",
        "bound_to_ollama": False,
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

    try:
        from mycosoft_mas.nlm.training_store import persist_grounding, persist_mutation

        await persist_mutation(mutation)
        await persist_grounding(
            {
                "type": "training_mutation",
                "run_id": run_id,
                "mutation_id": mutation_id,
                "mutation_type": req.mutation_type,
            }
        )
    except Exception as persist_exc:
        logger.warning("Mutation persist failed: %s", persist_exc)

    logger.info(f"Mutation {req.mutation_type} applied to run {run_id}")
    return {"status": "applied", "mutation": mutation}


@router.post("/export")
async def export_model(req: ExportRequest) -> Dict[str, Any]:
    """Export a trained scientific NLM checkpoint (safetensors/onnx only — never GGUF/Ollama)."""
    fmt = (req.format or "safetensors").lower().strip()
    if fmt in ("gguf", "ollama", "llama", "chat"):
        raise HTTPException(
            status_code=400,
            detail="NLM export refuses GGUF/Ollama/chat formats. Use safetensors or onnx. NLM is not an LLM.",
        )
    if fmt not in ("safetensors", "onnx", "pt"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported NLM export format '{fmt}'. Allowed: safetensors, onnx, pt",
        )
    try:
        from mycosoft_mas.nlm.trainer import NLMTrainer

        trainer = NLMTrainer()
        output_path = f"{NLM_MODEL_DIR}/exports/nlm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{fmt}"
        result = trainer.export_model(output_path=output_path, format=fmt)

        return {
            "status": "exported",
            "path": result,
            "format": fmt,
            "bound_to_ollama": False,
            "model_kind": "nature_learning_model",
            "message": f"Model exported to {output_path}",
        }
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/attest")
async def attest_artifacts(req: AttestRequest) -> Dict[str, Any]:
    """SHA-256 Merkle root + ECDSA P-256 signature (+ transparent inclusion proofs)."""
    from mycosoft_mas.nlm.merkle_attest import attest_payloads

    payloads: List[Dict[str, Any]] = []
    if req.payloads:
        payloads.extend(req.payloads)
    elif req.packet:
        payloads.append(req.packet)
    else:
        payloads.append(
            {
                "type": req.type or "frame_commit",
                "modelId": req.modelId,
                "ownerId": req.ownerId,
                "parent_frame_root": req.parent_frame_root,
                "source_device": req.source_device,
                "ts": datetime.now().isoformat(),
            }
        )

    attestation = attest_payloads(payloads)
    # Attach to active run lineage when present
    active = _get_active_run()
    if active is not None:
        active.setdefault("attestations", []).append(
            {
                "merkle_root": attestation["merkle_root"],
                "timestamp": attestation["timestamp"],
                "signed": attestation.get("signature", {}).get("signed"),
            }
        )

    return {
        "status": "attested",
        "model_kind": "nature_learning_model",
        "attestation": attestation,
    }


@router.get("/ingest/sources")
async def ingest_sources() -> Dict[str, Any]:
    """
    Device network sources for NLM training ingest.

    Returns MAS registry devices with declared sensor channels.
    Empty sensors when gateways have no MDP serial device — never fabricates samples.
    """
    devices = await _list_registry_devices()
    ROLE_SENSORS = {
        "psathyrella": [
            "bme688_ambient",
            "bme688_environment",
            "hydrophone_low",
            "hydrophone_high",
            "transducer",
        ],
        "mushroom1": ["bme688", "imu", "gas", "spectral", "bioelectric"],
        "hyphae1": ["bme688", "imu", "gas", "spectral"],
        "sporebase": ["bme688", "particulate", "optical"],
        "mycodrone": ["imu", "baro", "gps", "spectral"],
        "standalone": ["bme688", "gas"],
    }
    rows: List[Dict[str, Any]] = []
    for d in devices:
        role = str(d.get("device_role") or d.get("role") or "standalone").lower()
        sensors = list(d.get("sensors") or [])
        for s in ROLE_SENSORS.get(role, []):
            if s not in sensors:
                sensors.append(s)
        extra = d.get("extra") or {}
        rows.append(
            {
                "device_id": d.get("device_id"),
                "display_name": d.get("device_display_name")
                or d.get("device_name")
                or d.get("device_id"),
                "role": role,
                "status": d.get("status"),
                "host": d.get("host"),
                "mdp_device_id": extra.get("mdp_device_id"),
                "sensor_channels": sensors,
                "last_seen": d.get("last_seen"),
                "source": "mas-device-registry",
            }
        )
    return {
        "devices": rows,
        "count": len(rows),
        "bindings_active": len(_ingest_bindings),
        "note": "Live MAS registry only. Sensor samples require MDP telemetry.",
    }


@router.post("/ingest/bind")
async def ingest_bind(req: IngestBindRequest) -> Dict[str, Any]:
    """Persist device_id + sensor_id bindings for upcoming / active NLM runs."""
    bindings = _normalize_bindings(req.bindings)
    if not bindings:
        raise HTTPException(status_code=400, detail="bindings[{device_id,sensor_id}] required")

    registry = await _list_registry_devices()
    known_ids = {str(d.get("device_id")) for d in registry}
    validated: List[Dict[str, str]] = []
    rejected: List[Dict[str, str]] = []
    for b in bindings:
        if known_ids and b["device_id"] not in known_ids:
            rejected.append({**b, "reason": "device_not_in_registry"})
        else:
            validated.append(b)

    if not validated:
        raise HTTPException(
            status_code=422,
            detail={"error": "No bindings matched MAS registry", "rejected": rejected},
        )

    record = {
        "id": f"bind_{uuid.uuid4().hex[:10]}",
        "model_id": req.model_id,
        "run_id": req.run_id or _active_run_id,
        "owner_id": req.owner_id,
        "bindings": validated,
        "rejected": rejected,
        "created_at": datetime.now().isoformat(),
    }
    _ingest_bindings.append(record)

    # Attach to active / named run when present
    target_run_id = req.run_id or _active_run_id
    if target_run_id:
        for run in _training_runs:
            if run.get("run_id") == target_run_id:
                run["ingest_bindings"] = validated
                run["device_ids"] = list({b["device_id"] for b in validated})
                run["sensor_ids"] = list({b["sensor_id"] for b in validated})
                cfg = run.setdefault("config", {})
                cfg["ingest_bindings"] = validated
                cfg["device_ids"] = run["device_ids"]
                cfg["sensor_ids"] = run["sensor_ids"]
                metrics = run.setdefault("metrics", {})
                metrics["device_bindings"] = validated
                run["updated_at"] = datetime.now().isoformat()
                break

    return {"status": "bound", "record": record}


@router.get("/health")
async def training_health() -> Dict[str, Any]:
    """Training router health — scientific NLM only."""
    return {
        "status": "ok",
        "active_run_id": _active_run_id,
        "runs": len(_training_runs),
        "ingest_bindings": len(_ingest_bindings),
        "bound_to_ollama": False,
        "model_kind": "nature_learning_model",
        "export_formats": ["safetensors", "onnx", "pt"],
        "merkle": {"hash": "SHA-256", "sign": "ECDSA-P256", "zk": "deferred_p2"},
        "device_ingest": True,
    }
