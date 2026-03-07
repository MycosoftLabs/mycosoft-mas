"""
Master Spreadsheet Sync API.

Triggers sync of inventory, hardware, and other tabs to the master Google Sheet.
Used by n8n workflows (scheduled + webhook) and Zapier for full automation.
Status is stored durably in Supabase sheet_sync_status and sync_runs.
Created: March 7, 2026
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/spreadsheet", tags=["spreadsheet-sync"])

# In-memory fallback when Supabase unavailable or no durable status yet
_last_sync: Dict[str, Any] = {}

# Master spreadsheet ID for status lookup
_MASTER_SPREADSHEET_ID = "1rhuGmyxZakCVet1zMK3_C2f3SCOzH_dr6HH6EKWGRmc"


async def _fetch_sheet_status_from_supabase() -> Optional[Dict[str, Any]]:
    """
    Fetch durable sync status from Supabase sheet_sync_status and sync_runs.
    Returns dict with last_run, success, tabs (per-tab status), error; or None if unavailable.
    """
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Latest sync runs for master spreadsheet
            r = await client.get(
                f"{url}/rest/v1/sync_runs",
                headers=headers,
                params={
                    "sync_type": "eq.sheet_tab",
                    "order": "started_at.desc",
                    "limit": 5,
                    "select": "id,target_system,status,records_synced,started_at,completed_at,error_message",
                },
            )
            if r.status_code != 200:
                return None
            runs = r.json() if r.text else []
            # Per-tab status
            s = await client.get(
                f"{url}/rest/v1/sheet_sync_status",
                headers=headers,
                params={
                    "spreadsheet_id": f"eq.{_MASTER_SPREADSHEET_ID}",
                    "order": "last_sync_at.desc",
                    "select": "tab_name,last_sync_at,sync_status,rows_synced,error_message",
                },
            )
            if s.status_code != 200:
                return None
            tabs_data = s.json() if s.text else []
        if not runs and not tabs_data:
            return None
        # Derive overall last_run and success from most recent run
        last_run = None
        success = False
        tabs: List[str] = []
        error: Optional[str] = None
        if runs:
            r0 = runs[0]
            last_run = r0.get("completed_at") or r0.get("started_at")
            success = r0.get("status") in ("success", "partial")
            tabs = [r.get("target_system", "") for r in runs if r.get("target_system")]
            if not success and r0.get("error_message"):
                error = r0.get("error_message")
        elif tabs_data:
            t0 = tabs_data[0]
            last_run = t0.get("last_sync_at")
            success = t0.get("sync_status") == "success"
            tabs = [t.get("tab_name", "") for t in tabs_data if t.get("tab_name")]
        return {
            "last_run": last_run,
            "success": success,
            "tabs": list(dict.fromkeys(tabs)) if tabs else None,
            "error": error,
            "per_tab": tabs_data,
        }
    except Exception as e:
        logger.debug("Supabase status fetch failed: %s", e)
        return None


def _get_mas_repo_root() -> Path:
    """Resolve MAS repo root."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent,
        Path("/home/mycosoft/mycosoft/mas"),
        Path(os.getcwd()),
    ]
    for p in candidates:
        if (p / "scripts").exists() and (p / "mycosoft_mas").exists():
            return p
    return Path(os.getcwd())


def _run_sync(tabs: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run sync_master_spreadsheet.py with --push."""
    root = _get_mas_repo_root()
    script = root / "scripts" / "sync_master_spreadsheet.py"
    if not script.exists():
        raise FileNotFoundError(f"Sync script not found: {script}")

    cmd = [os.environ.get("PYTHON_EXE", "python"), str(script), "--push"]
    if tabs:
        cmd.extend(["--tabs", ",".join(tabs)])

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        result = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Sync timed out after 120 seconds",
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }


class SyncTriggerResponse(BaseModel):
    """Response from sync trigger."""

    status: str = "success"
    message: str
    tabs_synced: Optional[List[str]] = None
    timestamp: str


class SyncStatusResponse(BaseModel):
    """Last sync status."""

    last_run: Optional[str] = None
    success: bool
    tabs: Optional[List[str]] = None
    error: Optional[str] = None


@router.post("/sync")
async def trigger_sync(
    tabs: Optional[str] = Query(None, description="Comma-separated tab names, e.g. inventory,hardware"),
):
    """
    Trigger master spreadsheet sync (fetches data and pushes to Google Sheets).
    Used by n8n scheduled workflow and Zapier.
    """
    tab_list = [t.strip() for t in tabs.split(",") if t.strip()] if tabs else None

    # Run sync in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run_sync, tab_list)

    now = datetime.now(timezone.utc).isoformat()
    _last_sync["last_run"] = now
    _last_sync["success"] = result["success"]
    _last_sync["tabs"] = tab_list
    _last_sync["stdout"] = result.get("stdout", "")
    _last_sync["stderr"] = result.get("stderr", "")

    if result["success"]:
        return SyncTriggerResponse(
            status="success",
            message="Spreadsheet sync completed",
            tabs_synced=tab_list,
            timestamp=now,
        )
    raise HTTPException(
        status_code=500,
        detail={
            "message": "Spreadsheet sync failed",
            "stderr": result.get("stderr", ""),
            "stdout": result.get("stdout", "")[:500],
        },
    )


@router.get("/status")
async def get_sync_status():
    """Return last sync status for monitoring. Prefers Supabase; falls back to in-memory."""
    durable = await _fetch_sheet_status_from_supabase()
    if durable:
        return SyncStatusResponse(
            last_run=durable.get("last_run"),
            success=durable.get("success", False),
            tabs=durable.get("tabs"),
            error=durable.get("error"),
        )
    if not _last_sync:
        return SyncStatusResponse(
            last_run=None,
            success=False,
            error="No sync has run yet",
        )
    return SyncStatusResponse(
        last_run=_last_sync.get("last_run"),
        success=_last_sync.get("success", False),
        tabs=_last_sync.get("tabs"),
        error=_last_sync.get("stderr") if not _last_sync.get("success") else None,
    )
