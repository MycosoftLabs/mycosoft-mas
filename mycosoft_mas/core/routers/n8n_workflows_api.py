"""
N8N Workflow Management API Router - January 25, 2026

FastAPI router for MYCA to manage n8n workflows via REST API.
This is the interface for the orchestrator to control workflows 24/7/365.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from mycosoft_mas.core.n8n_workflow_engine import (
    N8NWorkflowEngine,
    WorkflowScheduler,
    SyncResult,
    WorkflowInfo,
    WorkflowCategory,
    get_engine,
    get_scheduler
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["n8n-workflows"])

# Global instances
_engine: Optional[N8NWorkflowEngine] = None
_scheduler: Optional[WorkflowScheduler] = None


def get_workflow_engine() -> N8NWorkflowEngine:
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


def get_workflow_scheduler() -> WorkflowScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = get_scheduler()
    return _scheduler


# Pydantic Models
class WorkflowCreateRequest(BaseModel):
    name: str
    nodes: List[Dict[str, Any]] = []
    connections: Dict[str, Any] = {}
    settings: Dict[str, Any] = {}
    active: bool = False


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    connections: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None


class WorkflowImportRequest(BaseModel):
    filepath: str
    activate: bool = False


class WorkflowCloneRequest(BaseModel):
    new_name: str


class SyncRequest(BaseModel):
    activate_core: bool = True


class SchedulerConfig(BaseModel):
    sync_interval: int = 15
    health_interval: int = 5
    archive_interval: int = 24


# ==================== Workflow CRUD ====================

@router.get("/health")
async def workflow_health():
    """Check n8n connection health"""
    engine = get_workflow_engine()
    return engine.health_check()


@router.get("/stats")
async def workflow_stats():
    """Get workflow statistics"""
    engine = get_workflow_engine()
    return engine.get_workflow_stats()


@router.get("/list")
async def list_workflows(
    active_only: bool = False,
    category: Optional[str] = None
):
    """List all workflows"""
    engine = get_workflow_engine()
    cat = WorkflowCategory(category) if category else None
    workflows = engine.list_workflows(active_only=active_only, category=cat)
    return {"workflows": [w.to_dict() for w in workflows], "count": len(workflows)}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get a specific workflow"""
    engine = get_workflow_engine()
    try:
        workflow = engine.get_workflow(workflow_id)
        return workflow
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/by-name/{name}")
async def get_workflow_by_name(name: str):
    """Get workflow by name"""
    engine = get_workflow_engine()
    workflow = engine.get_workflow_by_name(name)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
    return workflow


