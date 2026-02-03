"""
MYCA Workflow Orchestration Integration - January 25, 2026

This module integrates the n8n workflow engine with the MYCA orchestrator,
enabling 24/7/365 automated management of workflows alongside agents.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from mycosoft_mas.core.n8n_workflow_engine import (
    N8NWorkflowEngine,
    WorkflowScheduler,
    SyncResult,
    WorkflowInfo,
    WorkflowCategory
)

logger = logging.getLogger(__name__)


@dataclass
class WorkflowOrchestratorStatus:
    """Status of the workflow orchestrator"""
    engine_connected: bool
    scheduler_running: bool
    workflow_count: int
    active_workflows: int
    recent_failures: int
    last_sync: Optional[str]
    last_health_check: Optional[str]


class MYCAWorkflowOrchestrator:
    """
    MYCA Workflow Orchestrator - Core component of the MAS
    
    Responsibilities:
    - Manage n8n workflows programmatically
    - Auto-sync workflows on schedule
    - Monitor workflow health
    - Auto-restart failed workflows
    - Archive and version workflows
    - Dynamically rewire workflows based on system needs
    
    This is integrated into the main MYCA orchestrator to provide
    unified control over both agents and workflows.
    """
    
    def __init__(self):
        self._engine: Optional[N8NWorkflowEngine] = None
        self._scheduler: Optional[WorkflowScheduler] = None
        self._last_sync: Optional[str] = None
        self._last_health_check: Optional[str] = None
        self._started = False
        
        # Event handlers for integration with main orchestrator
        self._event_handlers: Dict[str, List] = {
            "workflow_failed": [],
            "sync_complete": [],
            "health_degraded": []
        }
    
    @property
    def engine(self) -> N8NWorkflowEngine:
        """Get or create the workflow engine"""
        if self._engine is None:
            self._engine = N8NWorkflowEngine()
        return self._engine
    
    @property
    def scheduler(self) -> WorkflowScheduler:
        """Get or create the workflow scheduler"""
        if self._scheduler is None:
            self._scheduler = WorkflowScheduler(self.engine)
            
            # Register internal handlers
            self._scheduler.on("sync_complete", self._on_sync_complete)
            self._scheduler.on("workflow_failed", self._on_workflow_failed)
            self._scheduler.on("health_check", self._on_health_check)
        
        return self._scheduler
    
    def on_event(self, event: str, handler):
        """Register event handler for integration"""
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)
    
    async def _emit_event(self, event: str, data: Any):
        """Emit event to registered handlers"""
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler error for {event}: {e}")
    
    def _on_sync_complete(self, result: SyncResult):
        """Handle sync complete event"""
        self._last_sync = datetime.utcnow().isoformat()
        logger.info(f"Workflow sync complete: {len(result.imported)} imported")
        asyncio.create_task(self._emit_event("sync_complete", result))
    
    def _on_workflow_failed(self, failure: dict):
        """Handle workflow failure event"""
        logger.warning(f"Workflow failed: {failure.get('workflowName', 'unknown')}")
        asyncio.create_task(self._emit_event("workflow_failed", failure))
    
    def _on_health_check(self, health: dict):
        """Handle health check event"""
        self._last_health_check = datetime.utcnow().isoformat()
        
        if health.get("recent_failures", 0) > 5:
            logger.warning("Workflow health degraded - too many failures")
            asyncio.create_task(self._emit_event("health_degraded", health))
    
    async def start(
        self,
        sync_interval: int = 15,
        health_interval: int = 5,
        archive_interval: int = 24,
        initial_sync: bool = True
    ):
        """Start the workflow orchestrator"""
        logger.info("Starting MYCA Workflow Orchestrator...")
        
        # Initial sync if requested
        if initial_sync:
            try:
                result = self.engine.sync_all_local_workflows(activate_core=True)
                self._last_sync = datetime.utcnow().isoformat()
                logger.info(f"Initial sync: {len(result.imported)} workflows, {len(result.errors)} errors")
            except Exception as e:
                logger.error(f"Initial sync failed: {e}")
        
        # Start scheduler
        await self.scheduler.start(
            sync_interval=sync_interval,
            health_interval=health_interval,
            archive_interval=archive_interval
        )
        
        self._started = True
        logger.info("MYCA Workflow Orchestrator started")
    
    async def stop(self):
        """Stop the workflow orchestrator"""
        logger.info("Stopping MYCA Workflow Orchestrator...")
        
        if self._scheduler:
            await self._scheduler.stop()
        
        if self._engine:
            self._engine.close()
            self._engine = None
        
        self._started = False
        logger.info("MYCA Workflow Orchestrator stopped")
    
    def get_status(self) -> WorkflowOrchestratorStatus:
        """Get current orchestrator status"""
        try:
            health = self.engine.health_check()
            return WorkflowOrchestratorStatus(
                engine_connected=health.get("connected", False),
                scheduler_running=self._scheduler._running if self._scheduler else False,
                workflow_count=health.get("workflow_count", 0),
                active_workflows=health.get("active_count", 0),
                recent_failures=health.get("recent_failures", 0),
                last_sync=self._last_sync,
                last_health_check=self._last_health_check
            )
        except Exception as e:
            return WorkflowOrchestratorStatus(
                engine_connected=False,
                scheduler_running=False,
                workflow_count=0,
                active_workflows=0,
                recent_failures=0,
                last_sync=self._last_sync,
                last_health_check=self._last_health_check
            )
    
    # ==================== Workflow Operations ====================
    
    def list_workflows(self, category: WorkflowCategory = None) -> List[WorkflowInfo]:
        """List all workflows"""
        return self.engine.list_workflows(category=category)
    
    def get_workflow(self, workflow_id: str) -> dict:
        """Get a specific workflow"""
        return self.engine.get_workflow(workflow_id)
    
    def activate_workflow(self, workflow_id: str) -> dict:
        """Activate a workflow"""
        return self.engine.activate_workflow(workflow_id)
    
    def deactivate_workflow(self, workflow_id: str) -> dict:
        """Deactivate a workflow"""
        return self.engine.deactivate_workflow(workflow_id)
    
    def sync_workflows(self, activate_core: bool = True) -> SyncResult:
        """Manually trigger workflow sync"""
        result = self.engine.sync_all_local_workflows(activate_core=activate_core)
        self._last_sync = datetime.utcnow().isoformat()
        return result
    
    def archive_workflow(self, workflow_id: str, reason: str = "manual"):
        """Archive a workflow version"""
        return self.engine.archive_workflow(workflow_id, reason=reason)
    
    def restore_workflow(self, workflow_id: str, version: int = None) -> dict:
        """Restore a workflow from archive"""
        return self.engine.restore_workflow(workflow_id, version=version)
    
    def clone_workflow(self, workflow_id: str, new_name: str) -> dict:
        """Clone a workflow with a new name"""
        return self.engine.clone_workflow(workflow_id, new_name)
    
    # ==================== Dynamic Rewiring ====================
    
    def rewire_workflow_connection(
        self,
        workflow_id: str,
        source_node: str,
        target_node: str,
        disconnect: bool = False
    ) -> dict:
        """Add or remove a connection between nodes in a workflow"""
        workflow = self.engine.get_workflow(workflow_id)
        
        if "connections" not in workflow:
            workflow["connections"] = {}
        
        if disconnect:
            # Remove connection
            if source_node in workflow["connections"]:
                main_outputs = workflow["connections"][source_node].get("main", [])
                for outputs in main_outputs:
                    outputs[:] = [c for c in outputs if c.get("node") != target_node]
        else:
            # Add connection
            if source_node not in workflow["connections"]:
                workflow["connections"][source_node] = {"main": [[]]}
            
            workflow["connections"][source_node]["main"][0].append({
                "node": target_node,
                "type": "main",
                "index": 0
            })
        
        return self.engine.update_workflow(workflow_id, workflow)
    
    def disable_node(self, workflow_id: str, node_name: str) -> dict:
        """Disable a specific node in a workflow"""
        workflow = self.engine.get_workflow(workflow_id)
        
        for node in workflow.get("nodes", []):
            if node.get("name") == node_name:
                node["disabled"] = True
                break
        
        return self.engine.update_workflow(workflow_id, workflow)
    
    def enable_node(self, workflow_id: str, node_name: str) -> dict:
        """Enable a specific node in a workflow"""
        workflow = self.engine.get_workflow(workflow_id)
        
        for node in workflow.get("nodes", []):
            if node.get("name") == node_name:
                node["disabled"] = False
                break
        
        return self.engine.update_workflow(workflow_id, workflow)


# Global instance
_workflow_orchestrator: Optional[MYCAWorkflowOrchestrator] = None


def get_workflow_orchestrator() -> MYCAWorkflowOrchestrator:
    """Get the global workflow orchestrator instance"""
    global _workflow_orchestrator
    if _workflow_orchestrator is None:
        _workflow_orchestrator = MYCAWorkflowOrchestrator()
    return _workflow_orchestrator


async def start_workflow_orchestrator(**kwargs):
    """Start the global workflow orchestrator"""
    orchestrator = get_workflow_orchestrator()
    await orchestrator.start(**kwargs)
    return orchestrator


async def stop_workflow_orchestrator():
    """Stop the global workflow orchestrator"""
    orchestrator = get_workflow_orchestrator()
    await orchestrator.stop()
