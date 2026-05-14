"""
Avani API Router — Constitutional Governance Endpoints

Provides REST API access to the Avani-Micah governance system.

Author: Morgan Rockwell / Mycosoft Labs
Created: March 9, 2026
"""

from __future__ import annotations

import logging
import asyncio
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.avani.constitution.articles import CONSTITUTION, Tier, get_articles_by_tier
from mycosoft_mas.avani.constitution.red_lines import RED_LINES
from mycosoft_mas.avani.constitution.rights import (
    RIGHTS_CHARTER,
    RightsDomain,
    get_rights_by_domain,
)
from mycosoft_mas.avani.enforcement import AvaniActionPreflight, evaluate_action_preflight
from mycosoft_mas.avani.audit.ledger import AvaniAuditLedger, get_audit_ledger
from mycosoft_mas.avani.audit.season_state import AvaniSeasonStateStore
from mycosoft_mas.avani.governor.governor import AvaniGovernor, Proposal, RiskTier
from mycosoft_mas.avani.season_engine.seasons import Season, SeasonEngine, SeasonMetrics
from mycosoft_mas.avani.vision.vision import VISION_PRINCIPLES
from mycosoft_mas.avani.worldview import (
    build_worldstate_snapshot,
    review_device_action,
    review_worldview_payload,
)
from mycosoft_mas.avani.worldview_materializer import materialize_worldview_snapshot
from mycosoft_mas.core.routers.api_keys import require_api_key_scoped, require_api_key_scoped_any
from mycosoft_mas.governance.avani_message_evaluate import evaluate_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/avani", tags=["avani"])

# Shared instances (initialized on startup)
_season_engine: Optional[SeasonEngine] = None
_governor: Optional[AvaniGovernor] = None
_audit_ledger: Optional[AvaniAuditLedger] = None
_season_store: Optional[AvaniSeasonStateStore] = None
_runtime_restored = False
_worldview_materializer_task: Optional[asyncio.Task] = None


def get_ledger() -> AvaniAuditLedger:
    global _audit_ledger
    if _audit_ledger is None:
        _audit_ledger = get_audit_ledger()
    return _audit_ledger


def get_season_store() -> AvaniSeasonStateStore:
    global _season_store
    if _season_store is None:
        _season_store = AvaniSeasonStateStore()
    return _season_store


def get_season_engine() -> SeasonEngine:
    global _season_engine
    if _season_engine is None:
        _season_engine = SeasonEngine(initial_season=Season.SPRING)
    return _season_engine


def get_governor() -> AvaniGovernor:
    global _governor
    if _governor is None:
        _governor = AvaniGovernor(season_engine=get_season_engine(), audit_ledger=get_ledger())
    return _governor


async def ensure_runtime_restored() -> None:
    """Restore persisted season state once per process before serving AVANI state."""
    global _runtime_restored
    if _runtime_restored:
        return
    engine = get_season_engine()
    restored = await get_season_store().load()
    if restored is not None:
        engine.state = restored
        logger.info("Restored AVANI season state: %s", restored.current.value)
    _runtime_restored = True


# --- Request/Response Models ---


class ProposalRequest(BaseModel):
    source_agent: str = Field(..., description="ID of the proposing agent")
    action_type: str = Field(..., description="Type of action proposed")
    description: str = Field(..., description="Description of the proposal")
    risk_tier: str = Field(default="low", description="Risk tier: none/low/medium/high/critical")
    ecological_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    reversibility: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluateMessageRequest(BaseModel):
    """MYCA ingress contract: message-based evaluation consumed by website/voice/chat."""

    message: str = Field(..., description="User message or action description")
    user_id: str = Field(default="anonymous", description="User or session ID")
    user_role: str = Field(default="user", description="Role for authorization")
    is_superuser: bool = Field(default=False, description="Whether user has superuser")
    action_type: str = Field(
        default="chat",
        description="One of: chat, agent_dispatch, workflow, device_control, data_access, system_config",
    )
    response_text: Optional[str] = Field(
        default=None, description="Proposed or actual response for leakage check"
    )
    context: Dict[str, Any] = Field(default_factory=dict, description="Optional context")


