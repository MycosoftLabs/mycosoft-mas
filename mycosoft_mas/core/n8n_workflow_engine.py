"""
N8N Workflow Management Engine - January 25, 2026

Core automation engine for MYCA orchestrator to manage n8n workflows 24/7/365.
"""

import os
import json
import logging
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import httpx

logger = logging.getLogger(__name__)

# Configuration
N8N_URL = os.getenv("N8N_URL", "http://192.168.0.188:5678")
N8N_CLOUD_URL = os.getenv("N8N_CLOUD_URL", "https://mycosoft.app.n8n.cloud")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
N8N_CLOUD_API_KEY = os.getenv("N8N_CLOUD_API_KEY", "")

BASE_DIR = Path(__file__).parent.parent.parent
WORKFLOWS_DIR = BASE_DIR / "n8n" / "workflows"
ARCHIVE_DIR = BASE_DIR / "n8n" / "archive"
TEMPLATES_DIR = BASE_DIR / "n8n" / "templates"
REGISTRY_DIR = BASE_DIR / "n8n" / "registry"
BACKUP_DIR = BASE_DIR / "n8n" / "backup"

for d in [WORKFLOWS_DIR, ARCHIVE_DIR, TEMPLATES_DIR, REGISTRY_DIR, BACKUP_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class WorkflowStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    DRAFT = "draft"
    ERROR = "error"


class WorkflowCategory(Enum):
    CORE = "core"
    NATIVE = "native"
    OPS = "ops"
    SPEECH = "speech"
    CUSTOM = "custom"
    TEMPLATE = "template"


@dataclass
class WorkflowInfo:
    id: str
    name: str
    active: bool
    created_at: str
    updated_at: str
    nodes_count: int = 0
    tags: List[str] = field(default_factory=list)
    local_file: Optional[str] = None
    checksum: Optional[str] = None
    category: WorkflowCategory = WorkflowCategory.CUSTOM
    version: int = 1
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        return d


@dataclass
class WorkflowVersion:
    workflow_id: str
    workflow_name: str
    version: int
    archived_at: str
    checksum: str
    file_path: str
    reason: str = ""


@dataclass
class SyncResult:
    imported: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    activated: List[str] = field(default_factory=list)
    deactivated: List[str] = field(default_factory=list)
    archived: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionStats:
    workflow_id: str
    workflow_name: str
    total_executions: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_duration_ms: float = 0.0
    last_execution: Optional[str] = None
    last_status: Optional[str] = None


def clean_workflow_for_api(workflow_data: dict, for_update: bool = False) -> dict:
    """Clean workflow data to only include fields accepted by n8n API.
    
    Args:
        workflow_data: Raw workflow data from file or n8n
        for_update: If True, only include fields valid for PUT request
    """
    # Fields allowed for create/update
    allowed = {"name", "nodes", "connections", "settings", "staticData"}
    
    cleaned = {}
    for key in allowed:
        if key in workflow_data:
            cleaned[key] = workflow_data[key]
    
    # Ensure required fields
    if "name" not in cleaned or not cleaned["name"]:
        cleaned["name"] = "Unnamed Workflow"
    if "nodes" not in cleaned:
        cleaned["nodes"] = []
    if "connections" not in cleaned:
        cleaned["connections"] = {}
    if "settings" not in cleaned:
        cleaned["settings"] = {}
    
    return cleaned


class N8NWorkflowEngine:
    """N8N Workflow Management Engine for MYCA 24/7/365 automation"""
    
    def __init__(self, base_url: str = None, api_key: str = None, use_cloud: bool = False):
        if use_cloud:
            self.base_url = (base_url or N8N_CLOUD_URL).rstrip("/")
            self.api_key = api_key or N8N_CLOUD_API_KEY
        else:
            self.base_url = (base_url or N8N_URL).rstrip("/")
            self.api_key = api_key or N8N_API_KEY
        
        self.headers = {"X-N8N-API-KEY": self.api_key, "Content-Type": "application/json"}
        self.client = httpx.Client(timeout=60.0)
        self._version_registry: Dict[str, List[WorkflowVersion]] = {}
        self._load_version_registry()
        
    def _load_version_registry(self):
        registry_file = REGISTRY_DIR / "versions.json"
        if registry_file.exists():
            try:
                with open(registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for wf_id, versions in data.items():
                        self._version_registry[wf_id] = [WorkflowVersion(**v) for v in versions]
            except Exception as e:
                logger.error(f"Failed to load version registry: {e}")
    
    def _save_version_registry(self):
        registry_file = REGISTRY_DIR / "versions.json"
        try:
            data = {wf_id: [asdict(v) for v in versions] for wf_id, versions in self._version_registry.items()}
            with open(registry_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save version registry: {e}")
        
    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self.base_url}/api/v1{endpoint}"
        try:
            response = self.client.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.text else {}
        except httpx.HTTPStatusError as e:
            logger.error(f"N8N API error: {e.response.status_code} - {e.response.text[:500]}")
            raise
        except Exception as e:
            logger.error(f"N8N request failed: {e}")
            raise
    
    def _compute_checksum(self, data: dict) -> str:
        content = json.dumps(data, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _categorize_workflow(self, name: str, filename: str = "") -> WorkflowCategory:
        lower_name = (name + filename).lower()
        if any(x in lower_name for x in ["01_", "02_", "myca-", "command_api"]):
            return WorkflowCategory.CORE
        if any(x in lower_name for x in ["native_", "native-"]):
            return WorkflowCategory.NATIVE
        if any(x in lower_name for x in ["ops_", "ops-", "proxmox", "unifi", "nas", "gpu", "uart"]):
            return WorkflowCategory.OPS
        if any(x in lower_name for x in ["speech", "voice", "audio", "tts", "transcribe"]):
            return WorkflowCategory.SPEECH
        if any(x in lower_name for x in ["template", "base_"]):
            return WorkflowCategory.TEMPLATE
        return WorkflowCategory.CUSTOM

    def list_workflows(self, active_only: bool = False, category: WorkflowCategory = None) -> List[WorkflowInfo]:
        data = self._request("GET", "/workflows")
        workflows = []
        for w in data.get("data", []):
            if active_only and not w.get("active"):
                continue
            wf_category = self._categorize_workflow(w["name"])
            if category and wf_category != category:
                continue
            workflows.append(WorkflowInfo(
                id=w["id"], name=w["name"], active=w.get("active", False),
                created_at=w.get("createdAt", ""), updated_at=w.get("updatedAt", ""),
                nodes_count=len(w.get("nodes", [])), tags=[t["name"] for t in w.get("tags", [])],
                category=wf_category
            ))
        return workflows
    
    def get_workflow(self, workflow_id: str) -> dict:
        return self._request("GET", f"/workflows/{workflow_id}")
    
    def get_workflow_by_name(self, name: str) -> Optional[dict]:
        workflows = self._request("GET", "/workflows")
        for w in workflows.get("data", []):
            if w["name"] == name:
                return self.get_workflow(w["id"])
        return None
    
    def create_workflow(self, workflow_data: dict) -> dict:
        cleaned = clean_workflow_for_api(workflow_data)
        result = self._request("POST", "/workflows", json=cleaned)
        logger.info(f"Created workflow: {cleaned.get('name', 'unknown')}")
        return result
    
    def update_workflow(self, workflow_id: str, workflow_data: dict) -> dict:
        cleaned = clean_workflow_for_api(workflow_data, for_update=True)
        result = self._request("PUT", f"/workflows/{workflow_id}", json=cleaned)
        logger.info(f"Updated workflow {workflow_id}")
        return result
    
    def delete_workflow(self, workflow_id: str, archive_first: bool = True) -> bool:
        if archive_first:
            try:
                current = self.get_workflow(workflow_id)
                self.archive_workflow(workflow_id, current, reason="pre-delete backup")
            except Exception as e:
                logger.warning(f"Could not archive before delete: {e}")
        self._request("DELETE", f"/workflows/{workflow_id}")
        logger.info(f"Deleted workflow: {workflow_id}")
        return True
    
    def activate_workflow(self, workflow_id: str) -> dict:
        result = self._request("POST", f"/workflows/{workflow_id}/activate")
        logger.info(f"Activated workflow: {workflow_id}")
        return result
    
    def deactivate_workflow(self, workflow_id: str) -> dict:
        result = self._request("POST", f"/workflows/{workflow_id}/deactivate")
        logger.info(f"Deactivated workflow: {workflow_id}")
        return result
    
    def archive_workflow(self, workflow_id: str, workflow_data: dict = None, reason: str = "") -> WorkflowVersion:
        if not workflow_data:
            workflow_data = self.get_workflow(workflow_id)
        if workflow_id not in self._version_registry:
            self._version_registry[workflow_id] = []
        version = len(self._version_registry[workflow_id]) + 1
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{workflow_data['name']}__v{version}__{timestamp}.json"
        safe_filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        archive_path = ARCHIVE_DIR / safe_filename
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(workflow_data, f, indent=2)
        version_record = WorkflowVersion(
            workflow_id=workflow_id, workflow_name=workflow_data["name"], version=version,
            archived_at=datetime.utcnow().isoformat(), checksum=self._compute_checksum(workflow_data),
            file_path=str(archive_path), reason=reason
        )
        self._version_registry[workflow_id].append(version_record)
        self._save_version_registry()
        logger.info(f"Archived workflow {workflow_data['name']} v{version}")
        return version_record
    
    def restore_workflow(self, workflow_id: str, version: int = None) -> dict:
        if workflow_id not in self._version_registry:
            raise ValueError(f"No archived versions for workflow {workflow_id}")
        versions = self._version_registry[workflow_id]
        if not versions:
            raise ValueError(f"No archived versions for workflow {workflow_id}")
        if version:
            target = next((v for v in versions if v.version == version), None)
            if not target:
                raise ValueError(f"Version {version} not found")
        else:
            target = versions[-1]
        with open(target.file_path, "r", encoding="utf-8") as f:
            workflow_data = json.load(f)
        result = self.update_workflow(workflow_id, workflow_data)
        logger.info(f"Restored workflow {target.workflow_name} from v{target.version}")
        return result
    
    def list_versions(self, workflow_id: str) -> List[WorkflowVersion]:
        return self._version_registry.get(workflow_id, [])
    
    def export_workflow(self, workflow_id: str, filepath: Path = None) -> Path:
        workflow = self.get_workflow(workflow_id)
        if not filepath:
            safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in workflow["name"])
            filepath = BACKUP_DIR / f"{safe_name}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(workflow, f, indent=2)
        logger.info(f"Exported workflow to {filepath}")
        return filepath
    
    def export_all_workflows(self, output_dir: Path = None) -> List[Path]:
        output_dir = output_dir or BACKUP_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        exported = []
        for wf in self.list_workflows():
            try:
                path = self.export_workflow(wf.id, output_dir / f"{wf.name}.json")
                exported.append(path)
            except Exception as e:
                logger.error(f"Failed to export {wf.name}: {e}")
        return exported
    
    def import_workflow_from_file(self, filepath: Path, activate: bool = False) -> dict:
        with open(filepath, "r", encoding="utf-8") as f:
            workflow_data = json.load(f)
        
        name = workflow_data.get("name", "")
        if not name:
            logger.warning(f"Skipping {filepath.name}: no workflow name")
            return {"skipped": True, "reason": "no name"}
        
        existing = self.get_workflow_by_name(name)
        
        if existing:
            # Workflow exists - skip update for now (n8n already has it)
            # The workflows are already in n8n, no need to push local changes
            logger.debug(f"Workflow exists in n8n: {name}")
            result = existing
            
            if activate and result.get("id") and not result.get("active"):
                try:
                    self.activate_workflow(result["id"])
                    result["active"] = True
                except Exception as e:
                    logger.warning(f"Could not activate {name}: {e}")
        else:
            # New workflow - create it
            result = self.create_workflow(workflow_data)
            logger.info(f"Created workflow: {name}")
            
            if activate and result.get("id"):
                try:
                    self.activate_workflow(result["id"])
                    result["active"] = True
                except Exception as e:
                    logger.warning(f"Could not activate {name}: {e}")
        
        return result
    
    def sync_all_local_workflows(self, activate_core: bool = True, force_update: bool = False) -> SyncResult:
        result = SyncResult()
        if not WORKFLOWS_DIR.exists():
            logger.warning(f"Workflows directory not found: {WORKFLOWS_DIR}")
            return result
        
        workflow_files = list(WORKFLOWS_DIR.glob("**/*.json"))
        
        for filepath in sorted(workflow_files):
            try:
                is_core = filepath.name.startswith(("01_", "02_", "myca-"))
                should_activate = activate_core and is_core
                
                imported = self.import_workflow_from_file(filepath, activate=should_activate)
                
                if imported.get("skipped"):
                    result.skipped.append(filepath.name)
                elif imported.get("id"):
                    result.imported.append(filepath.name)
                    if should_activate and imported.get("active"):
                        result.activated.append(filepath.name)
                        
            except Exception as e:
                logger.error(f"Failed to import {filepath.name}: {e}")
                result.errors.append({"file": filepath.name, "error": str(e)})
        
        logger.info(f"Sync complete: {len(result.imported)} imported, {len(result.skipped)} skipped, {len(result.activated)} activated, {len(result.errors)} errors")
        return result
    
    def get_executions(self, workflow_id: str = None, limit: int = 50, status: str = None) -> List[dict]:
        params = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status
        data = self._request("GET", "/executions", params=params)
        return data.get("data", [])
    
    def get_execution_stats(self, workflow_id: str) -> ExecutionStats:
        executions = self.get_executions(workflow_id, limit=100)
        if not executions:
            wf = self.get_workflow(workflow_id)
            return ExecutionStats(workflow_id=workflow_id, workflow_name=wf.get("name", ""))
        success_count = sum(1 for e in executions if e.get("status") == "success")
        failure_count = sum(1 for e in executions if e.get("status") in ["error", "failed"])
        latest = executions[0] if executions else {}
        return ExecutionStats(
            workflow_id=workflow_id, workflow_name=latest.get("workflowName", ""),
            total_executions=len(executions), success_count=success_count, failure_count=failure_count,
            last_execution=latest.get("startedAt"), last_status=latest.get("status")
        )
    
    def get_failed_executions(self, hours: int = 24) -> List[dict]:
        all_executions = self.get_executions(limit=200)
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        failed = []
        for e in all_executions:
            if e.get("status") not in ["error", "failed"]:
                continue
            started = e.get("startedAt", "")
            if started:
                try:
                    exec_time = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    if exec_time.replace(tzinfo=None) > cutoff:
                        failed.append(e)
                except:
                    pass
        return failed
    
    def clone_workflow(self, workflow_id: str, new_name: str) -> dict:
        original = self.get_workflow(workflow_id)
        original["name"] = new_name
        return self.create_workflow(original)
    
    def get_workflow_stats(self) -> dict:
        workflows = self.list_workflows()
        by_category = {}
        for wf in workflows:
            cat = wf.category.value
            if cat not in by_category:
                by_category[cat] = {"total": 0, "active": 0}
            by_category[cat]["total"] += 1
            if wf.active:
                by_category[cat]["active"] += 1
        return {
            "total": len(workflows), "active": len([w for w in workflows if w.active]),
            "inactive": len([w for w in workflows if not w.active]),
            "by_category": by_category, "timestamp": datetime.utcnow().isoformat()
        }
    
    def health_check(self) -> dict:
        try:
            workflows = self.list_workflows()
            recent_failures = self.get_failed_executions(hours=1)
            return {
                "status": "healthy", "connected": True, "base_url": self.base_url,
                "workflow_count": len(workflows), "active_count": len([w for w in workflows if w.active]),
                "recent_failures": len(recent_failures), "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"status": "unhealthy", "connected": False, "base_url": self.base_url, "error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    def close(self):
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class WorkflowScheduler:
    """24/7/365 Workflow Scheduler for MYCA"""
    
    def __init__(self, engine: N8NWorkflowEngine = None):
        self.engine = engine or N8NWorkflowEngine()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._callbacks: Dict[str, List[Callable]] = {"sync_complete": [], "workflow_failed": [], "health_check": []}
    
    def on(self, event: str, callback: Callable):
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    async def _emit(self, event: str, data: Any):
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    async def _sync_loop(self, interval_minutes: int = 15):
        while self._running:
            try:
                logger.info("Running scheduled workflow sync...")
                result = self.engine.sync_all_local_workflows(activate_core=True)
                await self._emit("sync_complete", result)
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
            await asyncio.sleep(interval_minutes * 60)
    
    async def _health_loop(self, interval_minutes: int = 5):
        while self._running:
            try:
                health = self.engine.health_check()
                await self._emit("health_check", health)
                if health.get("recent_failures", 0) > 0:
                    failures = self.engine.get_failed_executions(hours=1)
                    for failure in failures:
                        await self._emit("workflow_failed", failure)
            except Exception as e:
                logger.error(f"Health loop error: {e}")
            await asyncio.sleep(interval_minutes * 60)
    
    async def _archive_loop(self, interval_hours: int = 24):
        while self._running:
            try:
                logger.info("Running scheduled workflow archive...")
                for wf in self.engine.list_workflows():
                    try:
                        self.engine.archive_workflow(wf.id, reason="scheduled backup")
                    except Exception as e:
                        logger.warning(f"Archive failed for {wf.name}: {e}")
            except Exception as e:
                logger.error(f"Archive loop error: {e}")
            await asyncio.sleep(interval_hours * 3600)
    
    async def start(self, sync_interval: int = 15, health_interval: int = 5, archive_interval: int = 24):
        logger.info("Starting workflow scheduler...")
        self._running = True
        try:
            result = self.engine.sync_all_local_workflows(activate_core=True)
            logger.info(f"Initial sync: {len(result.imported)} imported, {len(result.errors)} errors")
        except Exception as e:
            logger.error(f"Initial sync failed: {e}")
        self._tasks = [
            asyncio.create_task(self._sync_loop(sync_interval)),
            asyncio.create_task(self._health_loop(health_interval)),
            asyncio.create_task(self._archive_loop(archive_interval))
        ]
        logger.info("Workflow scheduler started")
    
    async def stop(self):
        logger.info("Stopping workflow scheduler...")
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        logger.info("Workflow scheduler stopped")


def get_engine(use_cloud: bool = False) -> N8NWorkflowEngine:
    return N8NWorkflowEngine(use_cloud=use_cloud)


def sync_workflows(activate_core: bool = True) -> SyncResult:
    with N8NWorkflowEngine() as engine:
        return engine.sync_all_local_workflows(activate_core=activate_core)


def get_scheduler() -> WorkflowScheduler:
    return WorkflowScheduler()


async def run_initial_sync():
    engine = N8NWorkflowEngine()
    try:
        result = engine.sync_all_local_workflows(activate_core=True)
        logger.info(f"Initial sync complete: {result.to_dict()}")
        return result
    finally:
        engine.close()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    with N8NWorkflowEngine() as engine:
        health = engine.health_check()
        print(f"Health: {health}")
        if health.get("connected"):
            stats = engine.get_workflow_stats()
            print(f"Stats: {stats}")
            result = engine.sync_all_local_workflows()
            print(f"Sync: {result.to_dict()}")
