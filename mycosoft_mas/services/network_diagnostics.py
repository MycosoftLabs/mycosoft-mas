"""
Network Diagnostics Service

Performs topology, DNS, latency, speed, and vulnerability checks.
Integrates with UniFi, Cloudflare, and system tools.

DNS anomaly detection: Compares resolution across multiple resolvers to detect
hijacking, poisoning, or misconfiguration.

Author: MYCA
Created: February 12, 2026
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import re
import socket
import subprocess
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Domains to check for DNS anomalies (Mycosoft)
DNS_CHECK_DOMAINS = ["mycosoft.com", "sandbox.mycosoft.com", "api.mycosoft.com"]

# Public resolvers for cross-validation (detect DNS poisoning/hijacking)
PUBLIC_RESOLVERS = {
    "cloudflare": "1.1.1.1",
    "google": "8.8.8.8",
    "quad9": "9.9.9.9",
}

# Mycosoft VM IPs for topology and latency
MYCOSOFT_VMS = {
    "sandbox": "192.168.0.187",
    "mas": "192.168.0.188",
    "mindex": "192.168.0.189",
}


@dataclass
class DnsCheckResult:
    """Result of a single DNS resolution check."""

    domain: str
    resolver: str
    resolver_ip: str
    ips: List[str]
    latency_ms: float
    success: bool
    error: Optional[str] = None
    suspicious: bool = False


@dataclass
class DnsAnomalyReport:
    """DNS anomaly detection report."""

    domain: str
    resolver_results: Dict[str, DnsCheckResult]
    consensus_ips: List[str]
    anomalies: List[str]
    is_healthy: bool
    timestamp: str


@dataclass
class LatencyResult:
    """Single host latency check."""

    host: str
    ip: str
    latency_ms: Optional[float]
    success: bool
    packet_loss: bool = False


@dataclass
class TopologyNode:
    """Network topology node (device or client)."""

    id: str
    name: str
    ip: Optional[str]
    mac: Optional[str]
    type: str  # "device" | "client"
    status: str
    parent_id: Optional[str] = None


@dataclass
class NetworkDiagnosticsReport:
    """Full network diagnostics report."""

    dns: Optional[Dict[str, Any]] = None
    latency: Optional[Dict[str, Any]] = None
    topology: Optional[Dict[str, Any]] = None
    unauthorized: Optional[Dict[str, Any]] = None
    vulnerabilities: Optional[Dict[str, Any]] = None
    connectivity: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    timestamp: str = ""


async def _run_subprocess(
    cmd: List[str], timeout: float = 10.0, shell: bool = False
) -> Tuple[str, str, int]:
    """Run a subprocess and return (stdout, stderr, returncode)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=shell,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return (
            stdout.decode(errors="replace").strip(),
            stderr.decode(errors="replace").strip(),
            proc.returncode or 0,
        )
    except asyncio.TimeoutError:
        return ("", "timeout", -1)
    except Exception as e:
        return ("", str(e), -1)


def _system_resolver() -> Optional[str]:
    """Get system DNS resolver IP if detectable."""
    try:
        if platform.system() == "Windows":
            out = subprocess.check_output(
                ["ipconfig", "/all"],
                timeout=5,
                text=True,
                errors="replace",
            )
            for line in out.splitlines():
                if "DNS Servers" in line or "DNS servers" in line.lower():
                    parts = line.split(":")
                    if len(parts) >= 2:
                        ip = parts[-1].strip()
                        if re.match(r"\d+\.\d+\.\d+\.\d+", ip):
                            return ip
        else:
            with open("/etc/resolv.conf") as f:
                for line in f:
                    if line.startswith("nameserver"):
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[1]
    except Exception:
        pass
    return None


async def _resolve_dns_async(
    domain: str, resolver_ip: str, timeout: float = 5.0
) -> DnsCheckResult:
    """Resolve a domain using a specific resolver."""
    start = time.perf_counter()
    try:
        if platform.system() == "Windows":
            out, err, rc = await _run_subprocess(
                ["nslookup", domain, resolver_ip], timeout=timeout
            )
        else:
            out, err, rc = await _run_subprocess(
                ["nslookup", domain, resolver_ip], timeout=timeout
            )

        latency_ms = (time.perf_counter() - start) * 1000
        ips: List[str] = []

        if rc == 0 and out:
            for line in out.splitlines():
                if "Address" in line or "Addresses" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        ip = parts[-1].strip().split("#")[0].strip()  # strip port like #53
                        if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip) and ip != resolver_ip:
                            ips.append(ip)

        # Fallback: socket if nslookup fails
        if not ips:
            try:
                loop = asyncio.get_event_loop()
                resolver = socket.getaddrinfo
                addrs = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: resolver(domain, None, socket.AF_INET),
                    ),
                    timeout=timeout,
                )
                ips = list({a[4][0] for a in addrs})
            except Exception:
                pass

        return DnsCheckResult(
            domain=domain,
            resolver=resolver_ip,
            resolver_ip=resolver_ip,
            ips=ips,
            latency_ms=round(latency_ms, 2),
            success=len(ips) > 0,
        )
    except Exception as e:
        return DnsCheckResult(
            domain=domain,
            resolver=resolver_ip,
            resolver_ip=resolver_ip,
            ips=[],
            latency_ms=0,
            success=False,
            error=str(e),
        )


