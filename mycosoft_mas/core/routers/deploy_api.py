"""
Deployment API for autonomous fix pipeline.

Provides programmatic triggers for deploying to Sandbox (website), MAS, and MINDEX.
Used by n8n autonomous-fix-pipeline and ErrorTriageService after code fixes.
Created: February 24, 2026
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deploy", tags=["deploy"])

# In-memory job status (for /status endpoint)
_deploy_jobs: Dict[str, Dict[str, Any]] = {}


class DeployTriggerRequest(BaseModel):
    """Request to trigger a deployment."""

    target: str = Field(..., description="mas | website | mindex")
    reason: Optional[str] = Field(None, description="e.g. autonomous_fix")
    error_id: Optional[str] = Field(None, description="From triage if fix-related")


class DeployTriggerResponse(BaseModel):
    """Response from deploy trigger."""

    job_id: str
    status: str = "queued"
    target: str
    message: str


class DeployStatusResponse(BaseModel):
    """Deploy job status."""

    job_id: str
    status: str  # queued, running, success, failed
    target: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None


def _get_mas_repo_root() -> Path:
    """Resolve MAS repo root (where deploy scripts live)."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent,
        Path("/home/mycosoft/mycosoft/mas"),
        Path(os.getcwd()),
    ]
    for p in candidates:
        if (p / "scripts").exists() and (p / "mycosoft_mas").exists():
            return p
    return Path(os.getcwd())


def _get_website_repo_root() -> Path:
    """Resolve website repo root (for sandbox deploy)."""
    mas_root = _get_mas_repo_root()
    # Website repo is often sibling to MAS
    sibling = mas_root.parent / "website"
    if (sibling / "package.json").exists():
        return sibling
    return (
        mas_root.parent / "WEBSITE" / "website"
        if (mas_root.parent / "WEBSITE").exists()
        else sibling
    )


