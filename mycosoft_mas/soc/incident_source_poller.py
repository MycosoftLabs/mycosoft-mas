"""
Background poller: network diagnostics + UniFi guest/unknown signals → SOC incidents.

Writes via soc.repository.create_incident (Postgres + Redis stream publish on create).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from dataclasses import asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _pg() -> bool:
    return bool(os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"))


async def _maybe_emit_diagnostics_incident(report: Any) -> None:
    from mycosoft_mas.soc import repository as soc_repo

    dns = report.dns or {}
    dns_summary = dns.get("summary", {}) if isinstance(dns, dict) else {}
    dns_ok = bool(dns_summary.get("healthy", True))

    latency = report.latency or {}
    lat_hosts = latency.get("hosts", {}) if isinstance(latency, dict) else {}
    lat_summary = latency.get("summary", {}) if isinstance(latency, dict) else {}
    lat_total = int(lat_summary.get("total") or len(lat_hosts) or 0)
    lat_ok = int(lat_summary.get("reachable") or 0)

    conn = report.connectivity or {}
    conn_eps = conn.get("endpoints", {}) if isinstance(conn, dict) else {}
    conn_summary = conn.get("summary", {}) if isinstance(conn, dict) else {}
    conn_total = int(conn_summary.get("total") or len(conn_eps) or 0)
    conn_ok = int(conn_summary.get("reachable") or 0)

    issues: List[str] = []
    if not dns_ok:
        issues.append("DNS anomalies or inconsistent resolver consensus")
    if lat_total and lat_ok < lat_total:
        issues.append(f"VM ICMP reachability degraded ({lat_ok}/{lat_total})")
    if conn_total and conn_ok < conn_total:
        issues.append(f"HTTP service reachability degraded ({conn_ok}/{conn_total})")
    if getattr(report, "errors", None):
        for e in report.errors[:5]:
            issues.append(f"diag_error:{e}")

    if not issues:
        return

    recent = await soc_repo.count_recent_incidents_by_source_kind(
        "network_diagnostics",
        "network.health",
        within_minutes=int(os.getenv("SOC_DIAG_INCIDENT_DEDUPE_MIN", "90")),
    )
    if recent > 0:
        return

    title = "Network diagnostics: " + "; ".join(issues[:3])
    details: Dict[str, Any] = {
        "issues": issues,
        "dns_summary": dns_summary,
        "latency_summary": lat_summary,
        "connectivity_summary": conn_summary,
        "errors": list(getattr(report, "errors", []) or [])[:20],
    }
    if hasattr(report, "__dataclass_fields__"):
        details["report_excerpt"] = asdict(report)
    await soc_repo.create_incident(
        title=title[:500],
        description="Automated network diagnostics reported actionable conditions. See details JSON.",
        severity="medium" if lat_ok < lat_total or conn_ok < conn_total else "low",
        status="open",
        source="network_diagnostics",
        kind="network.health",
        details=details,
        tags=["auto", "network_diagnostics"],
        timeline=[
            {
                "timestamp": report.timestamp,
                "action": "detected",
                "actor": "incident_source_poller",
                "details": title,
            }
        ],
    )


async def _maybe_emit_unifi_guest_incident(report: Any) -> None:
    """High guest/unknown client counts from diagnostics topology."""
    from mycosoft_mas.soc import repository as soc_repo

    u = report.unauthorized or {}
    if not isinstance(u, dict):
        return
    unknown = int(u.get("unknown_or_guest_clients") or 0)
    total = int(u.get("total_clients") or 0)
    threshold = int(os.getenv("SOC_UNIFI_UNKNOWN_CLIENT_THRESHOLD", "25"))
    if total == 0 or unknown < threshold:
        return

    recent = await soc_repo.count_recent_incidents_by_source_kind(
        "unifi",
        "unifi.guest_unknown_surge",
        within_minutes=int(os.getenv("SOC_UNIFI_INCIDENT_DEDUPE_MIN", "120")),
    )
    if recent > 0:
        return

    await soc_repo.create_incident(
        title=f"UniFi: elevated unknown/guest clients ({unknown}/{total})",
        description="UniFi topology shows elevated unknown or guest wireless clients.",
        severity="low",
        status="open",
        source="unifi",
        kind="unifi.guest_unknown_surge",
        details={"unauthorized": u},
        tags=["auto", "unifi"],
        timeline=[
            {
                "timestamp": report.timestamp,
                "action": "detected",
                "actor": "incident_source_poller",
                "details": "Guest/unknown client ratio crossed threshold",
            }
        ],
    )


async def _maybe_emit_threat_intel_snapshot() -> None:
    """Optional: poll WEBSITE threat_intel_service when THREAT_INTEL_SERVICE_URL is set."""
    base = (os.getenv("THREAT_INTEL_SERVICE_URL") or "").strip().rstrip("/")
    if not base:
        return
    from mycosoft_mas.soc import repository as soc_repo

    try:
        import httpx
    except ImportError:
        logger.debug("httpx not available; skip threat intel poll")
        return

    blocked_count = 0
    tor_count = 0
    try:
        async with httpx.AsyncClient(timeout=12.0, verify=True) as client:
            br = await client.get(f"{base}/api/v1/blocked")
            if br.is_success:
                data = br.json()
                blocked_count = int(data.get("count") or len(data.get("blocked") or []) or 0)
            tr = await client.get(f"{base}/api/v1/tor-exits")
            if tr.is_success:
                tj = tr.json()
                tor_count = int(tj.get("count") or 0)
    except Exception as e:
        logger.debug("threat intel poll failed: %s", e)
        return

    thr_blocked = int(os.getenv("SOC_THREAT_INTEL_BLOCKED_THRESHOLD", "80"))
    if blocked_count < thr_blocked:
        return
    dedupe_min = int(os.getenv("SOC_THREAT_INTEL_INCIDENT_DEDUPE_MIN", "360"))
    recent = await soc_repo.count_recent_incidents_by_source_kind(
        "threat_intel", "threat_intel.blocked_inventory", dedupe_min
    )
    if recent > 0:
        return

    await soc_repo.create_incident(
        title=f"Threat intel: blocked IP inventory elevated ({blocked_count})",
        description="Threat intelligence service reports elevated count of blocked IPs. Review /api/v1/blocked and firewall rules.",
        severity="medium" if blocked_count >= thr_blocked * 2 else "low",
        status="open",
        source="threat_intel",
        kind="threat_intel.blocked_inventory",
        details={"blocked_count": blocked_count, "tor_exit_count": tor_count, "service_url": base},
        tags=["auto", "threat_intel"],
        timeline=[
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "detected",
                "actor": "incident_source_poller",
                "details": "Blocked IP count crossed threshold",
            }
        ],
    )


async def run_incident_source_poll_once() -> Dict[str, Any]:
    if not _pg():
        return {"skipped": True, "reason": "no_database"}
    from mycosoft_mas.services.network_diagnostics import run_full_diagnostics

    report = await run_full_diagnostics()
    await _maybe_emit_diagnostics_incident(report)
    await _maybe_emit_unifi_guest_incident(report)
    await _maybe_emit_threat_intel_snapshot()
    return {"ok": True, "timestamp": report.timestamp}


async def _poller_loop() -> None:
    interval = int(os.getenv("SOC_INCIDENT_POLLER_INTERVAL_SEC", "600"))
    logger.info("Incident source poller starting (interval=%ss)", interval)
    while True:
        try:
            summary = await run_incident_source_poll_once()
            logger.info("incident_source_poller: %s", json.dumps(summary, default=str))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("incident_source_poller cycle failed: %s", e)
        await asyncio.sleep(max(120, interval))


_task: Optional[asyncio.Task[None]] = None


def start_incident_source_poller_background() -> None:
    global _task
    if os.getenv("SOC_INCIDENT_POLLER", "1") == "0":
        logger.info("SOC_INCIDENT_POLLER=0; skipping incident source poller")
        return
    if not _pg():
        return
    if _task and not _task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _task = loop.create_task(_poller_loop(), name="incident-source-poller")