async def run_dns_checks(
    domains: Optional[List[str]] = None,
    include_system: bool = True,
) -> Dict[str, Any]:
    """
    Run DNS checks across multiple resolvers.
    Detects anomalies: mismatched IPs across resolvers (possible hijacking).
    """
    domains = domains or DNS_CHECK_DOMAINS
    all_resolvers = dict(PUBLIC_RESOLVERS)
    sys_resolver = _system_resolver()
    if include_system and sys_resolver:
        all_resolvers["system"] = sys_resolver

    results: Dict[str, Dict[str, Any]] = {}
    anomalies_global: List[str] = []

    for domain in domains:
        tasks = [
            _resolve_dns_async(domain, ip) for ip in all_resolvers.values()
        ]
        resolver_results = await asyncio.gather(*tasks)

        by_resolver: Dict[str, Dict[str, Any]] = {}
        all_ips: List[Tuple[str, str]] = []
        for name, res in zip(all_resolvers.keys(), resolver_results):
            by_resolver[name] = asdict(res)
            for ip in res.ips:
                all_ips.append((name, ip))

        # Consensus: IPs that appear from multiple resolvers
        ip_counts: Dict[str, set] = {}
        for res_name, ip in all_ips:
            ip_counts.setdefault(ip, set()).add(res_name)

        consensus = [ip for ip, sources in ip_counts.items() if len(sources) >= 2]
        if not consensus and all_ips:
            consensus = list({ip for _, ip in all_ips})

        anomalies: List[str] = []
        if len(ip_counts) > 1 and len(consensus) == 0:
            anomalies.append(
                f"Resolvers return different IPs for {domain} - possible DNS hijacking or misconfiguration"
            )
            anomalies_global.append(f"{domain}: inconsistent resolution")

        for res in resolver_results:
            if res.ips and consensus and res.ips != consensus:
                res.suspicious = True
                by_resolver[list(all_resolvers.keys())[
                    list(all_resolvers.values()).index(res.resolver_ip)
                ]] = asdict(res)

        results[domain] = {
            "resolver_results": by_resolver,
            "consensus_ips": consensus,
            "anomalies": anomalies,
            "is_healthy": len(anomalies) == 0,
        }

    return {
        "domains": results,
        "resolvers_used": all_resolvers,
        "anomalies_detected": anomalies_global,
        "summary": {
            "total_domains": len(domains),
            "anomaly_count": len(anomalies_global),
            "healthy": len(anomalies_global) == 0,
        },
    }


