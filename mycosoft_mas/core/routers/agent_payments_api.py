"""
Agent Payments API — x402 Payment Protocol Endpoints
=====================================================

Exposes REST endpoints for the Agent Payments system:
- Tiger tier listing and info
- x402 charge processing
- CrewAI research (gated by x402)
- Revenue analytics
- Ampersend A2A agent management
- Ampersend CLI skill operations (setup, fetch, config)

Author: MYCA / Morgan Rockwell
Created: April 1, 2026
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from mycosoft_mas.agents.financial.agent_payments import (
    AMPERSEND_DASHBOARD,
    DEFAULT_TIER,
    PAY_TO_ADDRESS,
    PAYMENT_NETWORK,
    TIGER_TIERS,
    AgentPaymentsAgent,
    TigerTier,
    TigerTierConfig,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent-payments", tags=["agent-payments"])

# ---------------------------------------------------------------------------
# Singleton agent instance (lazy-init)
# ---------------------------------------------------------------------------

_payments_agent: Optional[AgentPaymentsAgent] = None


def _get_agent() -> AgentPaymentsAgent:
    global _payments_agent
    if _payments_agent is None:
        _payments_agent = AgentPaymentsAgent(
            agent_id="agent-payments-x402",
            name="AgentPaymentsAgent",
            config={
                "pay_to_address": PAY_TO_ADDRESS,
                "network": PAYMENT_NETWORK,
                "default_tier": DEFAULT_TIER.value,
            },
        )
    return _payments_agent


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ChargeRequest(BaseModel):
    client_id: str
    service_type: str = "query"
    tier: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TierAssignRequest(BaseModel):
    client_id: str
    tier: str


class CrewResearchRequest(BaseModel):
    topic: str
    tier: str = TigerTier.SUMATRAN.value
    client_id: str = "anonymous"


class AmpersendSetupStartRequest(BaseModel):
    name: str
    daily_limit: Optional[str] = None
    monthly_limit: Optional[str] = None
    per_transaction_limit: Optional[str] = None
    auto_topup: bool = False
    force: bool = False


class AmpersendFetchRequest(BaseModel):
    url: str
    method: str = "GET"
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    inspect: bool = False


class AmpersendConfigSetRequest(BaseModel):
    key_account: Optional[str] = None
    api_url: Optional[str] = None
    network: Optional[str] = None
    clear_api_url: bool = False
    clear_network: bool = False


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health")
async def health():
    agent = _get_agent()
    return await agent.health_check()


# ---------------------------------------------------------------------------
# Tiger Tier endpoints
# ---------------------------------------------------------------------------


@router.get("/tiers")
async def list_tiers():
    """List all 9 tiger variety pricing tiers."""
    agent = _get_agent()
    return await agent.process_task({"type": "get_tiers"})


@router.get("/tiers/{tier_name}")
async def get_tier(tier_name: str):
    """Get details for a specific tiger tier."""
    agent = _get_agent()
    result = await agent.process_task({"type": "get_tier_info", "tier": tier_name})
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# Charging / Payments
# ---------------------------------------------------------------------------


@router.post("/charge")
async def charge(req: ChargeRequest):
    """Charge a client for a service at their assigned tiger tier."""
    agent = _get_agent()
    result = await agent.process_task({
        "type": "charge",
        "client_id": req.client_id,
        "service_type": req.service_type,
        "tier": req.tier,
        "metadata": req.metadata,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/assign-tier")
async def assign_tier(req: TierAssignRequest):
    """Assign a tiger tier to a client."""
    agent = _get_agent()
    result = await agent.process_task({
        "type": "assign_tier",
        "client_id": req.client_id,
        "tier": req.tier,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# CrewAI Research (x402-gated)
# ---------------------------------------------------------------------------


@router.post("/research")
async def crew_research(req: CrewResearchRequest):
    """
    Execute a CrewAI research task (requires Sumatran tier or above).

    This endpoint is gated by x402 payment when accessed through the
    x402 middleware. Direct API calls charge via the agent internally.
    """
    agent = _get_agent()
    result = await agent.process_task({
        "type": "crew_research",
        "topic": req.topic,
        "tier": req.tier,
        "client_id": req.client_id,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# Revenue / Analytics
# ---------------------------------------------------------------------------


@router.get("/revenue")
async def get_revenue():
    """Get revenue analytics across all tiger tiers."""
    agent = _get_agent()
    return await agent.process_task({"type": "get_revenue"})


@router.get("/transactions")
async def get_transactions(client_id: Optional[str] = None, limit: int = 50):
    """Get recent payment transactions."""
    agent = _get_agent()
    return await agent.process_task({
        "type": "get_transactions",
        "client_id": client_id,
        "limit": limit,
    })


# ---------------------------------------------------------------------------
# Ampersend A2A Management
# ---------------------------------------------------------------------------


@router.get("/ampersend/dashboard")
async def ampersend_dashboard():
    """Get Ampersend dashboard link and agent info."""
    return {
        "status": "success",
        "dashboard_url": AMPERSEND_DASHBOARD,
        "pay_to_address": PAY_TO_ADDRESS,
        "network": PAYMENT_NETWORK,
    }


@router.post("/ampersend/create-a2a")
async def create_a2a_agent(tier: str = DEFAULT_TIER.value):
    """Get instructions to create an Ampersend A2A agent for a tier."""
    agent = _get_agent()
    return await agent.process_task({"type": "create_a2a_agent", "tier": tier})


# ---------------------------------------------------------------------------
# Ampersend CLI Skill endpoints
# ---------------------------------------------------------------------------


def _run_ampersend_cmd(args: List[str], timeout: int = 30) -> Dict[str, Any]:
    """Execute an ampersend CLI command and parse JSON output."""
    cmd = ["ampersend"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip() or result.stderr.strip()
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {
                "ok": result.returncode == 0,
                "raw_output": output,
                "return_code": result.returncode,
            }
    except FileNotFoundError:
        return {
            "ok": False,
            "error": {
                "code": "CLI_NOT_FOUND",
                "message": (
                    "ampersend CLI not installed. "
                    "Install via: npm install -g @ampersend_ai/ampersend-sdk@0.0.14"
                ),
            },
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": {"code": "TIMEOUT", "message": f"Command timed out after {timeout}s"},
        }


@router.post("/ampersend/setup/start")
async def ampersend_setup_start(req: AmpersendSetupStartRequest):
    """
    Start Ampersend agent setup — generates a key and requests approval.

    Returns a user_approve_url that the user must visit to approve.
    """
    args = ["setup", "start", "--name", req.name]
    if req.force:
        args.append("--force")
    if req.daily_limit:
        args.extend(["--daily-limit", req.daily_limit])
    if req.monthly_limit:
        args.extend(["--monthly-limit", req.monthly_limit])
    if req.per_transaction_limit:
        args.extend(["--per-transaction-limit", req.per_transaction_limit])
    if req.auto_topup:
        args.append("--auto-topup")

    result = _run_ampersend_cmd(args)
    if not result.get("ok", False):
        raise HTTPException(status_code=400, detail=result.get("error", result))
    return result


@router.post("/ampersend/setup/finish")
async def ampersend_setup_finish(
    poll_interval: int = 5,
    timeout: int = 600,
    force: bool = False,
):
    """Poll for approval and activate the agent config."""
    args = ["setup", "finish"]
    if force:
        args.append("--force")
    args.extend(["--poll-interval", str(poll_interval)])
    args.extend(["--timeout", str(timeout)])

    result = _run_ampersend_cmd(args, timeout=timeout + 30)
    if not result.get("ok", False):
        raise HTTPException(status_code=400, detail=result.get("error", result))
    return result


@router.post("/ampersend/fetch")
async def ampersend_fetch(req: AmpersendFetchRequest):
    """
    Make an HTTP request with automatic x402 payment handling via Ampersend CLI.

    Use inspect=true to check payment requirements without paying.
    """
    args = ["fetch"]
    if req.method != "GET":
        args.extend(["-X", req.method])
    for key, value in req.headers.items():
        args.extend(["-H", f"{key}: {value}"])
    if req.body:
        args.extend(["-d", req.body])
    if req.inspect:
        args.append("--inspect")
    args.append(req.url)

    result = _run_ampersend_cmd(args, timeout=60)
    if not result.get("ok", False):
        raise HTTPException(status_code=400, detail=result.get("error", result))
    return result


@router.get("/ampersend/config/status")
async def ampersend_config_status():
    """Show current Ampersend CLI configuration status."""
    return _run_ampersend_cmd(["config", "status"])


@router.post("/ampersend/config/set")
async def ampersend_config_set(req: AmpersendConfigSetRequest):
    """Update Ampersend CLI configuration."""
    args = ["config", "set"]
    if req.key_account:
        args.append(req.key_account)
    if req.api_url:
        args.extend(["--api-url", req.api_url])
    if req.clear_api_url:
        args.append("--clear-api-url")
    if req.network:
        args.extend(["--network", req.network])
    if req.clear_network:
        args.append("--clear-network")

    if len(args) == 2:
        raise HTTPException(
            status_code=400,
            detail="At least one config option must be provided",
        )

    result = _run_ampersend_cmd(args)
    if not result.get("ok", False):
        raise HTTPException(status_code=400, detail=result.get("error", result))
    return result


# ---------------------------------------------------------------------------
# x402 middleware factory endpoint (for dynamic route protection)
# ---------------------------------------------------------------------------


@router.get("/x402/info")
async def x402_info():
    """Information about x402 payment protocol configuration."""
    return {
        "status": "success",
        "protocol": "x402",
        "pay_to_address": PAY_TO_ADDRESS,
        "network": PAYMENT_NETWORK,
        "dashboard": AMPERSEND_DASHBOARD,
        "integrations": {
            "ampersend_a2a": {
                "description": "Google ADK agents with x402 before_agent_callback",
                "sdk": "ampersend-sdk==0.0.13",
            },
            "x402_fastapi": {
                "description": "FastAPI route-level payment middleware",
                "sdk": "x402",
            },
            "crewai": {
                "description": "CrewAI research crews gated by x402",
                "sdk": "crewai",
            },
            "ampersend_cli": {
                "description": "CLI for autonomous agent payments (setup, fetch, config)",
                "sdk": "@ampersend_ai/ampersend-sdk@0.0.14 (npm)",
            },
        },
        "tiers": {
            tier.value: {
                "display_name": cfg.display_name,
                "subspecies": cfg.subspecies,
                "price": cfg.price_per_request,
                "conservation_status": cfg.conservation_status,
            }
            for tier, cfg in TIGER_TIERS.items()
        },
    }
