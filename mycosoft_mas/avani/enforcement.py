"""Shared AVANI action preflight helpers.

MYCA and MAS routes use this module to normalize action-capable requests before
execution. The caller supplies the active AVANI governor so router and in-process
checks share the same season state and audit ledger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from mycosoft_mas.avani.governor.governor import AvaniGovernor, Proposal, RiskTier


HIGH_IMPACT_ACTIONS = frozenset(
    {
        "agent_dispatch",
        "device_control",
        "earth_sim_command",
        "execute_workflow",
        "model_promotion",
        "red_team",
        "system_config",
        "tool_execution",
        "workflow",
    }
)
MEDIUM_IMPACT_ACTIONS = frozenset(
    {
        "data_access",
        "generate_workflow",
        "grounding",
        "omnichannel_send",
        "worldview_release",
    }
)


@dataclass(frozen=True)
class AvaniActionPreflight:
    source_agent: str
    action_type: str
    description: str
    route: str = ""
    risk_tier: str = "low"
    ecological_impact: float = 0.0
    reversibility: float = 1.0
    operator_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AvaniActionPolicy:
    """Static route policy for action-capable MAS/MYCA surfaces."""

    route: str
    action_type: str
    risk_tier: str
    reversibility: float
    fail_closed: bool = True
    ecological_impact: float = 0.0


ACTION_ROUTE_POLICIES: Dict[str, AvaniActionPolicy] = {
    "/api/deploy/trigger": AvaniActionPolicy("/api/deploy/trigger", "system_config", "high", 0.4),
    "/api/deploy/autonomous-fix": AvaniActionPolicy("/api/deploy/autonomous-fix", "system_config", "high", 0.4),
    "/tools/execute": AvaniActionPolicy("/tools/execute", "tool_execution", "high", 0.6),
    "/tools/execute/batch": AvaniActionPolicy("/tools/execute/batch", "tool_execution", "high", 0.6),
    "/workflows/execute": AvaniActionPolicy("/workflows/execute", "execute_workflow", "high", 0.6),
    "/workflows/create": AvaniActionPolicy("/workflows/create", "workflow", "high", 0.7),
    "/workflows/{workflow_id}": AvaniActionPolicy("/workflows/{workflow_id}", "workflow", "high", 0.6),
    "/workflows/{workflow_id}/activate": AvaniActionPolicy("/workflows/{workflow_id}/activate", "workflow", "high", 0.6),
    "/workflows/{workflow_id}/deactivate": AvaniActionPolicy("/workflows/{workflow_id}/deactivate", "workflow", "medium", 0.8),
    "/workflows/{workflow_id}/archive": AvaniActionPolicy("/workflows/{workflow_id}/archive", "workflow", "medium", 0.8),
    "/workflows/{workflow_id}/restore": AvaniActionPolicy("/workflows/{workflow_id}/restore", "workflow", "high", 0.6),
    "/workflows/sync": AvaniActionPolicy("/workflows/sync", "workflow", "high", 0.6),
    "/workflows/sync-both": AvaniActionPolicy("/workflows/sync-both", "workflow", "high", 0.6),
    "/workflows/export-all": AvaniActionPolicy("/workflows/export-all", "data_access", "medium", 1.0),
    "/workflows/{workflow_id}/export": AvaniActionPolicy("/workflows/{workflow_id}/export", "data_access", "medium", 1.0),
    "/workflows/{workflow_id}/clone": AvaniActionPolicy("/workflows/{workflow_id}/clone", "workflow", "high", 0.7),
    "/workflows/scheduler/start": AvaniActionPolicy("/workflows/scheduler/start", "workflow", "high", 0.5),
    "/workflows/scheduler/stop": AvaniActionPolicy("/workflows/scheduler/stop", "workflow", "medium", 0.8),
    "/api/devices/{device_id}/command": AvaniActionPolicy("/api/devices/{device_id}/command", "device_control", "high", 0.6, ecological_impact=0.3),
    "/api/devices/{device_id}": AvaniActionPolicy("/api/devices/{device_id}", "device_control", "medium", 0.8),
    "/api/devices/{device_id}/fci-summary": AvaniActionPolicy("/api/devices/{device_id}/fci-summary", "grounding", "medium", 1.0),
    "/api/iot/fleet/bulk/commands": AvaniActionPolicy("/api/iot/fleet/bulk/commands", "device_control", "high", 0.5, ecological_impact=0.3),
    "/api/iot/fleet/firmware/deploy": AvaniActionPolicy("/api/iot/fleet/firmware/deploy", "device_control", "high", 0.4),
    "/api/iot/fleet/provisioning": AvaniActionPolicy("/api/iot/fleet/provisioning", "device_control", "medium", 0.8),
    "/api/earth2/forecast": AvaniActionPolicy("/api/earth2/forecast", "earth_sim_command", "medium", 1.0, fail_closed=False),
    "/api/earth2/nowcast": AvaniActionPolicy("/api/earth2/nowcast", "earth_sim_command", "medium", 1.0, fail_closed=False),
    "/api/earth2/downscale": AvaniActionPolicy("/api/earth2/downscale", "earth_sim_command", "high", 0.9),
    "/api/earth2/spore-dispersal": AvaniActionPolicy("/api/earth2/spore-dispersal", "earth_sim_command", "high", 0.8, ecological_impact=0.2),
    "/api/serving/profiles": AvaniActionPolicy("/api/serving/profiles", "model_promotion", "medium", 0.8),
    "/api/serving/bundles": AvaniActionPolicy("/api/serving/bundles", "model_promotion", "medium", 0.8),
    "/api/serving/bundles/{bundle_id}/promote": AvaniActionPolicy("/api/serving/bundles/{bundle_id}/promote", "model_promotion", "critical", 0.4),
    "/api/serving/calibrate": AvaniActionPolicy("/api/serving/calibrate", "model_promotion", "high", 0.7),
    "/api/gpu-node/deploy/container": AvaniActionPolicy("/api/gpu-node/deploy/container", "system_config", "high", 0.5),
    "/api/gpu-node/deploy/service": AvaniActionPolicy("/api/gpu-node/deploy/service", "system_config", "high", 0.5),
    "/api/gpu-node/deploy/personaplex-split": AvaniActionPolicy("/api/gpu-node/deploy/personaplex-split", "system_config", "high", 0.5),
    "/api/gpu-node/containers/{name}": AvaniActionPolicy("/api/gpu-node/containers/{name}", "system_config", "high", 0.5),
    "/api/omnichannel/send": AvaniActionPolicy("/api/omnichannel/send", "omnichannel_send", "medium", 0.7),
    "/api/omnichannel/forward": AvaniActionPolicy("/api/omnichannel/forward", "omnichannel_send", "medium", 0.7),
    "/api/redteam/authorize": AvaniActionPolicy("/api/redteam/authorize", "red_team", "medium", 0.8),
    "/api/redteam/simulate": AvaniActionPolicy("/api/redteam/simulate", "red_team", "high", 0.5),
    "/api/redteam/credential-test": AvaniActionPolicy("/api/redteam/credential-test", "red_team", "low", 0.9),
    "/api/redteam/phishing-sim": AvaniActionPolicy("/api/redteam/phishing-sim", "red_team", "low", 0.9),
    "/api/redteam/pivot-test": AvaniActionPolicy("/api/redteam/pivot-test", "red_team", "medium", 0.7),
    "/api/redteam/exfil-test": AvaniActionPolicy("/api/redteam/exfil-test", "red_team", "medium", 0.7),
    "/api/redteam/simulation/{sim_id}/cancel": AvaniActionPolicy("/api/redteam/simulation/{sim_id}/cancel", "red_team", "medium", 0.8),
    "/api/n8n/sandbox/execute": AvaniActionPolicy("/api/n8n/sandbox/execute", "tool_execution", "high", 0.5),
    "/api/n8n/safety/request-confirmation": AvaniActionPolicy("/api/n8n/safety/request-confirmation", "tool_execution", "medium", 0.7),
    "/api/n8n/safety/submit-confirmation": AvaniActionPolicy("/api/n8n/safety/submit-confirmation", "tool_execution", "high", 0.4),
    "/api/sporebase/devices/{device_id}/command": AvaniActionPolicy("/api/sporebase/devices/{device_id}/command", "device_control", "high", 0.4, ecological_impact=0.3),
    "/api/sporebase/calibration/{calibration_id}": AvaniActionPolicy("/api/sporebase/calibration/{calibration_id}", "device_control", "high", 0.5, ecological_impact=0.2),
    "/api/sporebase/order": AvaniActionPolicy("/api/sporebase/order", "workflow", "medium", 0.6),
    "/api/nlm/training/start": AvaniActionPolicy("/api/nlm/training/start", "nlm_training", "high", 0.4),
    "/api/nlm/training/stop": AvaniActionPolicy("/api/nlm/training/stop", "nlm_training", "medium", 0.7),
    "/api/nlm/training/pause": AvaniActionPolicy("/api/nlm/training/pause", "nlm_training", "medium", 0.8),
    "/api/nlm/training/resume": AvaniActionPolicy("/api/nlm/training/resume", "nlm_training", "medium", 0.7),
    "/api/nlm/training/checkpoint": AvaniActionPolicy("/api/nlm/training/checkpoint", "nlm_training", "medium", 0.8),
    "/api/nlm/training/load": AvaniActionPolicy("/api/nlm/training/load", "nlm_training", "high", 0.5),
    "/api/nlm/training/mutate": AvaniActionPolicy("/api/nlm/training/mutate", "nlm_training", "critical", 0.2),
    "/api/nlm/training/export": AvaniActionPolicy("/api/nlm/training/export", "nlm_training", "high", 0.5),
    "/api/serving/bundles/{bundle_id}/eval": AvaniActionPolicy("/api/serving/bundles/{bundle_id}/eval", "model_promotion", "high", 0.7),
}


class AvaniActionDenied(RuntimeError):
    """Raised when AVANI denies an action that must fail closed."""

    def __init__(self, decision: Dict[str, Any]) -> None:
        self.decision = decision
        super().__init__(decision.get("reason") or "AVANI denied action preflight")


def infer_risk_tier(
    action_type: str,
    *,
    risk_tier: Optional[str] = None,
    ecological_impact: float = 0.0,
    reversibility: float = 1.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Infer a conservative AVANI risk tier from action shape."""
    if risk_tier:
        return risk_tier.lower()

    action = (action_type or "").strip().lower()
    meta = metadata or {}
    if bool(meta.get("irreversible")) or ecological_impact >= 0.8 or reversibility <= 0.2:
        return "critical"
    if action in HIGH_IMPACT_ACTIONS or ecological_impact >= 0.5 or reversibility <= 0.5:
        return "high"
    if action in MEDIUM_IMPACT_ACTIONS or ecological_impact >= 0.2 or reversibility <= 0.8:
        return "medium"
    return "low"


