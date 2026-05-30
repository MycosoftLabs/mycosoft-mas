"""MAS firmware flash API — routes flash jobs to per-host executors (Phase 0 COM4, Phase 1 Hyphae Pi)."""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.core.routers import device_registry_api as registry

logger = logging.getLogger("FirmwareFlash")

router = APIRouter(prefix="/api/devices", tags=["firmware"])

REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_LOG = REPO_ROOT / "data" / "mas_firmware_flash_jobs.jsonl"

HYPHAE_DEVICE_ID = "mycobrain-hyphae1-jetson-228"
MUSHROOM_DEVICE_ID = "mycobrain-mushroom1-jetson-123"
HYPHAE_HOST = os.getenv("HYPHAE_PI_HOST", "192.168.0.228")
OPENCLAW_FLASH_PATH = os.getenv("HYPHAE_OPENCLAW_FLASH_URL", f"http://{HYPHAE_HOST}:18789/flash/jobs")

_mas_jobs: Dict[str, Dict[str, Any]] = {}


class FirmwareFlashRequest(BaseModel):
    firmware_version: Optional[str] = Field(None, description="Manifest version or local artifact name")
    profile: Optional[str] = Field(None, description="Role profile: mushroom1, hyphae1, standalone, etc.")
    artifact_url: Optional[str] = None
    artifact_path: Optional[str] = None
    confirm: bool = Field(False, description="Required for destructive flash")
    dry_run: bool = Field(True, description="Validate only — default true")
    idempotency_key: Optional[str] = None
    sha256: Optional[str] = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_audit(entry: Dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")


def _device_base_url(device: Dict[str, Any]) -> str:
    host = device.get("host", "")
    port = int(device.get("port") or 8003)
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    return f"http://{host}:{port}"


def _resolve_profile(device: Dict[str, Any], req: FirmwareFlashRequest) -> str:
    if req.profile:
        return req.profile.strip()
    role = (device.get("device_role") or "standalone").strip()
    return role or "standalone"


def _is_mushroom_protected(device_id: str) -> bool:
    return device_id == MUSHROOM_DEVICE_ID or "mushroom1" in device_id.lower()


async def _relay_openclaw_flash(body: FirmwareFlashRequest, profile: str) -> Dict[str, Any]:
    payload = {
        "profile": profile,
        "version": body.firmware_version,
        "confirm": body.confirm,
        "dry_run": body.dry_run,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(OPENCLAW_FLASH_PATH, json=payload)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text[:500])
        return r.json()


async def _relay_ssh_pi_flash(body: FirmwareFlashRequest, profile: str, job: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback: run pi_flash_sidecar on Hyphae Pi via SSH."""
    import subprocess

    version = body.firmware_version or "side-a-mdp-2.1.0"
    artifact = REPO_ROOT / "data" / "firmware_artifacts" / version / f"{version}_{profile}_merged.bin"
    if not artifact.is_file():
        raise HTTPException(status_code=404, detail=f"Hyphae artifact not found: {artifact}")

    script = REPO_ROOT / "scripts" / "hyphae_pi_flash.py"
    cmd = [sys.executable, str(script), "--host", HYPHAE_HOST, "--artifact", str(artifact)]
    if body.dry_run:
        cmd.append("--dry-run")
    if body.confirm:
        cmd.append("--confirm")
    env = os.environ.copy()
    if body.confirm:
        env["APPROVE_FLASH"] = "true"
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
    job["ssh_exit_code"] = proc.returncode
    job["ssh_stdout"] = (proc.stdout or "")[-3000:]
    job["ssh_stderr"] = (proc.stderr or "")[-1000:]
    if proc.returncode != 0:
        job["state"] = "failed"
        job["error"] = job["ssh_stderr"] or job["ssh_stdout"] or f"ssh flash exit {proc.returncode}"
        return job
    try:
        # hyphae_pi_flash prints SSH wrapper JSON; parse inner stdout if nested
        outer = json.loads(proc.stdout)
        inner = outer.get("stdout", proc.stdout)
        parsed = json.loads(inner) if isinstance(inner, str) and inner.strip().startswith("{") else outer
        job["host_result"] = parsed
        job["state"] = parsed.get("state", "success")
    except json.JSONDecodeError:
        job["state"] = "success" if proc.returncode == 0 else "failed"
    return job


@router.get("/firmware/health")
async def firmware_health():
    return {
        "status": "ok",
        "service": "firmware-flash-api",
        "phase": "0-com4-host-flash,1-hyphae-pi-ssh",
        "approve_flash_env": os.getenv("APPROVE_FLASH", ""),
        "timestamp": _utc_now(),
    }


@router.post("/{device_id}/firmware/flash")
async def start_firmware_flash(device_id: str, body: FirmwareFlashRequest):
    """Create a firmware flash job. COM4 → local :8003; Hyphae Pi → OpenClaw or SSH sidecar."""
    registry._cleanup_expired_devices()

    if _is_mushroom_protected(device_id):
        raise HTTPException(
            status_code=403,
            detail=f"Flash blocked: {device_id} is protected (live demo). Use Hyphae or COM4 bench only.",
        )

    if device_id not in registry._device_registry:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    device = registry._device_registry[device_id]
    status = registry._get_device_status(device_id)
    if status == "offline":
        raise HTTPException(status_code=503, detail=f"Device {device_id} is offline")

    idem = body.idempotency_key or f"{device_id}:{body.firmware_version or 'unknown'}:{body.dry_run}"
    for existing in _mas_jobs.values():
        if existing.get("idempotency_key") == idem and existing.get("device_id") == device_id:
            return existing

    profile = _resolve_profile(device, body)
    job_id = f"mas-flash-{uuid.uuid4().hex[:12]}"
    job: Dict[str, Any] = {
        "job_id": job_id,
        "device_id": device_id,
        "state": "requested",
        "profile": profile,
        "firmware_version": body.firmware_version,
        "dry_run": body.dry_run,
        "confirm": body.confirm,
        "idempotency_key": idem,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }

    if not body.confirm and not body.dry_run:
        job["state"] = "approval_required"
        job["message"] = "Set confirm=true for destructive flash"
        _mas_jobs[job_id] = job
        _append_audit(job)
        return job

    # Phase 1: Hyphae Raspberry Pi only
    if device_id == HYPHAE_DEVICE_ID:
        job["relay"] = HYPHAE_HOST
        try:
            try:
                host_result = await _relay_openclaw_flash(body, profile)
                job["relay_mode"] = "openclaw"
            except Exception as openclaw_exc:
                logger.warning("OpenClaw flash unavailable (%s); falling back to SSH sidecar", openclaw_exc)
                job["relay_mode"] = "ssh_sidecar"
                job["openclaw_error"] = str(openclaw_exc)
                await _relay_ssh_pi_flash(body, profile, job)
                _mas_jobs[job_id] = job
                _append_audit(job)
                job["updated_at"] = _utc_now()
                return job
            job["state"] = host_result.get("state", "unknown")
            job["host_result"] = host_result
        except HTTPException:
            raise
        except Exception as exc:
            job["state"] = "failed"
            job["error"] = str(exc)
            _mas_jobs[job_id] = job
            _append_audit(job)
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        job["updated_at"] = _utc_now()
        _mas_jobs[job_id] = job
        _append_audit(job)
        return job

    # Phase 0: local MycoBrain service on host :8003
    host_port = int(device.get("port") or 8003)
    is_local_mycobrain = (
        device_id.startswith("mycobrain-COM")
        or device_id.startswith("mycobrain-tty")
        or (host_port == 8003 and not registry._is_agent_api(device))
    )

    if not is_local_mycobrain:
        job["state"] = "failed"
        job["error"] = f"Unsupported flash target {device_id}; allowed: COM4 bench, {HYPHAE_DEVICE_ID}"
        _append_audit(job)
        _mas_jobs[job_id] = job
        raise HTTPException(status_code=501, detail=job["error"])

    base_url = _device_base_url(device)
    port_name = device.get("extra", {}).get("port_name") or device_id.replace("mycobrain-", "").replace("-", "/")
    if port_name.startswith("COM-"):
        port_name = port_name.replace("COM-", "COM")

    payload = {
        "profile": profile,
        "version": body.firmware_version,
        "artifact_url": body.artifact_url,
        "artifact_path": body.artifact_path,
        "port": port_name if "COM" in port_name.upper() or "tty" in port_name.lower() else None,
        "confirm": body.confirm,
        "dry_run": body.dry_run,
        "sha256": body.sha256,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{base_url}/flash", json=payload)
            if r.status_code >= 400:
                job["state"] = "failed"
                job["error"] = r.text[:500]
                _mas_jobs[job_id] = job
                _append_audit(job)
                raise HTTPException(status_code=r.status_code, detail=job["error"])
            host_result = r.json()
    except HTTPException:
        raise
    except Exception as exc:
        job["state"] = "failed"
        job["error"] = str(exc)
        _mas_jobs[job_id] = job
        _append_audit(job)
        raise HTTPException(status_code=503, detail=f"MycoBrain flash service unreachable: {exc}") from exc

    job["state"] = host_result.get("state", "unknown")
    job["host_job_id"] = host_result.get("job_id")
    job["host_result"] = host_result
    job["relay"] = base_url
    job["updated_at"] = _utc_now()
    _mas_jobs[job_id] = job
    _append_audit(job)
    return job


@router.get("/{device_id}/firmware/jobs")
async def list_firmware_jobs(device_id: str):
    items = [j for j in _mas_jobs.values() if j.get("device_id") == device_id]
    items.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return {"device_id": device_id, "jobs": items, "count": len(items), "timestamp": _utc_now()}


@router.get("/{device_id}/firmware/jobs/{job_id}")
async def get_firmware_job(device_id: str, job_id: str):
    job = _mas_jobs.get(job_id)
    if not job or job.get("device_id") != device_id:
        raise HTTPException(status_code=404, detail="job_not_found")
    host_job_id = job.get("host_job_id")
    if host_job_id and job.get("relay"):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(f"{job['relay']}/flash/jobs/{host_job_id}")
                if r.status_code == 200:
                    job = {**job, "host_live": r.json(), "updated_at": _utc_now()}
        except Exception as exc:
            job["host_poll_error"] = str(exc)
    return job
