from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class GateDecision:
    allowed: bool
    reason: str
    required_approvals: List[str]


class SafetyGateService:
    """
    Phase 3.1 gatekeeper for all physical actions.
    """

    NON_DESTRUCTIVE_ACTIONS = {
        "camera_rotate",
        "set_sampling_rate",
        "signal_emit",
        "look_up",
    }

    def evaluate(self, action_type: str, request: Dict[str, Any]) -> GateDecision:
        if action_type in self.NON_DESTRUCTIVE_ACTIONS:
            return GateDecision(
                allowed=True, reason="non_destructive_action", required_approvals=[]
            )

        if action_type in {"gripper_close", "arm_move_precise"}:
            return GateDecision(
                allowed=False,
                reason="human_approval_required",
                required_approvals=["human_operator"],
            )

        return GateDecision(
            allowed=False,
            reason="unknown_action_blocked",
            required_approvals=["human_operator", "safety_admin"],
        )
