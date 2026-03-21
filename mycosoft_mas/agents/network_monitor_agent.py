"""
Network Monitor Agent

Runs topology, DNS, latency, connectivity, and vulnerability checks.
Integrates with UniFi, Cloudflare, and system tools.
Detects DNS anomalies, unauthorized clients, and connectivity issues.

Author: MYCA
Created: February 12, 2026
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.services.network_diagnostics import (
    run_connectivity_checks,
    run_dns_checks,
    run_full_diagnostics,
    run_latency_checks,
)

logger = logging.getLogger(__name__)


class NetworkMonitorAgent(BaseAgent):
    """
    Network diagnostics agent for topology, DNS, latency, and security.

    Capabilities:
    - network_dns_check: Multi-resolver DNS consistency (anomaly detection)
    - network_latency_check: Ping latency to VMs
    - network_connectivity_check: HTTP connectivity to services
    - network_full_diagnostics: Full report (DNS, latency, topology, unauthorized)
    - network_topology: UniFi devices and clients (when configured)
    """

    def __init__(
        self,
        agent_id: str = "network-monitor-agent",
        name: str = "NetworkMonitorAgent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            agent_id=agent_id,
            name=name,
            config=config or {},
        )
        self.capabilities = [
            "network_dns_check",
            "network_latency_check",
            "network_connectivity_check",
            "network_full_diagnostics",
            "network_topology",
        ]
        self._monitoring_interval = config.get("monitoring_interval", 300)  # 5 min
        self.metrics = {
            "dns_checks_run": 0,
            "anomalies_detected": 0,
            "last_full_scan": None,
        }

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process network diagnostic tasks."""
        task_type = task.get("type", "")
        handlers = {
            "dns_check": self._handle_dns_check,
            "latency_check": self._handle_latency_check,
            "connectivity_check": self._handle_connectivity_check,
            "full_diagnostics": self._handle_full_diagnostics,
            "topology": self._handle_topology,
        }
        handler = handlers.get(task_type)
        if handler:
            return await handler(task)
        return {"status": "error", "message": f"Unknown task type: {task_type}"}

    async def _handle_dns_check(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run DNS checks with anomaly detection."""
        domains = task.get("domains")
        try:
            result = await run_dns_checks(domains=domains)
            self.metrics["dns_checks_run"] += 1
            anomalies = result.get("anomalies_detected", [])
            if anomalies:
                self.metrics["anomalies_detected"] += len(anomalies)
            return {
                "status": "success",
                "result": result,
                "anomalies_detected": len(anomalies),
            }
        except Exception as e:
            logger.exception("DNS check failed")
            return {"status": "error", "message": str(e)}

    async def _handle_latency_check(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run latency checks to VMs."""
        try:
            result = await run_latency_checks()
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_connectivity_check(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run connectivity checks to services."""
        try:
            result = await run_connectivity_checks()
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_full_diagnostics(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run full network diagnostics."""
        try:
            report = await run_full_diagnostics()
            self.metrics["last_full_scan"] = datetime.utcnow().isoformat()
            out = {
                "timestamp": report.timestamp,
                "dns": report.dns,
                "latency": report.latency,
                "connectivity": report.connectivity,
                "topology": report.topology,
                "unauthorized": report.unauthorized,
                "vulnerabilities": report.vulnerabilities,
                "errors": report.errors,
            }
            if report.dns and report.dns.get("anomalies_detected"):
                self.metrics["anomalies_detected"] += len(report.dns["anomalies_detected"])
            return {"status": "success", "result": out}
        except Exception as e:
            logger.exception("Full diagnostics failed")
            return {"status": "error", "message": str(e)}

    async def _handle_topology(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get network topology from UniFi."""
        try:
            report = await run_full_diagnostics()
            return {
                "status": "success",
                "result": {
                    "topology": report.topology,
                    "unauthorized": report.unauthorized,
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def run_cycle(self) -> Dict[str, Any]:
        """Periodic cycle: run full diagnostics and optionally alert on anomalies."""
        try:
            report = await run_full_diagnostics()
            anomalies = []
            if report.dns and report.dns.get("anomalies_detected"):
                anomalies.extend(report.dns["anomalies_detected"])
            if report.unauthorized and report.unauthorized.get("unknown_or_guest_clients", 0) > 5:
                anomalies.append(
                    f"High number of unknown/guest clients: {report.unauthorized['unknown_or_guest_clients']}"
                )

            return {
                "tasks_processed": 1,
                "insights_generated": len(anomalies),
                "summary": (
                    f"Network diagnostics complete; {len(anomalies)} anomalies"
                    if anomalies
                    else "Network diagnostics complete; no anomalies"
                ),
                "anomalies": anomalies,
            }
        except Exception as e:
            logger.exception("Network monitor cycle failed")
            return {"tasks_processed": 0, "summary": f"Cycle failed: {e}"}
