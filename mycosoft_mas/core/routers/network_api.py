"""
Network Diagnostics API

Endpoints for topology, DNS, latency, speed, unauthorized access, and vulnerability checks.
Integrates with UniFi, Cloudflare, and system tools.

Author: MYCA
Created: February 12, 2026
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from mycosoft_mas.services.network_diagnostics import (
    run_connectivity_checks,
    run_dns_checks,
    run_full_diagnostics,
    run_latency_checks,
)

router = APIRouter(prefix="/api/network", tags=["network"])


class DnsCheckRequest(BaseModel):
    """Request body for custom DNS check."""

    domains: List[str] = ["mycosoft.com", "sandbox.mycosoft.com"]
    include_system: bool = True


@router.get("/health")
async def network_health() -> Dict[str, Any]:
    """Health check for network API."""
    return {"status": "ok", "service": "network-diagnostics"}


@router.get("/dns")
async def get_dns_check(
    domains: Optional[str] = Query(None, description="Comma-separated domains"),
    include_system: bool = Query(True, description="Include system resolver"),
) -> Dict[str, Any]:
    """
    Run DNS checks across Cloudflare, Google, Quad9, and system resolvers.
    Detects anomalies (hijacking, poisoning) when resolvers return different IPs.
    """
    domain_list = (
        [d.strip() for d in domains.split(",") if d.strip()]
        if domains and domains.strip()
        else None
    )
    result = await run_dns_checks(domains=domain_list, include_system=include_system)
    return result


@router.post("/dns")
async def post_dns_check(body: DnsCheckRequest) -> Dict[str, Any]:
    """Run DNS checks with custom domains."""
    result = await run_dns_checks(
        domains=body.domains,
        include_system=body.include_system,
    )
    return result


@router.get("/latency")
async def get_latency() -> Dict[str, Any]:
    """Run latency (ping) checks to Mycosoft VMs."""
    return await run_latency_checks()


@router.get("/connectivity")
async def get_connectivity() -> Dict[str, Any]:
    """Check HTTP connectivity to MAS, MINDEX, Sandbox."""
    return await run_connectivity_checks()


@router.get("/diagnostics")
async def get_full_diagnostics(
    website_url: Optional[str] = Query(None),
    unifi_host: Optional[str] = Query(None),
    unifi_api_key: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Run full network diagnostics:
    - DNS: multi-resolver consistency (anomaly detection)
    - Latency: ping to VMs
    - Connectivity: HTTP to services
    - Topology: UniFi devices and clients (if configured)
    - Unauthorized: unknown/guest clients
    - Vulnerabilities: basic indicators
    """
    report = await run_full_diagnostics(
        website_url=website_url or os.environ.get("WEBSITE_API_URL"),
        unifi_host=unifi_host or os.environ.get("UNIFI_HOST"),
        unifi_api_key=unifi_api_key or os.environ.get("UNIFI_API_KEY"),
        cloudflare_token=os.environ.get("CLOUDFLARE_API_TOKEN"),
        cloudflare_zone_id=os.environ.get("CLOUDFLARE_ZONE_ID"),
    )
    out: Dict[str, Any] = {
        "timestamp": report.timestamp,
        "errors": report.errors,
    }
    if report.dns:
        out["dns"] = report.dns
    if report.latency:
        out["latency"] = report.latency
    if report.connectivity:
        out["connectivity"] = report.connectivity
    if report.topology:
        out["topology"] = report.topology
    if report.unauthorized:
        out["unauthorized"] = report.unauthorized
    if report.vulnerabilities:
        out["vulnerabilities"] = report.vulnerabilities

    # Summary flags for quick triage
    dns_ok = report.dns and report.dns.get("summary", {}).get("healthy", True)
    out["summary"] = {
        "dns_healthy": dns_ok,
        "has_errors": len(report.errors) > 0,
        "topology_available": report.topology is not None,
    }
    return out