def get_action_policy(route: str) -> Optional[AvaniActionPolicy]:
    """Return a static route policy by canonical FastAPI route path."""
    return ACTION_ROUTE_POLICIES.get(route)


async def evaluate_action_preflight(
    governor: AvaniGovernor,
    request: AvaniActionPreflight,
) -> Dict[str, Any]:
    """Evaluate an action and return the standard AVANI decision envelope."""
    risk_tier = infer_risk_tier(
        request.action_type,
        risk_tier=request.risk_tier,
        ecological_impact=request.ecological_impact,
        reversibility=request.reversibility,
        metadata=request.metadata,
    )
    proposal = Proposal(
        source_agent=request.source_agent,
        action_type=request.action_type,
        description=request.description,
        risk_tier=RiskTier.from_string(risk_tier),
        ecological_impact=request.ecological_impact,
        reversibility=request.reversibility,
        metadata={
            **request.metadata,
            "route": request.route,
            "operator_id": request.operator_id,
        },
    )
    decision = await governor.evaluate_proposal(proposal)
    payload = decision.to_dict()
    recent = governor.recent_decisions[-1] if governor.recent_decisions else {}
    storage_mode = None
    if governor.audit_ledger is not None:
        try:
            stats = await governor.audit_ledger.stats()
            storage_mode = stats.get("storage")
        except Exception:
            storage_mode = None
    payload.update(
        {
            "verdict": "allow" if decision.approved else "deny",
            "risk_tier": risk_tier,
            "human_review": not decision.approved and risk_tier in {"high", "critical"},
            "degraded": False,
            "confidence": 0.9 if decision.approved else 0.95,
            "season": governor.season_engine.current_season.value,
            "route": request.route,
            "audit_trail_id": recent.get("audit_trail_id"),
            "entry_hash": recent.get("entry_hash"),
            "storage_mode": storage_mode,
        }
    )
    return payload


