"""
Workflow Auto-Monitor Service - February 18, 2026

24/7 background service for n8n workflow health, drift detection, and auto-sync.
Runs health check every 60s, drift detection every 15 min, auto-sync on drift.
"""

import asyncio
import json
import hashlib
import logging
import os
from typing import Callable, Dict, Any, Optional

from mycosoft_mas.core.n8n_workflow_engine import (
    N8NWorkflowEngine,
    WORKFLOWS_DIR,
)

logger = logging.getLogger(__name__)

# Intervals in seconds
HEALTH_INTERVAL = 60
DRIFT_INTERVAL = 15 * 60  # 15 minutes


def _compute_checksum(data: dict) -> str:
    content = json.dumps(data, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()


def _repo_checksums() -> Dict[str, str]:
    """Return mapping of workflow name -> checksum for repo files."""
    out = {}
    if not WORKFLOWS_DIR.exists():
        return out
    for f in WORKFLOWS_DIR.glob("**/*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            name = data.get("name", f.stem)
            out[name] = _compute_checksum(data)
        except Exception as e:
            logger.warning(f"Could not checksum {f}: {e}")
    return out


def _instance_checksums(engine: N8NWorkflowEngine) -> Dict[str, str]:
    """Return mapping of workflow name -> checksum for n8n instance."""
    out = {}
    try:
        for w in engine.list_workflows():
            try:
                wf = engine.get_workflow(w.id)
                name = wf.get("name", w.name)
                out[name] = _compute_checksum(wf)
            except Exception as e:
                logger.warning(f"Could not get workflow {w.name}: {e}")
    except Exception as e:
        logger.warning(f"Instance checksums failed: {e}")
    return out


def _drift_detected(repo: Dict[str, str], local: Dict[str, str], cloud: Dict[str, str]) -> bool:
    """True if repo differs from local or from cloud (by name/checksum)."""
    for name, csum in repo.items():
        if local.get(name) != csum or cloud.get(name) != csum:
            return True
    # Extra workflows in local/cloud that are not in repo count as drift if we care
    for name in set(local) | set(cloud):
        if name not in repo and (local.get(name) or cloud.get(name)):
            return True
    return False


class WorkflowAutoMonitor:
    """
    24/7 background service: health check (60s), drift detection (15m), auto-sync on drift.
    Optional: log failures to episodic memory, trigger alert workflow.
    """

    def __init__(
        self,
        *,
        health_interval: int = HEALTH_INTERVAL,
        drift_interval: int = DRIFT_INTERVAL,
        on_failure: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ):
        self.health_interval = health_interval
        self.drift_interval = drift_interval
        self.on_failure = on_failure  # (message, context) -> None or awaitable
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_health: Dict[str, Any] = {}
        self._last_drift_run: Optional[float] = None

    async def _emit_failure(self, message: str, context: Dict[str, Any]) -> None:
        logger.warning("WorkflowAutoMonitor: %s %s", message, context)
        if self.on_failure:
            try:
                fn = self.on_failure
                if asyncio.iscoroutinefunction(fn):
                    await fn(message, context)
                else:
                    fn(message, context)
            except Exception as e:
                logger.exception("on_failure callback error: %s", e)

    async def _health_loop(self) -> None:
        local_url = os.getenv("N8N_LOCAL_URL", "http://localhost:5678")
        cloud_url = os.getenv("N8N_URL", "http://192.168.0.188:5678")
        local_key = os.getenv("N8N_LOCAL_API_KEY", os.getenv("N8N_API_KEY", ""))
        cloud_key = os.getenv("N8N_API_KEY", "")
        while self._running:
            try:
                local_health = None
                cloud_health = None
                try:
                    engine_local = N8NWorkflowEngine(base_url=local_url, api_key=local_key)
                    try:
                        local_health = await asyncio.to_thread(engine_local.health_check)
                    finally:
                        engine_local.close()
                except Exception as e:
                    local_health = {"status": "unhealthy", "error": str(e)}
                    await self._emit_failure("Local n8n health check failed", {"error": str(e), "url": local_url})

                try:
                    engine_cloud = N8NWorkflowEngine(base_url=cloud_url, api_key=cloud_key)
                    try:
                        cloud_health = await asyncio.to_thread(engine_cloud.health_check)
                    finally:
                        engine_cloud.close()
                except Exception as e:
                    cloud_health = {"status": "unhealthy", "error": str(e)}
                    await self._emit_failure("Cloud n8n health check failed", {"error": str(e), "url": cloud_url})

                self._last_health = {"local": local_health, "cloud": cloud_health}
            except Exception as e:
                logger.exception("Health loop error: %s", e)
            await asyncio.sleep(self.health_interval)

    async def _drift_loop(self) -> None:
        local_url = os.getenv("N8N_LOCAL_URL", "http://localhost:5678")
        cloud_url = os.getenv("N8N_URL", "http://192.168.0.188:5678")
        local_key = os.getenv("N8N_LOCAL_API_KEY", os.getenv("N8N_API_KEY", ""))
        cloud_key = os.getenv("N8N_API_KEY", "")
        while self._running:
            try:
                repo = _repo_checksums()
                local_csums = {}
                cloud_csums = {}
                try:
                    engine_local = N8NWorkflowEngine(base_url=local_url, api_key=local_key)
                    try:
                        local_csums = await asyncio.to_thread(_instance_checksums, engine_local)
                    finally:
                        engine_local.close()
                except Exception as e:
                    logger.warning("Drift: could not get local checksums: %s", e)
                try:
                    engine_cloud = N8NWorkflowEngine(base_url=cloud_url, api_key=cloud_key)
                    try:
                        cloud_csums = await asyncio.to_thread(_instance_checksums, engine_cloud)
                    finally:
                        engine_cloud.close()
                except Exception as e:
                    logger.warning("Drift: could not get cloud checksums: %s", e)

                if _drift_detected(repo, local_csums, cloud_csums):
                    logger.info("Workflow drift detected; running sync-both")
                    try:
                        engine_local = N8NWorkflowEngine(base_url=local_url, api_key=local_key)
                        engine_cloud = N8NWorkflowEngine(base_url=cloud_url, api_key=cloud_key)
                        try:
                            r_local = await asyncio.to_thread(
                                engine_local.sync_all_local_workflows, True
                            )
                            r_cloud = await asyncio.to_thread(
                                engine_cloud.sync_all_local_workflows, True
                            )
                            logger.info(
                                "Auto-sync: local imported=%s, cloud imported=%s",
                                len(r_local.imported),
                                len(r_cloud.imported),
                            )
                        finally:
                            engine_local.close()
                            engine_cloud.close()
                    except Exception as e:
                        await self._emit_failure("Auto-sync after drift failed", {"error": str(e)})
                self._last_drift_run = asyncio.get_event_loop().time()
            except Exception as e:
                logger.exception("Drift loop error: %s", e)
            await asyncio.sleep(self.drift_interval)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loops())
        logger.info("WorkflowAutoMonitor started (health=%ss, drift=%ss)", self.health_interval, self.drift_interval)

    async def _run_loops(self) -> None:
        await asyncio.gather(self._health_loop(), self._drift_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("WorkflowAutoMonitor stopped")

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "last_health": self._last_health,
            "last_drift_run": self._last_drift_run,
            "health_interval": self.health_interval,
            "drift_interval": self.drift_interval,
        }


# Singleton for startup integration
_monitor: Optional[WorkflowAutoMonitor] = None


def get_workflow_auto_monitor() -> WorkflowAutoMonitor:
    global _monitor
    if _monitor is None:
        _monitor = WorkflowAutoMonitor()
    return _monitor