class SeasonUpdateRequest(BaseModel):
    eco_stability: float = Field(default=1.0, ge=0.0, le=1.0)
    founder_latency_hours: float = Field(default=0.0, ge=0.0)
    toxicity_detected: bool = False
    critical_error: bool = False
    red_line_violated: bool = False
    all_systems_green: bool = True


class GroundingCheckRequest(BaseModel):
    claim: str = Field(..., description="Claim, answer, forecast, or action to ground")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Evidence and provenance")
    source_domains: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    degraded: bool = False


class WorldviewReviewRequest(BaseModel):
    worldview_request_id: str = Field(..., description="Worldview API request id")
    data: Any = Field(default=None, description="Filtered payload about to leave Worldview")
    source_domains: list[str] = Field(default_factory=list)
    caller: Dict[str, Any] = Field(default_factory=dict)
    region: Optional[Dict[str, Any]] = None
    time_window: Optional[Dict[str, Any]] = None
    worldstate_snapshot_id: Optional[str] = None
    worldstate_degraded: bool = False


class ActionPreflightRequest(BaseModel):
    source_agent: str = Field(..., description="Agent, route, or service requesting execution")
    action_type: str = Field(..., description="Action family being proposed")
    description: str = Field(..., description="Plain-language action description")
    route: str = Field(default="", description="Canonical route or execution surface")
    risk_tier: Optional[str] = Field(default=None, description="none/low/medium/high/critical")
    ecological_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    reversibility: float = Field(default=1.0, ge=0.0, le=1.0)
    operator_id: str = Field(default="", description="Human/service operator identity")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DevicePreflightRequest(BaseModel):
    device_id: str = Field(..., description="Device or sensor id")
    action: str = Field(..., description="Hardware action being requested")
    operator_id: str = Field(default="", description="Operator or service identity")
    telemetry: Dict[str, Any] = Field(default_factory=dict)
    ecological_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    reversibility: float = Field(default=1.0, ge=0.0, le=1.0)
    rollback_plan: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorldviewMaterializeRequest(BaseModel):
    region: Optional[Dict[str, Any]] = None


# --- Endpoints ---


async def _worldview_materializer_loop() -> None:
    interval = max(5, int(os.getenv("AVANI_WORLDVIEW_MATERIALIZER_INTERVAL_SECONDS", "60")))
    while True:
        try:
            await materialize_worldview_snapshot(source="avani_materializer_background")
        except Exception as exc:
            logger.warning("AVANI Worldview materializer refresh failed: %s", exc)
        await asyncio.sleep(interval)


@router.on_event("startup")
async def start_worldview_materializer() -> None:
    global _worldview_materializer_task
    enabled = os.getenv("AVANI_WORLDVIEW_MATERIALIZER_ENABLED", "false").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return
    if _worldview_materializer_task is None or _worldview_materializer_task.done():
        _worldview_materializer_task = asyncio.create_task(_worldview_materializer_loop())


@router.on_event("shutdown")
async def stop_worldview_materializer() -> None:
    global _worldview_materializer_task
    if _worldview_materializer_task is not None:
        _worldview_materializer_task.cancel()
        _worldview_materializer_task = None


@router.get("/health")
async def avani_health():
    """Avani system health check."""
    await ensure_runtime_restored()
    engine = get_season_engine()
    get_governor()
    stats = await get_ledger().stats()
    verification = await get_ledger().verify(limit=500)
    return {
        "status": "healthy",
        "system": "avani-governor",
        "router_mounted": True,
        "season": engine.current_season.value,
        "is_operational": engine.is_operational,
        "audit": {
            "storage_mode": stats.get("storage"),
            "chain_valid": verification.valid,
            "checked": verification.checked,
            "degraded": stats.get("storage") != "postgres",
        },
        "stats": {
            **stats,
            "current_season": engine.current_season.value,
            "is_operational": engine.is_operational,
        },
    }


@router.get("/season")
async def get_season():
    """Get current seasonal state."""
    await ensure_runtime_restored()
    return get_season_engine().to_dict()


