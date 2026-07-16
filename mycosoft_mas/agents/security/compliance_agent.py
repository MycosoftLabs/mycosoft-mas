"""
CMMC/NIST 800-171 Compliance Engine Agent for Mycosoft MAS.

CMMC Level 1-3 self-assessment, NIST 800-171 control mapping,
evidence collection, gap analysis, POA&M generation.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus
from mycosoft_mas.security.compliance_evidence_gate import (
    evaluate_control_response,
    is_control_met,
)

logger = logging.getLogger(__name__)

# CMMC 14 domains (NIST 800-171 families)
CMMC_DOMAINS = [
    "AC",  # Access Control
    "AT",  # Awareness and Training
    "AU",  # Audit and Accountability
    "CA",  # Security Assessment
    "CM",  # Configuration Management
    "IA",  # Identification and Authentication
    "IR",  # Incident Response
    "MA",  # Maintenance
    "MP",  # Media Protection
    "PE",  # Physical Protection
    "PS",  # Personnel Security
    "RA",  # Risk Assessment
    "SC",  # System and Communications Protection
    "SI",  # System and Information Integrity
]

CMMC_L1_PRACTICE_COUNT = 17
CMMC_L2_PRACTICE_COUNT = 110
CMMC_L3_PRACTICE_COUNT = 20


class CmmcComplianceAgent(BaseAgent):
    """Agent for evidence-gated CMMC/NIST 800-171 self-assessment and POA&M work."""

    def __init__(
        self,
        agent_id: str,
        name: str = "CMMC Compliance Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities.update(
            {
                "cmmc",
                "nist_800_171",
                "self_assessment",
                "gap_analysis",
                "poam",
                "evidence_collection",
                "control_mapping",
            }
        )
        self._exostar = None
        self._assessments: Dict[str, Dict[str, Any]] = {}

    def _get_exostar(self):
        if self._exostar is None:
            try:
                from mycosoft_mas.integrations.exostar_client import ExostarClient

                self._exostar = ExostarClient(self.config)
            except ImportError:
                pass
        return self._exostar

    async def _initialize_services(self) -> None:
        self.status = AgentStatus.ACTIVE

    async def _check_services_health(self) -> Dict[str, Any]:
        exostar = self._get_exostar()
        return {
            "exostar": await exostar.health_check() if exostar else {"status": "unavailable"},
        }

    async def _check_resource_usage(self) -> Dict[str, Any]:
        return {"cpu": 0, "memory": 0}

    async def _handle_error_type(self, error_type: str, error: str) -> Dict[str, Any]:
        return {"status": "error", "type": error_type, "message": error}

    async def _handle_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "received", "notification": notification}

    def _get_control_framework(self, level: int) -> Dict[str, Any]:
        """Return CMMC control framework for level 1, 2, or 3."""
        if level == 1:
            total = CMMC_L1_PRACTICE_COUNT
        elif level == 2:
            total = CMMC_L2_PRACTICE_COUNT
        elif level == 3:
            total = CMMC_L3_PRACTICE_COUNT
        else:
            total = 0
        return {
            "level": level,
            "domains": CMMC_DOMAINS,
            "practice_count": total,
            "framework": "CMMC v2.0" if level <= 2 else "CMMC v2.0 L3",
            "nist_mapping": (
                "NIST 800-171"
                if level == 2
                else ("FAR 52.204-21" if level == 1 else "NIST 800-172")
            ),
        }

    def _run_gap_analysis(
        self,
        assessment_id: str,
        responses: Dict[str, Any],
        level: int,
    ) -> Dict[str, Any]:
        """Identify gaps; a Met status requires evidence_uri and SAO validation."""
        total = {
            1: CMMC_L1_PRACTICE_COUNT,
            2: CMMC_L2_PRACTICE_COUNT,
            3: CMMC_L3_PRACTICE_COUNT,
        }.get(level, 0)

        compliant = sum(1 for value in responses.values() if is_control_met(value))
        gaps = [control_id for control_id, value in responses.items() if not is_control_met(value)]
        unverified_assertions: Dict[str, str] = {}
        for control_id, value in responses.items():
            result = evaluate_control_response(value)
            if result.status in {"met", "implemented", "yes", "compliant"} and not result.allowed_met:
                unverified_assertions[control_id] = result.reason

        return {
            "assessment_id": assessment_id,
            "level": level,
            "total_controls": total,
            "compliant": compliant,
            "non_compliant": len(gaps),
            "compliance_pct": round(100 * compliant / total, 1) if total else 0,
            "gaps": gaps[:50],
            "gap_count": len(gaps),
            "unverified_assertions": unverified_assertions,
            "evidence_gate": "Met requires evidence_uri and sao_validated=true",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _generate_poam(
        self,
        gap_analysis: Dict[str, Any],
        priority: str = "high",
    ) -> Dict[str, Any]:
        """Generate Plan of Action and Milestones for evidence-gated gaps."""
        gaps = gap_analysis.get("gaps", [])
        items = []
        for i, control_id in enumerate(gaps, 1):
            items.append(
                {
                    "id": f"POAM-{i:04d}",
                    "control_id": control_id,
                    "finding": f"Control {control_id} is not supported by validated evidence",
                    "priority": priority,
                    "responsible": "TBD",
                    "due_date": "TBD",
                    "resources": [],
                    "milestones": [],
                }
            )
        return {
            "assessment_id": gap_analysis.get("assessment_id"),
            "level": gap_analysis.get("level"),
            "total_findings": len(items),
            "items": items,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle compliance tasks."""
        task_type = task.get("type", "")
        if task_type == "get_framework":
            level = task.get("level", 2)
            return {"status": "success", "result": self._get_control_framework(level)}
        if task_type == "self_assess":
            assessment_id = (
                task.get("assessment_id") or f"assess-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
            )
            level = task.get("level", 2)
            responses = task.get("responses", {})
            self._assessments[assessment_id] = {"level": level, "responses": responses}
            gap = self._run_gap_analysis(assessment_id, responses, level)
            return {
                "status": "success",
                "result": {"assessment_id": assessment_id, "gap_analysis": gap},
            }
        if task_type == "gap_analysis":
            assessment_id = task.get("assessment_id")
            if not assessment_id or assessment_id not in self._assessments:
                return {"status": "error", "message": "Unknown assessment_id"}
            assessment = self._assessments[assessment_id]
            gap = self._run_gap_analysis(
                assessment_id,
                assessment["responses"],
                assessment["level"],
            )
            return {"status": "success", "result": gap}
        if task_type == "generate_poam":
            gap = task.get("gap_analysis")
            if not gap:
                assessment_id = task.get("assessment_id")
                if assessment_id and assessment_id in self._assessments:
                    assessment = self._assessments[assessment_id]
                    gap = self._run_gap_analysis(
                        assessment_id,
                        assessment["responses"],
                        assessment["level"],
                    )
                else:
                    return {"status": "error", "message": "gap_analysis or assessment_id required"}
            poam = self._generate_poam(gap, task.get("priority", "high"))
            return {"status": "success", "result": poam}
        if task_type == "exostar_status":
            exostar = self._get_exostar()
            if not exostar:
                return {"status": "error", "message": "Exostar client not available"}
            result = await exostar.check_compliance_status(task.get("entity_id"))
            return {"status": "success", "result": result}
        if task_type == "nist_mapping":
            level = task.get("level", 2)
            framework = self._get_control_framework(level)
            return {
                "status": "success",
                "result": {"mapping": framework["nist_mapping"], "framework": framework},
            }
        return {"status": "error", "message": f"Unknown task type: {task_type}"}
