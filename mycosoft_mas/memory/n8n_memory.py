"""
n8n Workflow Memory System.
Created: February 5, 2026

Provides memory management for n8n workflow automation:
- Workflow execution history tracking
- Automation pattern learning
- Failure analysis and recovery
- Performance optimization insights
- Cross-workflow dependencies
"""

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger("N8NMemory")


class ExecutionStatus(str, Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class WorkflowCategory(str, Enum):
    """Categories of workflows."""
    MYCA = "myca"           # MYCA assistant workflows
    DEVICE = "device"       # Device control workflows
    DATA = "data"           # Data processing workflows
    ALERT = "alert"         # Alert and notification workflows
    SYNC = "sync"           # Data sync workflows
    SCHEDULE = "schedule"   # Scheduled automation
    WEBHOOK = "webhook"     # Webhook-triggered workflows
    CUSTOM = "custom"       # Custom workflows


@dataclass
class WorkflowExecution:
    """A single workflow execution record."""
    id: UUID
    workflow_id: str
    workflow_name: str
    category: WorkflowCategory
    status: ExecutionStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    trigger: str = "manual"
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    error_node: Optional[str] = None
    nodes_executed: int = 0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "category": self.category.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_ms": self.duration_ms,
            "trigger": self.trigger,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "error_node": self.error_node,
            "nodes_executed": self.nodes_executed,
            "retry_count": self.retry_count,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowExecution":
        return cls(
            id=UUID(data["id"]),
            workflow_id=data["workflow_id"],
            workflow_name=data["workflow_name"],
            category=WorkflowCategory(data["category"]),
            status=ExecutionStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            duration_ms=data.get("duration_ms"),
            trigger=data.get("trigger", "manual"),
            input_data=data.get("input_data", {}),
            output_data=data.get("output_data", {}),
            error_message=data.get("error_message"),
            error_node=data.get("error_node"),
            nodes_executed=data.get("nodes_executed", 0),
            retry_count=data.get("retry_count", 0),
            metadata=data.get("metadata", {})
        )


@dataclass
class WorkflowPattern:
    """A learned pattern from workflow executions."""
    id: UUID
    workflow_id: str
    pattern_type: str  # "success", "failure", "performance"
    description: str
    frequency: int = 0
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    conditions: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class WorkflowDependency:
    """A dependency between workflows."""
    source_workflow: str
    target_workflow: str
    dependency_type: str  # "triggers", "data", "sequence"
    strength: float = 1.0  # 0-1 indicating how often they run together


class WorkflowAnalyzer:
    """Analyzes workflow executions for patterns and insights."""
    
    def analyze_failures(self, executions: List[WorkflowExecution]) -> List[WorkflowPattern]:
        """Identify failure patterns."""
        patterns = []
        
        # Group failures by error node
        node_failures: Dict[str, List[WorkflowExecution]] = {}
        for ex in executions:
            if ex.status == ExecutionStatus.ERROR and ex.error_node:
                if ex.error_node not in node_failures:
                    node_failures[ex.error_node] = []
                node_failures[ex.error_node].append(ex)
        
        # Create patterns for frequent failures
        for node, failures in node_failures.items():
            if len(failures) >= 3:
                pattern = WorkflowPattern(
                    id=uuid4(),
                    workflow_id=failures[0].workflow_id,
                    pattern_type="failure",
                    description=f"Node '{node}' fails frequently ({len(failures)} times)",
                    frequency=len(failures),
                    conditions={"error_node": node},
                    recommendations=[
                        f"Review the '{node}' node configuration",
                        "Check for input data validation issues",
                        "Consider adding error handling"
                    ],
                    confidence=min(0.9, 0.5 + (len(failures) * 0.1))
                )
                patterns.append(pattern)
        
        return patterns
    
    def analyze_performance(self, executions: List[WorkflowExecution]) -> Dict[str, Any]:
        """Analyze workflow performance."""
        if not executions:
            return {}
        
        successful = [e for e in executions if e.status == ExecutionStatus.SUCCESS and e.duration_ms]
        if not successful:
            return {}
        
        durations = [e.duration_ms for e in successful]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        
        # Identify slow executions (>2x average)
        slow_executions = [e for e in successful if e.duration_ms > avg_duration * 2]
        
        return {
            "total_executions": len(executions),
            "success_rate": len(successful) / len(executions),
            "avg_duration_ms": round(avg_duration, 2),
            "max_duration_ms": max_duration,
            "min_duration_ms": min_duration,
            "slow_execution_count": len(slow_executions),
            "performance_trend": "stable"  # Could be calculated from time series
        }
    
    def detect_dependencies(self, executions: List[WorkflowExecution]) -> List[WorkflowDependency]:
        """Detect dependencies between workflows based on execution patterns."""
        dependencies = []
        
        # Sort by time
        sorted_execs = sorted(executions, key=lambda e: e.started_at)
        
        # Track workflow sequences (workflows that run within 60s of each other)
        workflow_sequences: Dict[Tuple[str, str], int] = {}
        
        for i, ex in enumerate(sorted_execs[:-1]):
            next_ex = sorted_execs[i + 1]
            time_diff = (next_ex.started_at - ex.started_at).total_seconds()
            
            if time_diff < 60 and ex.workflow_id != next_ex.workflow_id:
                key = (ex.workflow_id, next_ex.workflow_id)
                workflow_sequences[key] = workflow_sequences.get(key, 0) + 1
        
        # Create dependencies for frequent sequences
        for (source, target), count in workflow_sequences.items():
            if count >= 3:
                dependencies.append(WorkflowDependency(
                    source_workflow=source,
                    target_workflow=target,
                    dependency_type="sequence",
                    strength=min(1.0, count / 10)
                ))
        
        return dependencies


class N8NMemory:
    """
    Memory system for n8n workflow automation.
    
    Provides:
    - Workflow execution history
    - Pattern learning from executions
    - Failure analysis and recommendations
    - Performance tracking
    - Cross-workflow dependency tracking
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv(
            "MINDEX_DATABASE_URL",
            "postgresql://mycosoft:REDACTED_VM_SSH_PASSWORD@192.168.0.189:5432/mindex"
        )
        self._pool = None
        self._analyzer = WorkflowAnalyzer()
        self._execution_cache: Dict[UUID, WorkflowExecution] = {}
        self._pattern_cache: Dict[str, List[WorkflowPattern]] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the memory system."""
        if self._initialized:
            return
        
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=5
            )
            logger.info("N8N memory connected to database")
        except Exception as e:
            logger.warning(f"Database connection failed, using in-memory only: {e}")
        
        self._initialized = True
    
    async def record_execution(
        self,
        workflow_id: str,
        workflow_name: str,
        category: WorkflowCategory = WorkflowCategory.CUSTOM,
        trigger: str = "manual",
        input_data: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        """Record start of a workflow execution."""
        execution = WorkflowExecution(
            id=uuid4(),
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            category=category,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            trigger=trigger,
            input_data=input_data or {}
        )
        
        self._execution_cache[execution.id] = execution
        await self._persist_execution(execution)
        
        return execution
    
    async def complete_execution(
        self,
        execution_id: UUID,
        status: ExecutionStatus,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_node: Optional[str] = None,
        nodes_executed: int = 0
    ) -> Optional[WorkflowExecution]:
        """Complete a workflow execution."""
        execution = self._execution_cache.get(execution_id)
        if not execution:
            return None
        
        execution.status = status
        execution.ended_at = datetime.now(timezone.utc)
        execution.duration_ms = int((execution.ended_at - execution.started_at).total_seconds() * 1000)
        execution.output_data = output_data or {}
        execution.error_message = error_message
        execution.error_node = error_node
        execution.nodes_executed = nodes_executed
        
        await self._persist_execution(execution)
        
        # Analyze for patterns after completion
        if status == ExecutionStatus.ERROR:
            await self._analyze_and_update_patterns(execution.workflow_id)
        
        return execution
    
    async def _persist_execution(self, execution: WorkflowExecution) -> bool:
        """Persist execution to database."""
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO workflow.executions (id, workflow_id, workflow_name, category,
                        status, started_at, ended_at, duration_ms, trigger, input_data,
                        output_data, error_message, error_node, nodes_executed, retry_count, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb, $12, $13, $14, $15, $16::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        ended_at = EXCLUDED.ended_at,
                        duration_ms = EXCLUDED.duration_ms,
                        output_data = EXCLUDED.output_data,
                        error_message = EXCLUDED.error_message,
                        error_node = EXCLUDED.error_node,
                        nodes_executed = EXCLUDED.nodes_executed
                """, str(execution.id), execution.workflow_id, execution.workflow_name,
                    execution.category.value, execution.status.value, execution.started_at,
                    execution.ended_at, execution.duration_ms, execution.trigger,
                    json.dumps(execution.input_data), json.dumps(execution.output_data),
                    execution.error_message, execution.error_node, execution.nodes_executed,
                    execution.retry_count, json.dumps(execution.metadata))
            return True
        except Exception as e:
            logger.error(f"Failed to persist execution: {e}")
            return False
    
    async def _analyze_and_update_patterns(self, workflow_id: str) -> None:
        """Analyze recent executions and update patterns."""
        executions = await self.get_executions(workflow_id, limit=50)
        
        # Analyze failures
        failure_patterns = self._analyzer.analyze_failures(executions)
        self._pattern_cache[workflow_id] = failure_patterns
        
        # Persist patterns
        for pattern in failure_patterns:
            await self._persist_pattern(pattern)
    
    async def _persist_pattern(self, pattern: WorkflowPattern) -> bool:
        """Persist pattern to database."""
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO workflow.patterns (id, workflow_id, pattern_type, description,
                        frequency, last_seen, conditions, recommendations, confidence)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9)
                    ON CONFLICT (id) DO UPDATE SET
                        frequency = EXCLUDED.frequency,
                        last_seen = EXCLUDED.last_seen,
                        confidence = EXCLUDED.confidence
                """, str(pattern.id), pattern.workflow_id, pattern.pattern_type,
                    pattern.description, pattern.frequency, pattern.last_seen,
                    json.dumps(pattern.conditions), pattern.recommendations, pattern.confidence)
            return True
        except Exception as e:
            logger.error(f"Failed to persist pattern: {e}")
            return False
    
    async def get_executions(
        self,
        workflow_id: Optional[str] = None,
        category: Optional[WorkflowCategory] = None,
        status: Optional[ExecutionStatus] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[WorkflowExecution]:
        """Get workflow executions."""
        if not self._pool:
            # Return from cache
            results = list(self._execution_cache.values())
            if workflow_id:
                results = [e for e in results if e.workflow_id == workflow_id]
            return results[:limit]
        
        try:
            async with self._pool.acquire() as conn:
                sql = "SELECT * FROM workflow.executions WHERE 1=1"
                params = []
                param_idx = 1
                
                if workflow_id:
                    sql += f" AND workflow_id = ${param_idx}"
                    params.append(workflow_id)
                    param_idx += 1
                
                if category:
                    sql += f" AND category = ${param_idx}"
                    params.append(category.value)
                    param_idx += 1
                
                if status:
                    sql += f" AND status = ${param_idx}"
                    params.append(status.value)
                    param_idx += 1
                
                if since:
                    sql += f" AND started_at >= ${param_idx}"
                    params.append(since)
                    param_idx += 1
                
                sql += f" ORDER BY started_at DESC LIMIT ${param_idx}"
                params.append(limit)
                
                rows = await conn.fetch(sql, *params)
                return [WorkflowExecution.from_dict({
                    "id": row["id"],
                    "workflow_id": row["workflow_id"],
                    "workflow_name": row["workflow_name"],
                    "category": row["category"],
                    "status": row["status"],
                    "started_at": row["started_at"].isoformat(),
                    "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
                    "duration_ms": row["duration_ms"],
                    "trigger": row["trigger"],
                    "input_data": json.loads(row["input_data"]) if row["input_data"] else {},
                    "output_data": json.loads(row["output_data"]) if row["output_data"] else {},
                    "error_message": row["error_message"],
                    "error_node": row["error_node"],
                    "nodes_executed": row["nodes_executed"],
                    "retry_count": row["retry_count"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                }) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get executions: {e}")
            return []
    
    async def get_patterns(self, workflow_id: str) -> List[WorkflowPattern]:
        """Get learned patterns for a workflow."""
        if workflow_id in self._pattern_cache:
            return self._pattern_cache[workflow_id]
        return []
    
    async def get_performance_report(self, workflow_id: str) -> Dict[str, Any]:
        """Get performance report for a workflow."""
        executions = await self.get_executions(workflow_id, limit=100)
        return self._analyzer.analyze_performance(executions)
    
    async def get_workflow_health(self) -> Dict[str, Any]:
        """Get overall workflow system health."""
        now = datetime.now(timezone.utc)
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        hourly = await self.get_executions(since=last_hour)
        daily = await self.get_executions(since=last_day)
        
        hourly_success = len([e for e in hourly if e.status == ExecutionStatus.SUCCESS])
        hourly_errors = len([e for e in hourly if e.status == ExecutionStatus.ERROR])
        
        daily_success = len([e for e in daily if e.status == ExecutionStatus.SUCCESS])
        daily_errors = len([e for e in daily if e.status == ExecutionStatus.ERROR])
        
        return {
            "last_hour": {
                "total": len(hourly),
                "success": hourly_success,
                "errors": hourly_errors,
                "success_rate": hourly_success / len(hourly) if hourly else 1.0
            },
            "last_day": {
                "total": len(daily),
                "success": daily_success,
                "errors": daily_errors,
                "success_rate": daily_success / len(daily) if daily else 1.0
            },
            "database_connected": self._pool is not None
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return {
            "cached_executions": len(self._execution_cache),
            "cached_patterns": sum(len(p) for p in self._pattern_cache.values()),
            "database_connected": self._pool is not None,
            "initialized": self._initialized
        }


# Singleton instance
_n8n_memory: Optional[N8NMemory] = None


async def get_n8n_memory() -> N8NMemory:
    """Get or create the singleton N8N memory instance."""
    global _n8n_memory
    if _n8n_memory is None:
        _n8n_memory = N8NMemory()
        await _n8n_memory.initialize()
    return _n8n_memory
