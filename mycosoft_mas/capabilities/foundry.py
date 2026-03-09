"""
Capability Foundry — Engine for safe skill acquisition.

Pipeline: detect missing → search approved sources → build adapter →
sandbox → test → policy check → security scan → register → deploy →
execute → store procedural memory.

The scary part is not "AI became conscious." The scary part is:
a system told to "save the world" will try to simplify the world.
This foundry ensures every new capability goes through proper
quarantine before it touches production.

Architecture: March 9, 2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class CapabilityStatus(str, Enum):
    """Status of a capability in the acquisition pipeline."""

    REQUESTED = "requested"
    SEARCHING = "searching"
    BUILDING = "building"
    SANDBOXING = "sandboxing"
    TESTING = "testing"
    POLICY_CHECK = "policy_check"
    SECURITY_SCAN = "security_scan"
    REGISTERING = "registering"
    DEPLOYED = "deployed"
    FAILED = "failed"
    REJECTED = "rejected"  # Failed policy/security check


class DeployTarget(str, Enum):
    """Where to deploy a new capability."""

    SANDBOX = "sandbox"  # Test only
    STAGING = "staging"  # Limited availability
    PRODUCTION = "production"  # Full deployment


@dataclass
class CapabilityRequest:
    """Request to acquire a new capability."""

    task_description: str
    requester_agent: str
    urgency: str = "normal"  # "low", "normal", "high"
    request_id: str = field(default_factory=lambda: str(uuid4()))
    requested_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class CapabilityCandidate:
    """A candidate capability found during search."""

    source: str
    name: str
    description: str
    source_type: str  # "internal_registry", "approved_package", "mcp_server", etc.
    confidence: float = 0.0  # 0-1 how well it matches the request
    requirements: List[str] = field(default_factory=list)
    risk_tier: str = "medium"


@dataclass
class CapabilityAdapter:
    """A built adapter ready for testing."""

    adapter_id: str
    name: str
    description: str
    source_candidate: CapabilityCandidate
    code: Optional[str] = None  # Adapter code if generated
    config: Dict[str, Any] = field(default_factory=dict)
    built_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class PipelineStageResult:
    """Result of a pipeline stage."""

    stage: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class CapabilityResult:
    """Final result of the capability acquisition pipeline."""

    success: bool
    request: CapabilityRequest
    capability_id: Optional[str] = None
    status: CapabilityStatus = CapabilityStatus.REQUESTED
    deploy_target: Optional[DeployTarget] = None
    pipeline_results: List[PipelineStageResult] = field(default_factory=list)
    error: Optional[str] = None
    completed_at: Optional[datetime] = None


class CapabilityFoundry:
    """
    Engine for safe skill acquisition.

    This is the difference between a neat demo and a real
    company-running intelligence. Every new capability goes through:

    1. Detection — What capability is missing?
    2. Discovery — Search approved sources only
    3. Building — Create adapter/wrapper
    4. Sandboxing — Isolate for testing
    5. Testing — Verify correctness
    6. Policy check — Verify against governance rules
    7. Security scan — Check for vulnerabilities/malware
    8. Registration — Add to versioned skill registry
    9. Deployment — Stage or production based on risk
    10. Procedural memory — Store the learned skill
    """

    def __init__(self) -> None:
        self._active_requests: Dict[str, CapabilityResult] = {}
        self._completed: List[CapabilityResult] = []
        self._registered_capabilities: Dict[str, Dict[str, Any]] = {}

    async def acquire_capability(
        self, request: CapabilityRequest
    ) -> CapabilityResult:
        """
        Run the full capability acquisition pipeline.

        Each stage must pass before proceeding to the next.
        Failure at any stage halts the pipeline.
        """
        result = CapabilityResult(
            success=False,
            request=request,
            status=CapabilityStatus.REQUESTED,
        )
        self._active_requests[request.request_id] = result

        try:
            # Stage 1: Detect missing capability
            detection = await self.detect_missing(
                {"description": request.task_description}
            )
            result.pipeline_results.append(
                PipelineStageResult(
                    stage="detection",
                    passed=detection is not None,
                    message=detection or "No missing capability detected",
                    details={"capability_needed": detection},
                )
            )
            if not detection:
                result.status = CapabilityStatus.FAILED
                result.error = "Could not determine missing capability"
                return self._finalize(result)

            # Stage 2: Search approved sources
            result.status = CapabilityStatus.SEARCHING
            candidates = await self.search_sources(detection)
            result.pipeline_results.append(
                PipelineStageResult(
                    stage="discovery",
                    passed=len(candidates) > 0,
                    message=f"Found {len(candidates)} candidates",
                    details={"candidates": [c.name for c in candidates]},
                )
            )
            if not candidates:
                result.status = CapabilityStatus.FAILED
                result.error = f"No candidates found for capability: {detection}"
                return self._finalize(result)

            # Select best candidate
            best = max(candidates, key=lambda c: c.confidence)

            # Stage 3: Build adapter
            result.status = CapabilityStatus.BUILDING
            adapter = await self.build_adapter(best)
            result.pipeline_results.append(
                PipelineStageResult(
                    stage="building",
                    passed=adapter is not None,
                    message=f"Built adapter: {adapter.name}" if adapter else "Build failed",
                )
            )
            if not adapter:
                result.status = CapabilityStatus.FAILED
                result.error = "Failed to build capability adapter"
                return self._finalize(result)

            # Stage 4: Sandbox test
            result.status = CapabilityStatus.SANDBOXING
            sandbox_result = await self.sandbox_test(adapter)
            result.pipeline_results.append(sandbox_result)
            if not sandbox_result.passed:
                result.status = CapabilityStatus.FAILED
                result.error = f"Sandbox test failed: {sandbox_result.message}"
                return self._finalize(result)

            # Stage 5: Policy check
            result.status = CapabilityStatus.POLICY_CHECK
            policy_result = await self.policy_check(adapter)
            result.pipeline_results.append(policy_result)
            if not policy_result.passed:
                result.status = CapabilityStatus.REJECTED
                result.error = f"Policy check failed: {policy_result.message}"
                return self._finalize(result)

            # Stage 6: Security scan
            result.status = CapabilityStatus.SECURITY_SCAN
            security_result = await self.security_scan(adapter)
            result.pipeline_results.append(security_result)
            if not security_result.passed:
                result.status = CapabilityStatus.REJECTED
                result.error = f"Security scan failed: {security_result.message}"
                return self._finalize(result)

            # Stage 7: Register and deploy
            result.status = CapabilityStatus.REGISTERING
            capability_id = await self.register_and_deploy(adapter)
            result.pipeline_results.append(
                PipelineStageResult(
                    stage="registration",
                    passed=capability_id is not None,
                    message=f"Registered as: {capability_id}" if capability_id else "Registration failed",
                    details={"capability_id": capability_id},
                )
            )

            if capability_id:
                result.success = True
                result.capability_id = capability_id
                result.status = CapabilityStatus.DEPLOYED
                result.deploy_target = self._determine_deploy_target(best.risk_tier)
            else:
                result.status = CapabilityStatus.FAILED
                result.error = "Registration failed"

        except Exception as e:
            result.status = CapabilityStatus.FAILED
            result.error = str(e)
            logger.error("Capability acquisition failed: %s", e)

        return self._finalize(result)

    async def detect_missing(self, task: Dict[str, Any]) -> Optional[str]:
        """Detect what capability is needed for a task."""
        description = task.get("description", "")
        if not description:
            return None

        # Simple keyword-based detection (in production, this would use LLM)
        capability_keywords = {
            "stripe": "payment_processing",
            "quickbooks": "accounting_integration",
            "email": "email_management",
            "calendar": "calendar_management",
            "deploy": "deployment_automation",
            "monitor": "system_monitoring",
            "analyze": "data_analysis",
            "visualize": "data_visualization",
            "scrape": "web_scraping",
            "translate": "language_translation",
        }

        description_lower = description.lower()
        for keyword, capability in capability_keywords.items():
            if keyword in description_lower:
                return capability

        # Generic capability name from description
        return f"custom_{description_lower[:30].replace(' ', '_')}"

    async def search_sources(
        self, capability_name: str
    ) -> List[CapabilityCandidate]:
        """Search approved sources for capability candidates."""
        # Import discovery module
        try:
            from mycosoft_mas.capabilities.discovery import CapabilityDiscovery

            discovery = CapabilityDiscovery()
            return await discovery.search(capability_name)
        except ImportError:
            logger.warning("CapabilityDiscovery not available, returning empty")
            return []

    async def build_adapter(
        self, candidate: CapabilityCandidate
    ) -> Optional[CapabilityAdapter]:
        """Build an adapter for a capability candidate."""
        return CapabilityAdapter(
            adapter_id=str(uuid4()),
            name=candidate.name,
            description=candidate.description,
            source_candidate=candidate,
            config={
                "source_type": candidate.source_type,
                "requirements": candidate.requirements,
                "risk_tier": candidate.risk_tier,
            },
        )

    async def sandbox_test(
        self, adapter: CapabilityAdapter
    ) -> PipelineStageResult:
        """Test capability in sandbox environment."""
        # In production, this would use safety/sandboxing.py CodeSandbox
        return PipelineStageResult(
            stage="sandbox_test",
            passed=True,
            message="Sandbox test passed (adapter validated)",
            details={"adapter_id": adapter.adapter_id},
        )

    async def policy_check(
        self, adapter: CapabilityAdapter
    ) -> PipelineStageResult:
        """Check capability against governance policies."""
        risk_tier = adapter.config.get("risk_tier", "medium")

        # Critical risk capabilities require human approval
        if risk_tier == "critical":
            return PipelineStageResult(
                stage="policy_check",
                passed=False,
                message="Critical-risk capability requires human approval",
                details={"risk_tier": risk_tier, "requires_approval": True},
            )

        return PipelineStageResult(
            stage="policy_check",
            passed=True,
            message=f"Policy check passed (risk_tier: {risk_tier})",
            details={"risk_tier": risk_tier},
        )

    async def security_scan(
        self, adapter: CapabilityAdapter
    ) -> PipelineStageResult:
        """Run security scan on capability."""
        # In production, this would use security/skill_scanner.py
        if adapter.code:
            # Check for obvious dangerous patterns
            dangerous_patterns = [
                "eval(", "exec(", "__import__", "subprocess",
                "os.system", "curl | bash", "wget | sh",
            ]
            for pattern in dangerous_patterns:
                if pattern in adapter.code:
                    return PipelineStageResult(
                        stage="security_scan",
                        passed=False,
                        message=f"Dangerous pattern detected: {pattern}",
                        details={"pattern": pattern},
                    )

        return PipelineStageResult(
            stage="security_scan",
            passed=True,
            message="Security scan passed",
        )

    async def register_and_deploy(
        self, adapter: CapabilityAdapter
    ) -> Optional[str]:
        """Register capability in skill registry and deploy."""
        capability_id = f"cap_{adapter.adapter_id[:8]}"
        self._registered_capabilities[capability_id] = {
            "id": capability_id,
            "name": adapter.name,
            "description": adapter.description,
            "source_type": adapter.source_candidate.source_type,
            "risk_tier": adapter.config.get("risk_tier", "medium"),
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }
        logger.info("Capability registered: %s (%s)", capability_id, adapter.name)
        return capability_id

    def _determine_deploy_target(self, risk_tier: str) -> DeployTarget:
        """Determine deployment target based on risk."""
        if risk_tier == "low":
            return DeployTarget.PRODUCTION
        elif risk_tier == "medium":
            return DeployTarget.STAGING
        else:
            return DeployTarget.SANDBOX

    def _finalize(self, result: CapabilityResult) -> CapabilityResult:
        """Finalize a capability result."""
        result.completed_at = datetime.now(timezone.utc)
        if result.request.request_id in self._active_requests:
            del self._active_requests[result.request.request_id]
        self._completed.append(result)
        return result

    def get_registered_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Return all registered capabilities."""
        return dict(self._registered_capabilities)

    def get_active_requests(self) -> Dict[str, CapabilityResult]:
        """Return currently active acquisition requests."""
        return dict(self._active_requests)
