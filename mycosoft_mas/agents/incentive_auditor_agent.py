"""
Incentive Auditor Agent - MYCA Ethics

Always-on agent that scores every task/recommendation for manipulation risk.
Flags certainty theater, monitors incentive alignment, logs to Event Ledger.
Integrates with GuardianAgent for high-risk escalation.

Created: March 3, 2026
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from mycosoft_mas.agents.base_agent import BaseAgent
except Exception:
    BaseAgent = object  # type: ignore

from mycosoft_mas.ethics.incentive_gate import IncentiveGate, IncentiveGateResult

logger = logging.getLogger(__name__)

# Lazy Event Ledger
_event_ledger = None


def _get_event_ledger():
    global _event_ledger
    if _event_ledger is None:
        try:
            from mycosoft_mas.myca.event_ledger import EventLedger
            _event_ledger = EventLedger()
        except ImportError:
            logger.debug("EventLedger not available - using in-memory audit store")
    return _event_ledger


class IncentiveAuditorAgent(BaseAgent if BaseAgent is not object else object):  # type: ignore
    """
    Scores tasks for manipulation risk, certainty theater, incentive alignment.
    Logs all audits to Event Ledger for immutable audit trail.
    """

    def __init__(self, agent_id: str = "incentive-auditor", name: str = "Incentive Auditor", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, name, config or {})
        self.capabilities.add("ethics_audit")
        self.capabilities.add("manipulation_detection")
        self.capabilities.add("certainty_theater_detection")
        self._gate = IncentiveGate()
        self._audit_store: Dict[str, Dict[str, Any]] = {}  # task_id -> audit result

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process audit task. Task type 'audit' runs ethics evaluation."""
        task_type = task.get("type", "audit")
        if task_type != "audit":
            return {"status": "success", "result": {"message": "Use type=audit for ethics evaluation"}}

        content = task.get("content", "") or task.get("text", "") or str(task.get("payload", ""))
        task_id = task.get("task_id") or str(uuid.uuid4())
        context = task.get("context", {})

        result = await self.audit(content, task_id=task_id, context=context)
        return {
            "status": "success",
            "result": result,
            "task_id": task_id,
        }

    async def audit(
        self,
        content: str,
        task_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run incentive gate evaluation and log to Event Ledger.
        Returns manipulation score, certainty_theater, beneficiaries, etc.
        """
        task_id = task_id or str(uuid.uuid4())
        context = context or {}

        gate_result: IncentiveGateResult = await self._gate.evaluate(content, context)

        audit_record = {
            "task_id": task_id,
            "manipulation_score": gate_result.manipulation_score,
            "certainty_theater": gate_result.certainty_theater,
            "false_urgency": gate_result.false_urgency,
            "dopamine_hooks": gate_result.dopamine_hooks,
            "beneficiaries": gate_result.beneficiaries,
            "passed": gate_result.passed,
            "timestamp": datetime.utcnow().isoformat(),
            "report": gate_result.report,
        }

        self._audit_store[task_id] = audit_record

        # Log to Event Ledger if available
        ledger = _get_event_ledger()
        if ledger:
            try:
                risk_flags = []
                if gate_result.certainty_theater:
                    risk_flags.append("certainty_theater")
                if gate_result.false_urgency:
                    risk_flags.append("false_urgency")
                if gate_result.manipulation_score >= 50:
                    risk_flags.append(f"manipulation_score:{gate_result.manipulation_score:.0f}")
                ledger.log_risk_event(
                    agent=self.agent_id,
                    event_type="ethics_audit",
                    description=f"Task {task_id}: manipulation_score={gate_result.manipulation_score:.0f}, passed={gate_result.passed}",
                    risk_flags=risk_flags,
                    context={"task_id": task_id, "manipulation_score": gate_result.manipulation_score, "passed": gate_result.passed},
                )
            except Exception as e:
                logger.warning("Failed to log to EventLedger: %s", e)

        # Escalate to GuardianAgent if score is high (optional integration)
        if gate_result.manipulation_score >= 80:
            try:
                from mycosoft_mas.safety.guardian_agent import GuardianAgent, RiskLevel
                guardian = GuardianAgent()
                await guardian.evaluate_action("ethics_audit", {
                    "manipulation_score": gate_result.manipulation_score,
                    "task_id": task_id,
                    "content_preview": content[:200],
                })
            except Exception as e:
                logger.debug("GuardianAgent escalation skipped: %s", e)

        return audit_record

    def get_audit(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve audit record by task_id."""
        return self._audit_store.get(task_id)
