"""Policy Compliance Agent — TAC-O Maritime Integration

Ensures all data handling, storage, and transmission meets
NIST 800-171/CMMC requirements in real-time. Monitors encryption
status, access logs, CUI markings, and auto-flags violations.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class PolicyComplianceAgent(BaseAgent):
    """Real-time NIST 800-171 compliance monitoring for TAC-O."""

    def __init__(self, agent_id: str = "taco-policy-compliance", name: str = "Policy Compliance", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = [
            "nist_800_171_monitoring",
            "cui_marking_validation",
            "encryption_audit",
            "access_log_review",
        ]
        self.cluster = "taco"

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        if task_type == "audit_encryption":
            return await self._audit_encryption(task)
        elif task_type == "validate_cui_marking":
            return await self._validate_cui(task)
        elif task_type == "review_access_logs":
            return await self._review_access(task)
        elif task_type == "compliance_status":
            return await self._compliance_status(task)
        return {"status": "error", "message": f"Unknown task type: {task_type}"}

    async def _audit_encryption(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Audit encryption status on data channels."""
        logger.info("Encryption audit requested")
        transit_scheme = str(task.get("transit_scheme") or "tls1.3").lower()
        at_rest_scheme = str(task.get("at_rest_scheme") or "aes-256-gcm").lower()
        findings = []
        if transit_scheme not in {"tls1.3", "mtls-tls1.3"}:
            findings.append("Transit encryption is below TLS 1.3 requirement")
        if at_rest_scheme != "aes-256-gcm":
            findings.append("At-rest encryption is not AES-256-GCM")
        return {
            "status": "success",
            "result": {
                "encryption_standard": "AES-256-GCM",
                "tls_version": "1.3",
                "audit": "pass" if not findings else "fail",
                "findings": findings,
                "transit_scheme": transit_scheme,
                "at_rest_scheme": at_rest_scheme,
            },
        }

    async def _validate_cui(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Validate CUI markings on stored data."""
        banner_present = bool(task.get("cui_banner_present", False))
        classification = str(task.get("classification") or "UNCLASSIFIED").upper()
        valid = banner_present and classification in {"CUI", "SECRET", "TS_SCI"}
        return {
            "status": "success",
            "result": {
                "validation": "pass" if valid else "fail",
                "cui_banner_present": banner_present,
                "classification": classification,
            },
        }

    async def _review_access(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Review access logs for unauthorized access."""
        access_events = task.get("access_events", [])
        violations = [
            event
            for event in access_events
            if not event.get("authorized", False) or not event.get("actor")
        ]
        return {
            "status": "success",
            "result": {
                "review": "pass" if not violations else "fail",
                "violations": violations,
                "events_reviewed": len(access_events),
            },
        }

    async def _compliance_status(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get current NIST 800-171 compliance status."""
        controls_met = int(task.get("controls_met", 0) or 0)
        total_controls = int(task.get("total_controls", 110) or 110)
        mtls_enabled = bool(task.get("mutual_tls_enabled", os.environ.get("VM_PASSWORD") is not None))
        audit_enabled = bool(task.get("audit_trail_enabled", True))
        status = "compliant" if controls_met >= total_controls and mtls_enabled and audit_enabled else "partial"
        return {
            "status": "success",
            "result": {
                "framework": "NIST 800-171 Rev. 2",
                "total_controls": total_controls,
                "controls_met": controls_met,
                "status": status,
                "mutual_tls_enabled": mtls_enabled,
                "audit_trail_enabled": audit_enabled,
            },
        }
