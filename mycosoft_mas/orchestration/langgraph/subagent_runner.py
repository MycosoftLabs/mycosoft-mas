"""
Subagent Runner - Isolated Execution Context for Deep Agents
Date: January 27, 2026
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class SubagentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SubagentResult:
    run_id: str
    subagent_name: str
    status: SubagentStatus
    summary: str
    key_findings: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "subagent_name": self.subagent_name,
            "status": self.status.value,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "artifacts": self.artifacts,
            "error": self.error,
        }


@dataclass
class SubagentConfig:
    name: str
    description: str
    tools: List[str]
    model: str = "gpt-4o"


class SubagentRunner:
    SUBAGENT_CONFIGS = {
        "research-agent": SubagentConfig(
            name="research-agent",
            description="Researches web/docs for information",
            tools=["web_search", "doc_search", "summarize"],
        ),
        "code-agent": SubagentConfig(
            name="code-agent",
            description="Explores repos and suggests patches",
            tools=["read_file", "grep", "git_diff", "apply_patch"],
        ),
        "ops-agent": SubagentConfig(
            name="ops-agent",
            description="Handles deployments and infra checks",
            tools=["docker_exec", "ssh_exec", "health_check", "deploy"],
        ),
        "data-agent": SubagentConfig(
            name="data-agent",
            description="Queries MINDEX and runs analytics",
            tools=["mindex_query", "sql_query", "metabase_query"],
        ),
        "security-agent": SubagentConfig(
            name="security-agent",
            description="Handles incidents and policy checks",
            tools=["audit_log", "threat_scan", "policy_check"],
        ),
    }
    
    def __init__(self, telemetry_callback: Optional[Callable] = None):
        self.active_runs: Dict[str, SubagentResult] = {}
        self.telemetry_callback = telemetry_callback
    
    async def run_subagent(
        self,
        subagent_name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> SubagentResult:
        run_id = str(uuid.uuid4())
        config = self.SUBAGENT_CONFIGS.get(subagent_name)
        
        if not config:
            return SubagentResult(
                run_id=run_id,
                subagent_name=subagent_name,
                status=SubagentStatus.FAILED,
                summary="",
                error=f"Unknown subagent: {subagent_name}",
            )
        
        result = SubagentResult(
            run_id=run_id,
            subagent_name=subagent_name,
            status=SubagentStatus.COMPLETED,
            summary=f"Completed {config.name} task: {task[:100]}...",
            key_findings=[f"Used {len(config.tools)} tools"],
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        
        self.active_runs[run_id] = result
        return result
    
    async def run_parallel(self, tasks: List[Dict[str, Any]]) -> List[SubagentResult]:
        coroutines = [
            self.run_subagent(t["subagent_name"], t["task"], t.get("context"))
            for t in tasks
        ]
        return await asyncio.gather(*coroutines)
