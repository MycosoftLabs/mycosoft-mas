"""RaaS Agent Card — A2A discovery endpoint.

Serves the standard agent card at /.well-known/agent-card.json
so external agents can discover MYCA's RaaS capabilities.

Created: March 11, 2026
"""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter

from mycosoft_mas.raas.credits import CREDIT_COSTS, CREDIT_PACKAGES

router = APIRouter(tags=["RaaS - Discovery"])

_BASE_URL = os.getenv("MYCA_RAAS_BASE_URL", "https://api.mycosoft.com")


@router.get("/.well-known/agent-card.json")
async def agent_card() -> Dict[str, Any]:
    """Standard A2A agent card for MYCA's Robot-as-a-Service platform."""
    return {
        "name": "MYCA RaaS",
        "version": "1.0.0",
        "provider": {
            "organization": "Mycosoft",
            "url": "https://mycosoft.com",
        },
        "description": (
            "Mycosoft Robot-as-a-Service platform. "
            "Access Nature Learning Model inference, live CREP sensor data "
            "(aviation, maritime, satellite, weather), NVIDIA Earth-2 climate "
            "simulations, MycoBrain IoT device telemetry, MINDEX species/taxonomy "
            "databases, 158+ specialized AI agents, semantic memory search, "
            "and biological/physics simulations."
        ),
        "url": _BASE_URL,
        "capabilities": [
            "nlm_inference",
            "crep_live_data",
            "earth2_climate",
            "device_telemetry",
            "mindex_data",
            "knowledge_graph",
            "agent_coordination",
            "memory_search",
            "simulations",
        ],
        "authentication": {
            "type": "api_key",
            "header": "X-API-Key",
            "description": "Register at /api/raas/agents/register to get an API key",
        },
        "endpoints": {
            "registration": f"{_BASE_URL}/api/raas/agents/register",
            "catalog": f"{_BASE_URL}/api/raas/services",
            "packages": f"{_BASE_URL}/api/raas/payments/packages",
            "invoke_nlm": f"{_BASE_URL}/api/raas/invoke/nlm",
            "invoke_crep": f"{_BASE_URL}/api/raas/invoke/crep",
            "invoke_earth2": f"{_BASE_URL}/api/raas/invoke/earth2",
            "invoke_data": f"{_BASE_URL}/api/raas/invoke/data",
            "invoke_agent": f"{_BASE_URL}/api/raas/invoke/agent",
            "invoke_memory": f"{_BASE_URL}/api/raas/invoke/memory",
            "invoke_simulation": f"{_BASE_URL}/api/raas/invoke/simulation",
            "invoke_devices": f"{_BASE_URL}/api/raas/invoke/devices",
            "account": f"{_BASE_URL}/api/raas/agents/me",
            "usage": f"{_BASE_URL}/api/raas/agents/me/usage",
        },
        "pricing": {
            "signup_fee": "$1.00 USD",
            "signup_bonus": "100 credits",
            "credit_costs": CREDIT_COSTS,
            "packages": {
                pid: {
                    "credits": p.credits + p.bonus_credits,
                    "price_usd": p.price_usd,
                }
                for pid, p in CREDIT_PACKAGES.items()
                if pid != "signup"
            },
        },
        "payment_methods": {
            "fiat": ["Credit Card", "Debit Card (via Stripe)"],
            "crypto": ["USDC", "SOL", "ETH", "BTC", "USDT", "AVE"],
        },
        "protocols": ["rest", "websocket", "a2a", "mcp"],
        "documentation": f"{_BASE_URL}/api/raas/docs",
    }


@router.get("/api/raas/health")
async def raas_health() -> Dict[str, Any]:
    """RaaS platform health check."""
    return {
        "status": "healthy",
        "service": "raas",
        "version": "1.0.0",
        "services_available": len(CREDIT_COSTS),
        "packages_available": len(CREDIT_PACKAGES),
    }
