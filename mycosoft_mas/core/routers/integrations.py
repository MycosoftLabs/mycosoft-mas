"""
Integration Router

Provides API endpoints for checking health and status of external integrations:
- MINDEX (Mycological Database)
- NATUREOS (IoT Platform)
- WEBSITE (Mycosoft Website)
- NOTION (Knowledge Base)
- N8N (Workflow Automation)
- MYCOBRAIN (Device Management)
"""

import os
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


async def _check_url_health(name: str, url: str, timeout: float = 5.0) -> Dict[str, Any]:
    """Check health of an HTTP endpoint."""
    if not url:
        return {
            "name": name,
            "status": "not_configured",
            "message": f"URL not configured",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            return {
                "name": name,
                "status": "healthy" if response.status_code < 400 else "unhealthy",
                "http_status": response.status_code,
                "url": url,
                "timestamp": datetime.utcnow().isoformat()
            }
    except httpx.TimeoutException:
        # httpx raises TimeoutException, not asyncio.TimeoutError
        return {
            "name": name,
            "status": "unhealthy",
            "error": "Timeout",
            "url": url,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "name": name,
            "status": "unhealthy",
            "error": str(e),
            "url": url,
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/health")
async def integrations_health():
    """Get health status of all integrations."""
    integrations = {
        "MINDEX": os.getenv("MINDEX_API_URL"),
        "NATUREOS": os.getenv("NATUREOS_API_URL"),
        "WEBSITE": os.getenv("WEBSITE_API_URL"),
        "N8N": os.getenv("N8N_WEBHOOK_URL"),
    }
    
    # Check all integrations concurrently
    tasks = []
    for name, url in integrations.items():
        health_url = f"{url}/health" if url else None
        tasks.append(_check_url_health(name, health_url))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    health_status = {}
    for i, (name, _) in enumerate(integrations.items()):
        if isinstance(results[i], Exception):
            health_status[name] = {
                "status": "error",
                "error": str(results[i])
            }
        else:
            health_status[name] = results[i]
    
    # Add Notion check (uses API key, not URL)
    notion_key = os.getenv("NOTION_API_KEY")
    health_status["NOTION"] = {
        "name": "NOTION",
        "status": "configured" if notion_key else "not_configured",
        "has_api_key": bool(notion_key),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add MYCOBRAIN check
    mycobrain_url = os.getenv("MYCOBRAIN_API_URL")
    health_status["MYCOBRAIN"] = await _check_url_health("MYCOBRAIN", 
        f"{mycobrain_url}/health" if mycobrain_url else None)
    
    return {
        "overall_status": "healthy" if all(
            h.get("status") in ["healthy", "configured"] 
            for h in health_status.values()
        ) else "partial",
        "integrations": health_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/mindex/health")
async def mindex_health():
    """Check MINDEX integration health."""
    url = os.getenv("MINDEX_API_URL")
    db_url = os.getenv("MINDEX_DATABASE_URL")
    
    health = await _check_url_health("MINDEX", f"{url}/health" if url else None)
    health["database_configured"] = bool(db_url)
    return health


@router.get("/natureos/health")
async def natureos_health():
    """Check NATUREOS integration health."""
    url = os.getenv("NATUREOS_API_URL")
    return await _check_url_health("NATUREOS", f"{url}/health" if url else None)


@router.get("/website/health")
async def website_health():
    """Check Website integration health."""
    url = os.getenv("WEBSITE_API_URL")
    return await _check_url_health("WEBSITE", f"{url}/health" if url else None)


@router.get("/notion/health")
async def notion_health():
    """Check Notion integration health."""
    api_key = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not api_key:
        return {
            "name": "NOTION",
            "status": "not_configured",
            "message": "NOTION_API_KEY not set",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Test Notion API
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": "2022-06-28"
            }
            response = await client.get(
                "https://api.notion.com/v1/users/me",
                headers=headers
            )
            if response.status_code == 200:
                return {
                    "name": "NOTION",
                    "status": "healthy",
                    "database_configured": bool(database_id),
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "name": "NOTION",
                    "status": "unhealthy",
                    "error": f"API returned {response.status_code}",
                    "timestamp": datetime.utcnow().isoformat()
                }
    except Exception as e:
        return {
            "name": "NOTION",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/n8n/health")
async def n8n_health():
    """Check n8n integration health."""
    url = os.getenv("N8N_WEBHOOK_URL", os.getenv("N8N_API_URL"))
    if url:
        # n8n health endpoint
        base_url = url.rstrip("/").rsplit("/webhook", 1)[0]
        health_url = f"{base_url}/healthz"
    else:
        health_url = None
    return await _check_url_health("N8N", health_url)


@router.get("/mycobrain/health")
async def mycobrain_health():
    """Check MYCOBRAIN integration health."""
    url = os.getenv("MYCOBRAIN_API_URL")
    return await _check_url_health("MYCOBRAIN", f"{url}/health" if url else None)


@router.get("/status")
async def integrations_status():
    """Get detailed status of all integration configurations."""
    return {
        "integrations": {
            "MINDEX": {
                "configured": bool(os.getenv("MINDEX_API_URL") or os.getenv("MINDEX_DATABASE_URL")),
                "api_url": bool(os.getenv("MINDEX_API_URL")),
                "database_url": bool(os.getenv("MINDEX_DATABASE_URL")),
                "api_key": bool(os.getenv("MINDEX_API_KEY")),
            },
            "NATUREOS": {
                "configured": bool(os.getenv("NATUREOS_API_URL")),
                "api_url": bool(os.getenv("NATUREOS_API_URL")),
                "api_key": bool(os.getenv("NATUREOS_API_KEY")),
                "tenant_id": bool(os.getenv("NATUREOS_TENANT_ID")),
            },
            "WEBSITE": {
                "configured": bool(os.getenv("WEBSITE_API_URL")),
                "api_url": bool(os.getenv("WEBSITE_API_URL")),
                "api_key": bool(os.getenv("WEBSITE_API_KEY")),
            },
            "NOTION": {
                "configured": bool(os.getenv("NOTION_API_KEY")),
                "api_key": bool(os.getenv("NOTION_API_KEY")),
                "database_id": bool(os.getenv("NOTION_DATABASE_ID")),
            },
            "N8N": {
                "configured": bool(os.getenv("N8N_WEBHOOK_URL") or os.getenv("N8N_API_URL")),
                "webhook_url": bool(os.getenv("N8N_WEBHOOK_URL")),
                "api_url": bool(os.getenv("N8N_API_URL")),
                "api_key": bool(os.getenv("N8N_API_KEY")),
            },
            "MYCOBRAIN": {
                "configured": bool(os.getenv("MYCOBRAIN_API_URL")),
                "api_url": bool(os.getenv("MYCOBRAIN_API_URL")),
            },
            "AZURE": {
                "configured": bool(os.getenv("AZURE_SUBSCRIPTION_ID")),
                "subscription_id": bool(os.getenv("AZURE_SUBSCRIPTION_ID")),
                "client_id": bool(os.getenv("AZURE_CLIENT_ID")),
            },
        },
        "timestamp": datetime.utcnow().isoformat()
    }