@router.post("/create")
async def create_workflow(request: WorkflowCreateRequest):
    """Create a new workflow"""
    engine = get_workflow_engine()
    try:
        result = engine.create_workflow(request.dict())
        return {"status": "created", "workflow": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, request: WorkflowUpdateRequest):
    """Update a workflow"""
    engine = get_workflow_engine()
    try:
        data = {k: v for k, v in request.dict().items() if v is not None}
        result = engine.update_workflow(workflow_id, data)
        return {"status": "updated", "workflow": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str, archive_first: bool = True):
    """Delete a workflow"""
    engine = get_workflow_engine()
    try:
        engine.delete_workflow(workflow_id, archive_first=archive_first)
        return {"status": "deleted", "workflow_id": workflow_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Activation ====================

@router.post("/{workflow_id}/activate")
async def activate_workflow(workflow_id: str):
    """Activate a workflow"""
    engine = get_workflow_engine()
    try:
        result = engine.activate_workflow(workflow_id)
        return {"status": "activated", "workflow": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workflow_id}/deactivate")
async def deactivate_workflow(workflow_id: str):
    """Deactivate a workflow"""
    engine = get_workflow_engine()
    try:
        result = engine.deactivate_workflow(workflow_id)
        return {"status": "deactivated", "workflow": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Archiving & Versioning ====================

@router.post("/{workflow_id}/archive")
async def archive_workflow(workflow_id: str, reason: str = "manual"):
    """Archive a workflow version"""
    engine = get_workflow_engine()
    try:
        version = engine.archive_workflow(workflow_id, reason=reason)
        return {"status": "archived", "version": version.version, "file": version.file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workflow_id}/versions")
async def list_versions(workflow_id: str):
    """List archived versions of a workflow"""
    engine = get_workflow_engine()
    versions = engine.list_versions(workflow_id)
    return {"versions": [{"version": v.version, "archived_at": v.archived_at, "reason": v.reason} for v in versions]}


@router.post("/{workflow_id}/restore")
async def restore_workflow(workflow_id: str, version: Optional[int] = None):
    """Restore a workflow from archive"""
    engine = get_workflow_engine()
    try:
        result = engine.restore_workflow(workflow_id, version=version)
        return {"status": "restored", "workflow": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Import/Export & Sync ====================

@router.post("/sync")
async def sync_workflows(request: SyncRequest, background_tasks: BackgroundTasks):
    """Sync all local workflows to n8n"""
    engine = get_workflow_engine()
    result = engine.sync_all_local_workflows(activate_core=request.activate_core)
    return {"status": "synced", "result": result.to_dict()}


@router.post("/export-all")
async def export_all_workflows():
    """Export all workflows from n8n to local files"""
    engine = get_workflow_engine()
    try:
        paths = engine.export_all_workflows()
        return {"status": "exported", "count": len(paths), "files": [str(p) for p in paths]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workflow_id}/export")
async def export_workflow(workflow_id: str):
    """Export a single workflow to local file"""
    engine = get_workflow_engine()
    try:
        path = engine.export_workflow(workflow_id)
        return {"status": "exported", "file": str(path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workflow_id}/clone")
async def clone_workflow(workflow_id: str, request: WorkflowCloneRequest):
    """Clone a workflow with a new name"""
    engine = get_workflow_engine()
    try:
        result = engine.clone_workflow(workflow_id, request.new_name)
        return {"status": "cloned", "workflow": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Executions ====================

@router.get("/executions/list")
async def list_executions(
    workflow_id: Optional[str] = None,
    limit: int = 50,
    status: Optional[str] = None
):
    """List workflow executions"""
    engine = get_workflow_engine()
    executions = engine.get_executions(workflow_id=workflow_id, limit=limit, status=status)
    return {"executions": executions, "count": len(executions)}


@router.get("/executions/failed")
async def get_failed_executions(hours: int = 24):
    """Get failed executions in last N hours"""
    engine = get_workflow_engine()
    failed = engine.get_failed_executions(hours=hours)
    return {"failed": failed, "count": len(failed)}


@router.get("/{workflow_id}/stats")
async def get_execution_stats(workflow_id: str):
    """Get execution statistics for a workflow"""
    engine = get_workflow_engine()
    try:
        stats = engine.get_execution_stats(workflow_id)
        return {
            "workflow_id": stats.workflow_id,
            "workflow_name": stats.workflow_name,
            "total_executions": stats.total_executions,
            "success_count": stats.success_count,
            "failure_count": stats.failure_count,
            "last_execution": stats.last_execution,
            "last_status": stats.last_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Scheduler Control ====================

@router.post("/scheduler/start")
async def start_scheduler(config: SchedulerConfig, background_tasks: BackgroundTasks):
    """Start the 24/7 workflow scheduler"""
    scheduler = get_workflow_scheduler()
    background_tasks.add_task(
        scheduler.start,
        sync_interval=config.sync_interval,
        health_interval=config.health_interval,
        archive_interval=config.archive_interval
    )
    return {"status": "starting", "config": config.dict()}


@router.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the workflow scheduler"""
    scheduler = get_workflow_scheduler()
    await scheduler.stop()
    return {"status": "stopped"}


@router.get("/scheduler/status")
async def scheduler_status():
    """Get scheduler status"""
    scheduler = get_workflow_scheduler()
    return {
        "running": scheduler._running,
        "tasks_count": len(scheduler._tasks)
    }
