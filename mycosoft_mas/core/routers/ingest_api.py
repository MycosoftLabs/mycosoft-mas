"""
External Ingestion API.

Triggers ingest of Asana, Notion, GitHub into Supabase backbone tables.
Used by n8n workflows before sheet sync so canonical data is fresh.
Created: March 7, 2026
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


def _get_mas_repo_root() -> Path:
    """Resolve MAS repo root."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent,
        Path("/home/mycosoft/mycosoft/mas"),
        Path(os.getcwd()),
    ]
    for p in candidates:
        if (p / "scripts").exists() and (p / "scripts" / "ingest_external_to_supabase.py").exists():
            return p
    return Path(os.getcwd())


def _run_ingest(sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run ingest_external_to_supabase.py."""
    root = _get_mas_repo_root()
    script = root / "scripts" / "ingest_external_to_supabase.py"
    if not script.exists():
        return {"success": False, "returncode": -1, "stdout": "", "stderr": f"Script not found: {script}"}

    cmd = [os.environ.get("PYTHON_EXE", "python"), str(script)]
    if sources:
        cmd.extend(["--sources", ",".join(sources)])

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        result = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=180, env=env)
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": "Ingest timed out after 180 seconds"}
    except Exception as e:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": str(e)}


class IngestResponse(BaseModel):
    """Response from ingest trigger."""

    status: str
    message: str
    sources: Optional[List[str]] = None
    timestamp: str
    returncode: Optional[int] = None
    stdout_tail: Optional[str] = None


@router.post("/external")
async def trigger_ingest(
    sources: Optional[str] = Query(
        default="asana,notion,github",
        description="Comma-separated: asana,notion,github",
    ),
):
    """
    Trigger external system ingestion into Supabase.
    Pulls Asana tasks, Notion pages, GitHub issues into commitments, customer_vendors, etc.
    Used by n8n before sheet sync.
    """
    source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else ["asana", "notion", "github"]

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: _run_ingest(source_list))

    now = datetime.now(timezone.utc).isoformat()
    stdout_tail = (result.get("stdout") or "")[-500:] if result.get("stdout") else None
    if result["success"]:
        return IngestResponse(
            status="success",
            message="External ingestion completed",
            sources=source_list,
            timestamp=now,
            returncode=result.get("returncode"),
            stdout_tail=stdout_tail,
        )
    return IngestResponse(
        status="error",
        message=(result.get("stderr") or "Ingest failed")[:500],
        sources=source_list,
        timestamp=now,
        returncode=result.get("returncode"),
        stdout_tail=stdout_tail,
    )