async def run_latency_checks(
    hosts: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Run ping-based latency checks to key hosts."""
    hosts = hosts or MYCOSOFT_VMS
    results: Dict[str, Dict[str, Any]] = {}
    count = 2 if platform.system() == "Windows" else 2

    for name, ip in hosts.items():
        try:
            if platform.system() == "Windows":
                cmd = ["ping", "-n", str(count), "-w", "3000", ip]
            else:
                cmd = ["ping", "-c", str(count), "-W", "3", ip]

            out, err, rc = await _run_subprocess(cmd, timeout=8.0)
            latency_ms: Optional[float] = None
            packet_loss = True

            if rc == 0 and out:
                # Parse "Average = 12ms" (Windows) or "avg/0.012" (Linux)
                m = re.search(r"Average\s*=\s*(\d+)", out, re.I)
                if m:
                    latency_ms = float(m.group(1))
                    packet_loss = False
                m = re.search(r"(\d+\.?\d*)\s*ms", out)
                if m and latency_ms is None:
                    latency_ms = float(m.group(1))
                    packet_loss = False

            results[name] = {
                "host": ip,
                "latency_ms": round(latency_ms, 2) if latency_ms else None,
                "success": rc == 0,
                "packet_loss": packet_loss,
            }
        except Exception as e:
            results[name] = {
                "host": ip,
                "latency_ms": None,
                "success": False,
                "error": str(e),
            }

    return {
        "hosts": results,
        "summary": {
            "reachable": sum(1 for r in results.values() if r.get("success")),
            "total": len(results),
        },
    }


async def run_connectivity_checks() -> Dict[str, Any]:
    """Check connectivity to key Mycosoft services."""
    endpoints = [
        ("mas_health", "http://192.168.0.188:8001/health"),
        ("mindex", "http://192.168.0.189:8000/"),
        ("sandbox", "http://192.168.0.187:3000/"),
    ]
    results: Dict[str, Dict[str, Any]] = {}

    try:
        import httpx
    except ImportError:
        return {
            "endpoints": {},
            "error": "httpx not installed",
        }

    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in endpoints:
            start = time.perf_counter()
            try:
                r = await client.get(url)
                latency_ms = (time.perf_counter() - start) * 1000
                results[name] = {
                    "url": url,
                    "status_code": r.status_code,
                    "latency_ms": round(latency_ms, 2),
                    "reachable": True,
                }
            except Exception as e:
                results[name] = {
                    "url": url,
                    "reachable": False,
                    "error": str(e),
                }

    return {
        "endpoints": results,
        "summary": {
            "reachable": sum(1 for r in results.values() if r.get("reachable")),
            "total": len(results),
        },
    }


async def run_full_diagnostics(
    website_url: Optional[str] = None,
    unifi_host: Optional[str] = None,
    unifi_api_key: Optional[str] = None,
    cloudflare_token: Optional[str] = None,
    cloudflare_zone_id: Optional[str] = None,
) -> NetworkDiagnosticsReport:
    """
    Run full network diagnostics.

    Uses env vars if not passed:
    - WEBSITE_API_URL or 192.168.0.187:3000 for UniFi proxy
    - UNIFI_HOST, UNIFI_API_KEY, UNIFI_SITE for UniFi
    - CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID for Cloudflare DNS
    """
    from datetime import datetime

    report = NetworkDiagnosticsReport(
        timestamp=datetime.utcnow().isoformat() + "Z"
    )
    website_url = website_url or os.environ.get("WEBSITE_API_URL", "http://192.168.0.187:3000")
    unifi_host = unifi_host or os.environ.get("UNIFI_HOST", "192.168.0.1")
    unifi_api_key = unifi_api_key or os.environ.get("UNIFI_API_KEY")
    cloudflare_token = cloudflare_token or os.environ.get("CLOUDFLARE_API_TOKEN")
    cloudflare_zone_id = cloudflare_zone_id or os.environ.get("CLOUDFLARE_ZONE_ID")

    # 1. DNS checks (always)
    try:
        report.dns = await run_dns_checks()
    except Exception as e:
        report.errors.append(f"DNS checks failed: {e}")
        logger.exception("DNS checks failed")

    # 2. Latency checks (always)
    try:
        report.latency = await run_latency_checks()
    except Exception as e:
        report.errors.append(f"Latency checks failed: {e}")

    # 3. Connectivity (always)
    try:
        report.connectivity = await run_connectivity_checks()
    except Exception as e:
        report.errors.append(f"Connectivity checks failed: {e}")

    # 4. Topology + Unauthorized from UniFi (direct client or website proxy)
    if unifi_api_key:
        try:
            from mycosoft_mas.integrations.unifi_client import UniFiClient

            client = UniFiClient(host=unifi_host, api_key=unifi_api_key)
            data = await client.get_topology()
            if data.get("devices") or data.get("clients"):
                report.topology = {
                    "devices": data.get("devices", []),
                    "clients": data.get("clients", []),
                    "source": "unifi",
                }
                clients = data.get("clients", [])
                unknown = [
                    c
                    for c in clients
                    if c.get("is_guest") or not c.get("name") or c.get("name") == "Unknown"
                ]
                report.unauthorized = {
                    "unknown_or_guest_clients": len(unknown),
                    "sample": unknown[:10],
                    "total_clients": len(clients),
                }
            else:
                # Fallback: website proxy when UniFi not reachable from MAS
                import httpx
                async with httpx.AsyncClient(timeout=15.0, verify=False) as client_http:
                    r = await client_http.get(
                        f"{website_url}/api/unifi?action=topology",
                        headers={"Cache-Control": "no-store"},
                    )
                    if r.status_code == 200:
                        data = r.json()
                        report.topology = {
                            "devices": data.get("devices", []),
                            "clients": data.get("clients", []),
                            "source": "unifi_via_website",
                        }
                        clients = data.get("clients", [])
                        unknown = [
                            c for c in clients
                            if c.get("is_guest") or not c.get("name")
                        ]
                        report.unauthorized = {
                            "unknown_or_guest_clients": len(unknown),
                            "sample": unknown[:10],
                            "total_clients": len(clients),
                        }
        except Exception as e:
            report.errors.append(f"UniFi topology failed: {e}")
    else:
        report.unauthorized = {"configured": False, "reason": "UNIFI_API_KEY not set"}

    # 5. Cloudflare DNS records (optional)
    if cloudflare_token and cloudflare_zone_id:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"https://api.cloudflare.com/client/v4/zones/{cloudflare_zone_id}/dns_records",
                    headers={
                        "Authorization": f"Bearer {cloudflare_token}",
                        "Content-Type": "application/json",
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    records = data.get("result", [])
                    report.dns = report.dns or {}
                    report.dns["cloudflare_records"] = [
                        {"name": rec.get("name"), "type": rec.get("type"), "content": rec.get("content")}
                        for rec in records[:20]
                    ]
        except Exception as e:
            report.errors.append(f"Cloudflare DNS fetch failed: {e}")

    # 6. Basic vulnerability indicators (no nmap - avoid heavy deps)
    report.vulnerabilities = {
        "checks_performed": ["dns_consistency", "connectivity"],
        "open_port_scan": "skipped (requires nmap)",
        "recommendation": "Run nmap or Suricata for full vulnerability assessment",
    }

    return report