async def require_action_preflight(
    governor: AvaniGovernor,
    request: AvaniActionPreflight,
) -> Dict[str, Any]:
    """Evaluate and raise AvaniActionDenied when an action cannot proceed."""
    decision = await evaluate_action_preflight(governor, request)
    if not decision.get("approved"):
        raise AvaniActionDenied(decision)
    return decision


async def require_avani_for_route(
    *,
    route: str,
    source_agent: str,
    description: str,
    action_type: Optional[str] = None,
    risk_tier: Optional[str] = None,
    ecological_impact: Optional[float] = None,
    reversibility: Optional[float] = None,
    operator_id: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """FastAPI-friendly fail-closed preflight using the shared AVANI runtime."""
    from mycosoft_mas.core.routers import avani_router

    policy = get_action_policy(route)
    await avani_router.ensure_runtime_restored()
    return await require_action_preflight(
        avani_router.get_governor(),
        AvaniActionPreflight(
            source_agent=source_agent,
            route=route,
            action_type=action_type or (policy.action_type if policy else "tool_execution"),
            description=description,
            risk_tier=risk_tier or (policy.risk_tier if policy else "high"),
            ecological_impact=(
                ecological_impact if ecological_impact is not None else (policy.ecological_impact if policy else 0.0)
            ),
            reversibility=reversibility if reversibility is not None else (policy.reversibility if policy else 0.6),
            operator_id=operator_id,
            metadata=metadata or {},
        ),
    )
