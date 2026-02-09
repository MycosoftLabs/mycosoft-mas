"""
DebugAgent - Automated Error Monitoring and Debugging Agent

This agent:
1. Monitors N8n workflow executions for errors
2. Analyzes error patterns and root causes
3. Communicates with MYCA orchestrator about issues
4. Creates improvement suggestions
5. Triggers CodeFixAgent for automatic fixes
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class WorkflowError:
    """Represents a workflow execution error"""
    execution_id: str
    workflow_id: str
    workflow_name: str
    error_message: str
    node_name: str
    timestamp: datetime
    run_time_ms: int
    stack_trace: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class ErrorPattern:
    """Represents a recurring error pattern"""
    pattern_id: str
    error_type: str
    affected_workflows: List[str]
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime
    suggested_fixes: List[str] = field(default_factory=list)
    auto_fixable: bool = False


@dataclass 
class ImprovementSuggestion:
    """Represents a system improvement suggestion"""
    suggestion_id: str
    category: str  # workflow, service, code, infrastructure
    priority: str  # critical, high, medium, low
    title: str
    description: str
    affected_components: List[str]
    estimated_impact: str
    auto_fixable: bool
    fix_code: Optional[str] = None


class DebugAgent:
    """
    Automated debugging agent that monitors and fixes system issues.
    
    Features:
    - Real-time error monitoring from N8n, Docker, and MAS orchestrator
    - Pattern recognition for recurring issues
    - Automatic fix generation using AI
    - Integration with MYCA orchestrator for reporting
    - GitHub integration for code fixes
    """
    
    def __init__(
        self,
        n8n_url: str = "http://localhost:5678",
        mas_url: str = "http://localhost:8001",
        check_interval: int = 60,  # seconds
    ):
        self.n8n_url = n8n_url
        self.mas_url = mas_url
        self.check_interval = check_interval
        self.errors: List[WorkflowError] = []
        self.patterns: Dict[str, ErrorPattern] = {}
        self.improvements: List[ImprovementSuggestion] = []
        self._running = False
        
    async def start(self):
        """Start the debug monitoring loop"""
        self._running = True
        logger.info("DebugAgent started - monitoring for errors...")
        
        while self._running:
            try:
                await self._check_n8n_executions()
                await self._check_docker_health()
                await self._check_mas_agents()
                await self._analyze_patterns()
                await self._report_to_orchestrator()
            except Exception as e:
                logger.error(f"DebugAgent error: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the monitoring loop"""
        self._running = False
        
    async def _check_n8n_executions(self):
        """Check N8n for failed workflow executions"""
        try:
            async with httpx.AsyncClient() as client:
                # Get recent executions (would need API key in production)
                # For now, we'll check via the webhook
                response = await client.get(
                    f"{self.n8n_url}/rest/executions",
                    params={"filter": '{"status":"error"}', "limit": 50},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for execution in data.get("data", []):
                        error = self._parse_execution_error(execution)
                        if error and not self._is_duplicate_error(error):
                            self.errors.append(error)
                            await self._handle_new_error(error)
        except Exception as e:
            logger.debug(f"N8n check failed (expected if no API key): {e}")
    
    async def _check_docker_health(self):
        """Check Docker container health status"""
        # This would use Docker SDK in production
        unhealthy_services = []
        
        # Known services to check
        services = [
            ("mas-orchestrator", f"{self.mas_url}/health"),
            ("n8n", f"{self.n8n_url}/healthz"),
            ("postgres", None),  # Would check via pg_isready
            ("redis", None),  # Would check via redis-cli ping
            ("qdrant", "http://localhost:6345/collections"),
        ]
        
        async with httpx.AsyncClient() as client:
            for service_name, health_url in services:
                if health_url:
                    try:
                        response = await client.get(health_url, timeout=5.0)
                        if response.status_code >= 400:
                            unhealthy_services.append(service_name)
                    except Exception:
                        unhealthy_services.append(service_name)
        
        if unhealthy_services:
            self.improvements.append(ImprovementSuggestion(
                suggestion_id=f"service_health_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                category="infrastructure",
                priority="critical",
                title=f"Unhealthy services detected: {', '.join(unhealthy_services)}",
                description=f"The following services are not responding: {unhealthy_services}",
                affected_components=unhealthy_services,
                estimated_impact="System functionality degraded",
                auto_fixable=True,
                fix_code=f"docker compose restart {' '.join(unhealthy_services)}"
            ))
    
    async def _check_mas_agents(self):
        """Check MAS agent health and activity"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.mas_url}/agents/registry/",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    inactive_agents = [
                        a for a in data.get("agents", [])
                        if a.get("status") == "error" or a.get("last_activity") is None
                    ]
                    
                    if len(inactive_agents) > 10:
                        self.improvements.append(ImprovementSuggestion(
                            suggestion_id=f"agent_health_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            category="service",
                            priority="high",
                            title=f"{len(inactive_agents)} agents inactive",
                            description="Multiple agents are not active or have errors",
                            affected_components=[a.get("name", "unknown") for a in inactive_agents[:5]],
                            estimated_impact="Reduced system capabilities",
                            auto_fixable=True,
                            fix_code="POST /runner/start to activate agents"
                        ))
        except Exception as e:
            logger.debug(f"MAS agent check failed: {e}")
    
    async def _analyze_patterns(self):
        """Analyze error patterns to identify recurring issues"""
        if len(self.errors) < 3:
            return
        
        # Group errors by workflow and error type
        error_groups: Dict[str, List[WorkflowError]] = {}
        for error in self.errors[-100:]:  # Last 100 errors
            key = f"{error.workflow_name}:{error.node_name}"
            if key not in error_groups:
                error_groups[key] = []
            error_groups[key].append(error)
        
        # Identify patterns (3+ occurrences)
        for key, errors in error_groups.items():
            if len(errors) >= 3:
                pattern = ErrorPattern(
                    pattern_id=f"pattern_{hash(key) % 10000:04d}",
                    error_type=key,
                    affected_workflows=list(set(e.workflow_name for e in errors)),
                    occurrence_count=len(errors),
                    first_seen=min(e.timestamp for e in errors),
                    last_seen=max(e.timestamp for e in errors),
                    auto_fixable=self._is_auto_fixable(errors[0]),
                )
                pattern.suggested_fixes = self._generate_fixes(errors)
                self.patterns[key] = pattern
    
    def _is_auto_fixable(self, error: WorkflowError) -> bool:
        """Determine if an error can be automatically fixed"""
        auto_fixable_patterns = [
            "service unavailable",
            "connection refused",
            "timeout",
            "health check failed",
            "hasn't been executed",
        ]
        
        error_lower = error.error_message.lower()
        return any(pattern in error_lower for pattern in auto_fixable_patterns)
    
    def _generate_fixes(self, errors: List[WorkflowError]) -> List[str]:
        """Generate fix suggestions for error pattern"""
        fixes = []
        error = errors[0]
        
        if "connection refused" in error.error_message.lower():
            fixes.append(f"Restart the service that {error.node_name} is trying to connect to")
            fixes.append("Check Docker container health: docker compose ps")
            
        if "timeout" in error.error_message.lower():
            fixes.append("Increase timeout settings in the workflow node")
            fixes.append("Check network connectivity between services")
            
        if "hasn't been executed" in error.error_message.lower():
            fixes.append("Add error handling to the Aggregate Results node")
            fixes.append("Make the Check TTS node failure non-blocking")
            
        if "health" in error.error_message.lower():
            fixes.append("Check that all dependent services are running")
            fixes.append("Verify health endpoints are correctly configured")
            
        return fixes
    
    def _parse_execution_error(self, execution: Dict) -> Optional[WorkflowError]:
        """Parse N8n execution data into WorkflowError"""
        try:
            error_data = execution.get("data", {}).get("resultData", {}).get("error", {})
            return WorkflowError(
                execution_id=str(execution.get("id")),
                workflow_id=execution.get("workflowId", ""),
                workflow_name=execution.get("workflowData", {}).get("name", "Unknown"),
                error_message=error_data.get("message", "Unknown error"),
                node_name=error_data.get("node", "Unknown"),
                timestamp=datetime.fromisoformat(execution.get("startedAt", datetime.now().isoformat())),
                run_time_ms=int(execution.get("stoppedAt", 0)) - int(execution.get("startedAt", 0)),
                stack_trace=error_data.get("stack"),
            )
        except Exception:
            return None
    
    def _is_duplicate_error(self, error: WorkflowError) -> bool:
        """Check if error is a duplicate of recent error"""
        for existing in self.errors[-10:]:
            if (existing.workflow_name == error.workflow_name and 
                existing.node_name == error.node_name and
                existing.error_message == error.error_message):
                return True
        return False
    
    async def _handle_new_error(self, error: WorkflowError):
        """Handle a newly detected error"""
        logger.warning(f"New error in {error.workflow_name}: {error.error_message}")
        
        # Generate suggested fix
        error.suggested_fix = await self._get_ai_fix_suggestion(error)
        
        # Notify orchestrator
        await self._notify_orchestrator(error)
    
    async def _get_ai_fix_suggestion(self, error: WorkflowError) -> str:
        """Use AI to generate fix suggestion"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mas_url}/voice/orchestrator/chat",
                    json={
                        "message": f"""Analyze this workflow error and suggest a fix:
Workflow: {error.workflow_name}
Node: {error.node_name}
Error: {error.error_message}

Provide a concise fix suggestion.""",
                        "context": {"intent": "debug"}
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "No suggestion available")
        except Exception as e:
            logger.debug(f"AI fix suggestion failed: {e}")
        
        return "Check service health and restart if needed"
    
    async def _notify_orchestrator(self, error: WorkflowError):
        """Notify MYCA orchestrator about the error"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.mas_url}/tasks/submit",
                    json={
                        "type": "debug_alert",
                        "priority": "high",
                        "data": {
                            "workflow_name": error.workflow_name,
                            "error_message": error.error_message,
                            "node_name": error.node_name,
                            "suggested_fix": error.suggested_fix,
                            "timestamp": error.timestamp.isoformat(),
                        }
                    },
                    timeout=10.0
                )
        except Exception as e:
            logger.debug(f"Orchestrator notification failed: {e}")
    
    async def _report_to_orchestrator(self):
        """Send periodic summary report to orchestrator"""
        if not self.patterns and not self.improvements:
            return
        
        report = self.generate_report()
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.mas_url}/tasks/submit",
                    json={
                        "type": "debug_report",
                        "priority": "medium",
                        "data": report
                    },
                    timeout=10.0
                )
        except Exception as e:
            logger.debug(f"Report submission failed: {e}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive debug report"""
        return {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_errors": len(self.errors),
                "unique_patterns": len(self.patterns),
                "improvements_suggested": len(self.improvements),
            },
            "error_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "error_type": p.error_type,
                    "occurrences": p.occurrence_count,
                    "first_seen": p.first_seen.isoformat(),
                    "last_seen": p.last_seen.isoformat(),
                    "auto_fixable": p.auto_fixable,
                    "suggested_fixes": p.suggested_fixes,
                }
                for p in self.patterns.values()
            ],
            "improvements": [
                {
                    "id": i.suggestion_id,
                    "category": i.category,
                    "priority": i.priority,
                    "title": i.title,
                    "description": i.description,
                    "auto_fixable": i.auto_fixable,
                }
                for i in self.improvements
            ],
            "efficiency_metrics": self._calculate_efficiency_metrics(),
        }
    
    def _calculate_efficiency_metrics(self) -> Dict[str, Any]:
        """Calculate system efficiency metrics"""
        if not self.errors:
            return {"error_rate": 0, "avg_resolution_time": 0, "improvement_rate": 0}
        
        recent_errors = [e for e in self.errors if e.timestamp > datetime.now() - timedelta(hours=1)]
        
        return {
            "errors_per_hour": len(recent_errors),
            "most_problematic_workflow": self._get_most_problematic_workflow(),
            "auto_fixable_percentage": sum(1 for p in self.patterns.values() if p.auto_fixable) / max(len(self.patterns), 1) * 100,
            "critical_issues": len([i for i in self.improvements if i.priority == "critical"]),
        }
    
    def _get_most_problematic_workflow(self) -> Optional[str]:
        """Get the workflow with most errors"""
        if not self.errors:
            return None
        
        workflow_counts: Dict[str, int] = {}
        for error in self.errors:
            workflow_counts[error.workflow_name] = workflow_counts.get(error.workflow_name, 0) + 1
        
        return max(workflow_counts, key=workflow_counts.get) if workflow_counts else None


# Create global debug agent instance
debug_agent = DebugAgent()


async def start_debug_agent():
    """Start the debug agent as a background task"""
    await debug_agent.start()


def get_debug_report() -> Dict[str, Any]:
    """Get the current debug report"""
    return debug_agent.generate_report()