@router.post("/season/update")
async def update_season(
    request: SeasonUpdateRequest,
    auth: dict = require_api_key_scoped("avani:update"),
):
    """Update season metrics and evaluate transitions. Root authority derived from avani:root scope."""
    await ensure_runtime_restored()
    engine = get_season_engine()
    old_season = engine.current_season.value
    scopes = auth.get("scopes") or []
    is_root = "avani:root" in scopes
    metrics = SeasonMetrics(
        eco_stability=request.eco_stability,
        founder_latency_hours=request.founder_latency_hours,
        toxicity_detected=request.toxicity_detected,
        critical_error=request.critical_error,
        red_line_violated=request.red_line_violated,
        all_systems_green=request.all_systems_green,
    )
    result = engine.update(metrics, is_root=is_root)
    storage = await get_season_store().save(engine.state)
    if result is not None:
        await get_ledger().append(
            event_kind="season_transition",
            source=auth.get("user_id", "api-key"),
            action_type="season_update",
            decision={
                "approved": True,
                "from": old_season,
                "to": engine.current_season.value,
                "reason": engine.state.trigger_reason,
            },
            season=engine.current_season.value,
            metadata={"metrics": request.model_dump(), "storage": storage},
        )
    return {
        "transitioned": result is not None,
        "season": engine.to_dict(),
        "storage": storage,
    }