async def _run_deploy_website(job_id: str) -> None:
    """Run website deploy to sandbox (VM 187)."""
    _deploy_jobs[job_id]["status"] = "running"
    _deploy_jobs[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()

    website_root = _get_website_repo_root()
    script = website_root / "_rebuild_sandbox.py"
    if not script.exists():
        _deploy_jobs[job_id]["status"] = "failed"
        _deploy_jobs[job_id]["error"] = f"Deploy script not found: {script}"
        _deploy_jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        return

    try:
        proc = await asyncio.create_subprocess_exec(
            "python",
            str(script),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(website_root),
            env=os.environ.copy(),
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode(errors="replace") if stdout else ""
        _deploy_jobs[job_id]["output"] = output[-4000:]  # Last 4k chars
        _deploy_jobs[job_id]["status"] = "success" if proc.returncode == 0 else "failed"
        if proc.returncode != 0:
            _deploy_jobs[job_id]["error"] = f"Script exited with {proc.returncode}"
    except Exception as e:
        _deploy_jobs[job_id]["status"] = "failed"
        _deploy_jobs[job_id]["error"] = str(e)
        logger.exception("Website deploy failed")

    _deploy_jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()


async def _run_deploy_mas(job_id: str) -> None:
    """Run MAS deploy to VM 188."""
    _deploy_jobs[job_id]["status"] = "running"
    _deploy_jobs[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()

    mas_root = _get_mas_repo_root()
    # Common deploy approach: SSH to 188, pull, rebuild container
    deploy_cmd = [
        "python",
        "-c",
        """
import os, sys, paramiko
from pathlib import Path
creds = Path('.credentials.local')
if creds.exists():
    for line in creds.read_text().splitlines():
        if line and '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()
pw = os.environ.get('VM_PASSWORD') or os.environ.get('VM_SSH_PASSWORD')
if not pw:
    print('No VM_PASSWORD'); sys.exit(1)
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.0.188', username='mycosoft', password=pw, timeout=30)
cmd = 'cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main && docker build -t mycosoft/mas-agent:latest --no-cache . 2>&1'
_, out, _ = c.exec_command(cmd, timeout=600)
print(out.read().decode(errors='replace'))
c.close()
""",
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *deploy_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(mas_root),
            env=os.environ.copy(),
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode(errors="replace") if stdout else ""
        _deploy_jobs[job_id]["output"] = output[-4000:]
        _deploy_jobs[job_id]["status"] = "success" if proc.returncode == 0 else "failed"
        if proc.returncode != 0:
            _deploy_jobs[job_id]["error"] = f"Deploy exited with {proc.returncode}"
    except Exception as e:
        _deploy_jobs[job_id]["status"] = "failed"
        _deploy_jobs[job_id]["error"] = str(e)
        logger.exception("MAS deploy failed")

    _deploy_jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()


async def _run_deploy_mindex(job_id: str) -> None:
    """Run MINDEX deploy to VM 189."""
    _deploy_jobs[job_id]["status"] = "running"
    _deploy_jobs[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()

    # MINDEX deploy: SSH to 189, docker compose rebuild
    _deploy_jobs[job_id]["status"] = "failed"
    _deploy_jobs[job_id]["error"] = "MINDEX deploy not yet implemented in deploy API"
    _deploy_jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()


@router.post("/trigger", response_model=DeployTriggerResponse)
async def trigger_deploy(
    req: DeployTriggerRequest,
    background_tasks: BackgroundTasks,
) -> DeployTriggerResponse:
    """
    Trigger a deployment to the specified target.
    Runs in background; poll /status/{job_id} for result.
    """
    if req.target not in ("mas", "website", "mindex"):
        raise HTTPException(400, f"Invalid target: {req.target}")

    job_id = str(uuid4())[:12]
    _deploy_jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "target": req.target,
        "reason": req.reason,
        "error_id": req.error_id,
        "started_at": None,
        "completed_at": None,
        "output": None,
        "error": None,
    }

    if req.target == "website":
        background_tasks.add_task(_run_deploy_website, job_id)
    elif req.target == "mas":
        background_tasks.add_task(_run_deploy_mas, job_id)
    else:
        background_tasks.add_task(_run_deploy_mindex, job_id)

    return DeployTriggerResponse(
        job_id=job_id,
        status="queued",
        target=req.target,
        message=f"Deploy to {req.target} queued. Poll /api/deploy/status/{job_id}",
    )


@router.post("/autonomous-fix")
async def receive_autonomous_fix(
    request: Request, background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Receive autonomous fix payload from n8n (triggered by ErrorTriageService).
    Logs the request and optionally triggers deploy.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    error_id = body.get("errorId", body.get("error_id", ""))
    data = body.get("data", body)
    deploy_target = data.get("deploy_target", "mas")

    logger.info(f"Autonomous fix received: error_id={error_id}, deploy_target={deploy_target}")

    # Optionally trigger deploy (code fix is assumed already pushed by Cursor/agent)
    job_id = None
    if deploy_target in ("mas", "website", "mindex"):
        job_id = str(uuid4())[:12]
        _deploy_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "target": deploy_target,
            "reason": "autonomous_fix",
            "error_id": error_id,
        }
        if deploy_target == "website":
            background_tasks.add_task(_run_deploy_website, job_id)
        elif deploy_target == "mas":
            background_tasks.add_task(_run_deploy_mas, job_id)
        else:
            background_tasks.add_task(_run_deploy_mindex, job_id)

    return {
        "status": "received",
        "error_id": error_id,
        "deploy_target": deploy_target,
        "deploy_job_id": job_id,
    }


@router.get("/status/{job_id}", response_model=DeployStatusResponse)
async def get_deploy_status(job_id: str) -> DeployStatusResponse:
    """Get status of a deploy job."""
    if job_id not in _deploy_jobs:
        raise HTTPException(404, f"Job {job_id} not found")

    j = _deploy_jobs[job_id]
    return DeployStatusResponse(
        job_id=j["job_id"],
        status=j["status"],
        target=j["target"],
        started_at=j.get("started_at"),
        completed_at=j.get("completed_at"),
        output=j.get("output"),
        error=j.get("error"),
    )
