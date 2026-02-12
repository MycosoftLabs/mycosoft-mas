"""
Deployment Feedback Service for Auto-Learning System.
Created: February 12, 2026

Monitors deployments and learns from them:
- Monitor deployment health
- Track success/failure rates
- Learn from deployment patterns
- Auto-rollback on failures
- Feed results back to learning system

Used by the autonomous operator and deployment pipeline.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

try:
    import httpx
except ImportError:
    httpx = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DeploymentFeedback")


@dataclass
class DeploymentRecord:
    """Record of a deployment."""
    deployment_id: str
    target: str  # sandbox, mas, mindex, website
    version: str
    commit_sha: Optional[str] = None
    status: str = "pending"  # pending, deploying, success, failed, rolled_back
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    health_check_passed: bool = False
    error_message: Optional[str] = None
    rollback_triggered: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    target: str
    endpoint: str
    status_code: int
    response_time_ms: float
    healthy: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None


class DeploymentFeedbackService:
    """
    Service for monitoring deployments and learning from them.
    
    Features:
    - Deployment tracking with persistence
    - Health check monitoring
    - Automatic rollback on failure
    - Success rate analysis
    - Deployment pattern learning
    """
    
    # VM configuration
    TARGETS = {
        "sandbox": {
            "ip": "192.168.0.187",
            "health_endpoint": "http://192.168.0.187:3000/api/health",
            "service": "website"
        },
        "mas": {
            "ip": "192.168.0.188",
            "health_endpoint": "http://192.168.0.188:8001/health",
            "service": "orchestrator"
        },
        "mindex": {
            "ip": "192.168.0.189",
            "health_endpoint": "http://192.168.0.189:8000/health",
            "service": "mindex-api"
        },
        "website": {
            "ip": "192.168.0.187",
            "health_endpoint": "http://192.168.0.187:3000/api/health",
            "service": "website"
        }
    }
    
    def __init__(self, data_dir: Optional[str] = None):
        self._data_dir = Path(data_dir or os.path.join(
            os.path.dirname(__file__), "../../data/deployments"
        ))
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        self._deployments: List[DeploymentRecord] = []
        self._health_history: Dict[str, List[HealthCheckResult]] = {}
        self._client: Optional["httpx.AsyncClient"] = None
        
        self._load_data()
    
    def _load_data(self) -> None:
        """Load persisted data."""
        deployments_file = self._data_dir / "deployments.json"
        if deployments_file.exists():
            try:
                with open(deployments_file, "r") as f:
                    data = json.load(f)
                    self._deployments = [DeploymentRecord(**d) for d in data]
            except Exception as e:
                logger.error(f"Failed to load deployments: {e}")
    
    def _save_data(self) -> None:
        """Persist data to disk."""
        deployments_file = self._data_dir / "deployments.json"
        recent = self._deployments[-500:]  # Keep last 500
        
        with open(deployments_file, "w") as f:
            json.dump([
                {
                    "deployment_id": d.deployment_id, "target": d.target,
                    "version": d.version, "commit_sha": d.commit_sha,
                    "status": d.status, "started_at": d.started_at,
                    "completed_at": d.completed_at,
                    "duration_seconds": d.duration_seconds,
                    "health_check_passed": d.health_check_passed,
                    "error_message": d.error_message,
                    "rollback_triggered": d.rollback_triggered,
                    "metadata": d.metadata
                }
                for d in recent
            ], f, indent=2)
    
    async def _get_client(self) -> Optional["httpx.AsyncClient"]:
        """Get or create HTTP client."""
        if not httpx:
            return None
        if not self._client:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client
    
    def start_deployment(
        self,
        target: str,
        version: str,
        commit_sha: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start tracking a new deployment."""
        deployment = DeploymentRecord(
            deployment_id=str(uuid4())[:8],
            target=target,
            version=version,
            commit_sha=commit_sha,
            status="deploying",
            metadata=metadata or {}
        )
        
        self._deployments.append(deployment)
        logger.info(f"Started deployment {deployment.deployment_id} to {target}")
        return deployment.deployment_id
    
    def update_deployment(
        self,
        deployment_id: str,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update deployment status."""
        for deployment in self._deployments:
            if deployment.deployment_id == deployment_id:
                if status:
                    deployment.status = status
                    if status in ["success", "failed", "rolled_back"]:
                        deployment.completed_at = datetime.now(timezone.utc).isoformat()
                        started = datetime.fromisoformat(deployment.started_at.replace("Z", "+00:00"))
                        completed = datetime.fromisoformat(deployment.completed_at.replace("Z", "+00:00"))
                        deployment.duration_seconds = (completed - started).total_seconds()
                
                if error_message:
                    deployment.error_message = error_message
                
                if metadata:
                    deployment.metadata.update(metadata)
                
                self._save_data()
                return True
        
        return False
    
    async def check_health(self, target: str) -> HealthCheckResult:
        """Check health of a deployment target."""
        config = self.TARGETS.get(target)
        if not config:
            return HealthCheckResult(
                target=target,
                endpoint="unknown",
                status_code=0,
                response_time_ms=0,
                healthy=False,
                error=f"Unknown target: {target}"
            )
        
        endpoint = config["health_endpoint"]
        client = await self._get_client()
        
        if not client:
            return HealthCheckResult(
                target=target,
                endpoint=endpoint,
                status_code=0,
                response_time_ms=0,
                healthy=False,
                error="HTTP client not available"
            )
        
        try:
            start_time = time.time()
            response = await client.get(endpoint)
            response_time = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                target=target,
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=response_time,
                healthy=response.status_code == 200
            )
        
        except Exception as e:
            result = HealthCheckResult(
                target=target,
                endpoint=endpoint,
                status_code=0,
                response_time_ms=0,
                healthy=False,
                error=str(e)
            )
        
        # Store in history
        if target not in self._health_history:
            self._health_history[target] = []
        self._health_history[target].append(result)
        
        # Keep last 100 checks per target
        self._health_history[target] = self._health_history[target][-100:]
        
        return result
    
    async def verify_deployment(
        self,
        deployment_id: str,
        max_attempts: int = 10,
        delay_seconds: int = 5
    ) -> bool:
        """Verify a deployment succeeded with health checks."""
        deployment = None
        for d in self._deployments:
            if d.deployment_id == deployment_id:
                deployment = d
                break
        
        if not deployment:
            logger.error(f"Deployment not found: {deployment_id}")
            return False
        
        target = deployment.target
        logger.info(f"Verifying deployment {deployment_id} to {target}...")
        
        for attempt in range(max_attempts):
            result = await self.check_health(target)
            
            if result.healthy:
                deployment.health_check_passed = True
                deployment.status = "success"
                deployment.completed_at = datetime.now(timezone.utc).isoformat()
                started = datetime.fromisoformat(deployment.started_at.replace("Z", "+00:00"))
                completed = datetime.fromisoformat(deployment.completed_at.replace("Z", "+00:00"))
                deployment.duration_seconds = (completed - started).total_seconds()
                
                self._save_data()
                logger.info(f"Deployment {deployment_id} verified successfully")
                return True
            
            logger.info(f"Health check attempt {attempt + 1}/{max_attempts} failed, retrying...")
            await asyncio.sleep(delay_seconds)
        
        # Failed after all attempts
        deployment.status = "failed"
        deployment.health_check_passed = False
        deployment.error_message = "Health check failed after all attempts"
        self._save_data()
        
        logger.error(f"Deployment {deployment_id} verification failed")
        return False
    
    def should_rollback(self, deployment_id: str) -> bool:
        """Determine if a deployment should be rolled back."""
        for d in self._deployments:
            if d.deployment_id == deployment_id:
                return d.status == "failed" and not d.rollback_triggered
        return False
    
    def mark_rollback(self, deployment_id: str) -> bool:
        """Mark a deployment as rolled back."""
        for d in self._deployments:
            if d.deployment_id == deployment_id:
                d.rollback_triggered = True
                d.status = "rolled_back"
                self._save_data()
                return True
        return False
    
    def get_success_rate(self, target: Optional[str] = None, days: int = 30) -> float:
        """Get deployment success rate."""
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
        
        relevant = []
        for d in self._deployments:
            if target and d.target != target:
                continue
            
            try:
                started = datetime.fromisoformat(d.started_at.replace("Z", "+00:00"))
                if started.timestamp() >= cutoff:
                    relevant.append(d)
            except Exception:
                pass
        
        if not relevant:
            return 0.0
        
        successful = sum(1 for d in relevant if d.status == "success")
        return successful / len(relevant)
    
    def get_average_duration(self, target: Optional[str] = None) -> float:
        """Get average deployment duration in seconds."""
        durations = []
        for d in self._deployments:
            if target and d.target != target:
                continue
            if d.duration_seconds:
                durations.append(d.duration_seconds)
        
        return sum(durations) / len(durations) if durations else 0.0
    
    def get_common_failures(self, target: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most common failure patterns."""
        failures: Dict[str, int] = {}
        
        for d in self._deployments:
            if target and d.target != target:
                continue
            if d.status == "failed" and d.error_message:
                key = d.error_message[:100]
                failures[key] = failures.get(key, 0) + 1
        
        sorted_failures = sorted(failures.items(), key=lambda x: x[1], reverse=True)
        return [
            {"error": err, "count": count}
            for err, count in sorted_failures[:limit]
        ]
    
    def get_deployment_report(self, target: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive deployment report."""
        relevant = [d for d in self._deployments if not target or d.target == target]
        
        return {
            "total_deployments": len(relevant),
            "success_rate_30d": self.get_success_rate(target, 30),
            "success_rate_7d": self.get_success_rate(target, 7),
            "average_duration_seconds": self.get_average_duration(target),
            "common_failures": self.get_common_failures(target, 5),
            "recent_deployments": [
                {
                    "id": d.deployment_id,
                    "target": d.target,
                    "status": d.status,
                    "version": d.version,
                    "duration": d.duration_seconds,
                    "started_at": d.started_at
                }
                for d in reversed(relevant[-10:])
            ],
            "targets": list(self.TARGETS.keys())
        }
    
    def get_learning_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations based on deployment patterns."""
        recommendations = []
        
        for target in self.TARGETS:
            rate = self.get_success_rate(target, 7)
            if rate < 0.8 and len([d for d in self._deployments if d.target == target]) >= 5:
                failures = self.get_common_failures(target, 3)
                recommendations.append({
                    "type": "low_success_rate",
                    "target": target,
                    "success_rate": rate,
                    "recommendation": f"Review deployment process for {target}",
                    "common_issues": [f["error"][:50] for f in failures]
                })
            
            avg_duration = self.get_average_duration(target)
            if avg_duration > 300:  # > 5 minutes
                recommendations.append({
                    "type": "slow_deployment",
                    "target": target,
                    "avg_duration_seconds": avg_duration,
                    "recommendation": f"Optimize deployment pipeline for {target}"
                })
        
        return recommendations
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._client:
            await self._client.aclose()


# Singleton instance
_service: Optional[DeploymentFeedbackService] = None


def get_deployment_service() -> DeploymentFeedbackService:
    """Get or create the singleton deployment service."""
    global _service
    if _service is None:
        _service = DeploymentFeedbackService()
    return _service


async def main():
    """Test the deployment feedback service."""
    service = get_deployment_service()
    
    # Start a test deployment
    dep_id = service.start_deployment(
        target="sandbox",
        version="1.0.0",
        commit_sha="abc123"
    )
    
    # Check health
    print("\nChecking health...")
    result = await service.check_health("sandbox")
    print(f"Health check: {result.healthy} ({result.status_code})")
    
    # Update deployment
    if result.healthy:
        service.update_deployment(dep_id, status="success")
    else:
        service.update_deployment(dep_id, status="failed", error_message=result.error)
    
    # Get report
    report = service.get_deployment_report()
    print("\n=== Deployment Report ===")
    print(f"Total deployments: {report['total_deployments']}")
    print(f"7-day success rate: {report['success_rate_7d']:.0%}")
    print(f"Avg duration: {report['average_duration_seconds']:.1f}s")
    
    recommendations = service.get_learning_recommendations()
    if recommendations:
        print("\nRecommendations:")
        for rec in recommendations:
            print(f"  - {rec['recommendation']}")
    
    await service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
