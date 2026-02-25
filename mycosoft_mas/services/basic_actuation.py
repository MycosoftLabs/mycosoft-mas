from __future__ import annotations

from typing import Any, Dict

from mycosoft_mas.services.action_logging import ActionLoggingService
from mycosoft_mas.services.safety_gates import SafetyGateService


class BasicActuationService:
    """
    Phase 3.2 + 3.3:
    - non-destructive actuation only
    - full action/outcome logging
    """

    def __init__(self) -> None:
        self._gates = SafetyGateService()
        self._logger = ActionLoggingService()

    async def execute(self, action_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        decision = self._gates.evaluate(action_type=action_type, request=payload)
        if not decision.allowed:
            record = await self._logger.log_action(
                action_type=action_type,
                request=payload,
                outcome={"status": "blocked", "reason": decision.reason},
                approved=False,
            )
            return {
                "status": "blocked",
                "reason": decision.reason,
                "required_approvals": decision.required_approvals,
                "action_id": record.action_id,
            }

        # The concrete hardware integrations are delegated to embodiment clients.
        outcome = {"status": "executed", "action_type": action_type, "payload": payload}
        record = await self._logger.log_action(
            action_type=action_type,
            request=payload,
            outcome=outcome,
            approved=True,
        )
        return {"status": "ok", "action_id": record.action_id, "outcome": outcome}