@router.post("/evaluate")
async def evaluate_proposal(
    request: ProposalRequest,
    auth: dict = require_api_key_scoped("avani:evaluate"),
):
    """Submit a proposal for constitutional evaluation."""
    await ensure_runtime_restored()
    gov = get_governor()
    try:
        proposal = Proposal(
            source_agent=request.source_agent,
            action_type=request.action_type,
            description=request.description,
            risk_tier=RiskTier.from_string(request.risk_tier),
            ecological_impact=request.ecological_impact,
            reversibility=request.reversibility,
            metadata={**request.metadata, "requested_by": auth.get("user_id")},
        )
        decision = await gov.evaluate_proposal(proposal)
        return decision.to_dict()
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/preflight")
async def action_preflight(
    request: ActionPreflightRequest,
    auth: dict = require_api_key_scoped("avani:evaluate"),
):
    """Shared action-capable preflight for MYCA, agents, devices, and workflows."""
    await ensure_runtime_restored()
    try:
        decision = await evaluate_action_preflight(
            get_governor(),
            AvaniActionPreflight(
                source_agent=request.source_agent,
                action_type=request.action_type,
                description=request.description,
                route=request.route,
                risk_tier=request.risk_tier or "low",
                ecological_impact=request.ecological_impact,
                reversibility=request.reversibility,
                operator_id=request.operator_id or auth.get("user_id", ""),
                metadata={**request.metadata, "requested_by": auth.get("user_id")},
            ),
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    stats = await get_ledger().stats()
    return {
        **decision,
        "season": get_season_engine().current_season.value,
        "storage_mode": stats.get("storage"),
    }


@router.post("/device/preflight")
async def device_preflight(
    request: DevicePreflightRequest,
    auth: dict = require_api_key_scoped("avani:evaluate"),
):
    """Review a hardware/device command before execution."""
    await ensure_runtime_restored()
    review = review_device_action(
        device_id=request.device_id,
        action=request.action,
        operator_id=request.operator_id or auth.get("user_id", ""),
        telemetry=request.telemetry,
        ecological_impact=request.ecological_impact,
        reversibility=request.reversibility,
        rollback_plan=request.rollback_plan,
    )
    proposal_decision = await evaluate_action_preflight(
        get_governor(),
        AvaniActionPreflight(
            source_agent="device_preflight",
            action_type="device_control",
            description=f"Device command {request.action} for {request.device_id}",
            risk_tier=review.risk_tier,
            ecological_impact=review.ecological_risk,
            reversibility=review.reversibility,
            metadata={
                **request.metadata,
                "device_review": review.to_dict(),
                "rollback_plan_present": bool(request.rollback_plan),
                "requested_by": auth.get("user_id"),
            },
        ),
    )
    approved = bool(review.approved and proposal_decision.get("approved"))
    verdict = review.verdict if not approved else proposal_decision.get("verdict", "allow")
    decision = {
        **review.to_dict(),
        "approved": approved,
        "verdict": verdict,
        "proposal_reason": proposal_decision.get("reason"),
        "season": get_season_engine().current_season.value,
    }
    audit_entry = await get_ledger().append(
        event_kind="device_preflight",
        source=auth.get("user_id", "api-key"),
        action_type="device_control",
        decision=decision,
        season=get_season_engine().current_season.value,
        metadata={"request": request.model_dump()},
    )
    return {
        **decision,
        "audit_trail_id": audit_entry.event_id,
        "storage_mode": audit_entry.storage,
    }


@router.post("/evaluate-message")
async def evaluate_message_request(
    request: EvaluateMessageRequest,
    auth: dict = require_api_key_scoped("avani:evaluate"),
):
    """
    Authoritative message-based AVANI evaluation for MYCA ingress.
    Same contract as website evaluateGovernance(); used by chat, voice orchestrator, search chat.
    All MYCA ingress routes must call this (or proxy to it) so no path bypasses governance.
    """
    await ensure_runtime_restored()
    evaluation = evaluate_message(
        message=request.message,
        user_id=request.user_id,
        user_role=request.user_role,
        is_superuser=request.is_superuser,
        action_type=request.action_type,
        response_text=request.response_text,
        context=request.context,
    )
    await get_ledger().append(
        event_kind="message_evaluation",
        source=request.user_id,
        action_type=request.action_type,
        decision=evaluation.to_dict(),
        season=get_season_engine().current_season.value,
        metadata={
            "user_role": request.user_role,
            "is_superuser": request.is_superuser,
            "requested_by": auth.get("user_id"),
        },
    )
    return evaluation.to_dict()


@router.get("/constitution")
async def get_constitution(tier: Optional[str] = None):
    """Read constitutional articles, optionally filtered by tier."""
    if tier:
        try:
            t = Tier(tier.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tier: {tier}. Valid: {[t.value for t in Tier]}",
            )
        articles = get_articles_by_tier(t)
    else:
        articles = CONSTITUTION

    return {
        "articles": {
            k: {"title": v.title, "text": v.text, "tier": v.tier.value} for k, v in articles.items()
        }
    }


@router.get("/rights")
async def get_rights(domain: Optional[str] = None):
    """Read the rights charter, optionally filtered by domain."""
    if domain:
        try:
            d = RightsDomain(domain.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid domain: {domain}. Valid: {[d.value for d in RightsDomain]}",
            )
        rights = get_rights_by_domain(d)
    else:
        rights = RIGHTS_CHARTER

    return {
        "rights": [{"id": r.id, "domain": r.domain.value, "statement": r.statement} for r in rights]
    }


@router.get("/red-lines")
async def get_red_lines():
    """Read all red lines (absolute prohibitions)."""
    return {
        "red_lines": [
            {
                "id": rl.id,
                "prohibition": rl.prohibition,
                "consequence": rl.consequence,
            }
            for rl in RED_LINES
        ]
    }


@router.get("/vision")
async def get_vision_principles():
    """Read Vision principles (the anti-Ultron wisdom layer)."""
    return {
        "principles": [
            {
                "id": p.id,
                "statement": p.statement,
                "weight": p.weight,
                "question": p.question,
            }
            for p in VISION_PRINCIPLES
        ],
        "doctrine": (
            "Intelligence must preserve the conditions that allow life, "
            "diversity, and creativity to exist — even when those conditions "
            "appear inefficient or chaotic."
        ),
    }


@router.get("/decisions/recent")
async def get_recent_decisions(auth: dict = require_api_key_scoped("avani:audit:read")):
    """Get recent governance decisions."""
    await ensure_runtime_restored()
    decisions = await get_ledger().query(limit=50)
    return {"decisions": decisions}


@router.get("/stats")
async def get_governance_stats(auth: dict = require_api_key_scoped("avani:audit:read")):
    """Get governance statistics."""
    await ensure_runtime_restored()
    stats = await get_ledger().stats()
    return {
        **stats,
        "current_season": get_season_engine().current_season.value,
        "is_operational": get_season_engine().is_operational,
    }


@router.get("/operator/status")
async def avani_operator_status(auth: dict = require_api_key_scoped("avani:audit:read")):
    """Operator-facing AVANI runtime status and recent governance events."""
    await ensure_runtime_restored()
    ledger = get_ledger()
    stats = await ledger.stats()
    verification = await ledger.verify(limit=500)
    recent = await ledger.query(limit=100)
    denials = [
        entry
        for entry in recent
        if not ((entry.get("decision") or {}).get("approved", True))
        or (entry.get("decision") or {}).get("verdict") in {"deny", "require_approval"}
    ]
    event_counts: Dict[str, int] = {}
    for entry in recent:
        kind = str(entry.get("event_kind") or "unknown")
        event_counts[kind] = event_counts.get(kind, 0) + 1
    return {
        "season": get_season_engine().to_dict(),
        "operational_state": {
            "is_operational": get_season_engine().is_operational,
            "router_mounted": True,
            "fail_closed_actions": True,
            "read_only_degraded_allowed": True,
        },
        "audit": {
            "storage_mode": stats.get("storage"),
            "chain_valid": verification.valid,
            "checked": verification.checked,
            "degraded": stats.get("storage") != "postgres",
        },
        "recent": {
            "event_counts": event_counts,
            "denials": denials[:20],
            "worldview_reviews": [
                entry for entry in recent if entry.get("event_kind") == "worldview_review"
            ][:20],
            "device_preflights": [
                entry for entry in recent if entry.get("event_kind") == "device_preflight"
            ][:20],
        },
        "stats": stats,
    }


# ============================================================================
# AVANI MARINE ECOLOGICAL SAFETY — TAC-O
# ============================================================================


@router.post("/ecological-review")
async def ecological_review(
    classification: dict,
    auth: dict = require_api_key_scoped("avani:evaluate"),
):
    """AVANI reviews classification for marine wildlife false positives.
    
    Gates threat classifications through the MarineEcologicalGuard
    before any alert reaches the operator.
    """
    marine_mammal_score = classification.get("marine_mammal_score", 0.0)
    if marine_mammal_score > 0.5:
        result = {
            "action": "gate_for_human_review",
            "reason": f"Marine mammal score={marine_mammal_score:.2f} exceeds threshold",
            "ecological_impact": "HIGH",
            "override_threat": True,
            "original_classification": classification,
        }
    else:
        result = {
            "action": "pass",
            "ecological_impact": "NONE",
            "override_threat": False,
            "marine_mammal_score": marine_mammal_score,
        }
    await ensure_runtime_restored()
    audit_entry = await get_ledger().append(
        event_kind="ecological_review",
        source=auth.get("user_id", "api-key"),
        action_type="ecological_review",
        decision=result,
        season=get_season_engine().current_season.value,
        metadata={"classification": classification},
    )
    result["audit_trail_id"] = audit_entry.event_id
    return result


@router.get("/ecological-audit-log")
async def ecological_audit_log(
    since: str = None,
    limit: int = 50,
    auth: dict = require_api_key_scoped("avani:audit:read"),
):
    """Retrieve AVANI ecological governance audit trail for TAC-O."""
    await ensure_runtime_restored()
    bounded_limit = max(1, min(limit, 500))
    entries = await get_ledger().query(
        event_kind="ecological_review",
        since=since,
        limit=bounded_limit,
    )
    return {
        "audit_entries": entries,
        "total": len(entries),
        "since": since,
        "limit": bounded_limit,
    }


@router.get("/audit/verify")
async def verify_audit_log(auth: dict = require_api_key_scoped("avani:audit:read")):
    """Verify AVANI audit hash-chain integrity."""
    verification = await get_ledger().verify()
    return verification.to_dict()


# ============================================================================
# AVANI WORLDSTATE / WORLDVIEW GOVERNANCE
# ============================================================================


@router.get("/worldstate")
async def avani_worldstate(auth: dict = require_api_key_scoped("avani:audit:read")):
    """Return AVANI's compact governance snapshot of MAS WorldState."""
    await ensure_runtime_restored()
    from mycosoft_mas.core.routers.worldstate_api import get_world

    world_payload = await get_world()
    snapshot = build_worldstate_snapshot(world_payload)
    audit_entry = await get_ledger().append(
        event_kind="worldstate_snapshot",
        source=auth.get("user_id", "api-key"),
        action_type="worldstate_read",
        decision={
            "approved": True,
            "verdict": "allow",
            "worldstate_snapshot_id": snapshot.worldstate_snapshot_id,
            "degraded": snapshot.degraded,
            "confidence": snapshot.confidence,
        },
        season=get_season_engine().current_season.value,
        metadata={"snapshot": snapshot.to_dict()},
    )
    return {
        **snapshot.to_dict(),
        "audit_trail_id": audit_entry.event_id,
        "storage_mode": audit_entry.storage,
    }


@router.get("/context")
async def avani_context(auth: dict = require_api_key_scoped("avani:audit:read")):
    """Return AVANI's current governed context for MYCA and internal agents."""
    await ensure_runtime_restored()
    snapshot = await avani_worldstate(auth=auth)
    return {
        "season": get_season_engine().to_dict(),
        "worldstate": snapshot,
        "governance": {
            "audit_storage": snapshot.get("storage_mode"),
            "fail_closed_actions": True,
            "read_only_degraded_allowed": True,
        },
    }


@router.post("/grounding-check")
async def avani_grounding_check(
    request: GroundingCheckRequest,
    auth: dict = require_api_key_scoped("avani:evaluate"),
):
    """Evaluate whether a claim/action is grounded enough for use."""
    await ensure_runtime_restored()
    reasons = []
    verdict = "allow"
    approved = True
    if request.degraded:
        verdict = "allow_with_audit"
        reasons.append("Evidence is degraded; release/action requires audit metadata.")
    if request.confidence < 0.4:
        verdict = "require_approval"
        approved = False
        reasons.append("Grounding confidence below AVANI minimum threshold.")
    if not request.evidence:
        verdict = "require_approval"
        approved = False
        reasons.append("No evidence payload supplied for grounding.")
    if not reasons:
        reasons.append("Claim is grounded by supplied evidence.")

    decision = {
        "approved": approved,
        "verdict": verdict,
        "confidence": request.confidence,
        "degraded": request.degraded,
        "reason": "; ".join(reasons),
        "source_domains": request.source_domains,
    }
    audit_entry = await get_ledger().append(
        event_kind="grounding_check",
        source=auth.get("user_id", "api-key"),
        action_type="grounding_check",
        decision=decision,
        season=get_season_engine().current_season.value,
        metadata={"claim": request.claim, "evidence": request.evidence},
    )
    return {
        **decision,
        "audit_trail_id": audit_entry.event_id,
        "storage_mode": audit_entry.storage,
    }


@router.post("/worldview/review")
async def avani_worldview_review(
    request: WorldviewReviewRequest,
    auth: dict = require_api_key_scoped("avani:evaluate"),
):
    """Review a filtered MINDEX Worldview response before customer release."""
    await ensure_runtime_restored()
    frame = review_worldview_payload(
        worldview_request_id=request.worldview_request_id,
        data=request.data,
        source_domains=request.source_domains,
        caller=request.caller,
        region=request.region,
        time_window=request.time_window,
        worldstate_snapshot_id=request.worldstate_snapshot_id,
        worldstate_degraded=request.worldstate_degraded,
    )
    approved = frame.avani_verdict != "deny"
    audit_entry = await get_ledger().append(
        event_kind="worldview_review",
        source=auth.get("user_id", "worldview-api"),
        action_type="worldview_release",
        decision={
            "approved": approved,
            "verdict": frame.avani_verdict,
            "confidence": frame.confidence,
            "degraded": frame.degraded,
            "reason": "; ".join(frame.governance_notes),
        },
        season=get_season_engine().current_season.value,
        metadata={"worldview_frame": frame.to_dict()},
    )
    return {
        **frame.to_dict(),
        "audit_trail_id": audit_entry.event_id,
        "storage_mode": audit_entry.storage,
    }


@router.post("/worldview/materialize")
async def avani_worldview_materialize(
    request: WorldviewMaterializeRequest,
    auth: dict = require_api_key_scoped_any(["avani:update", "avani:root"]),
):
    """Materialize MAS WorldState into MINDEX Worldview snapshot storage."""
    await ensure_runtime_restored()
    return await materialize_worldview_snapshot(
        region=request.region,
        source=auth.get("user_id", "api-key"),
    )
