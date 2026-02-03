"""Guardian Agent - Safety monitoring. Created: February 3, 2026"""
import logging
from typing import Any, Dict, List
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class GuardianAgent:
    """Monitors and enforces safety policies."""
    
    def __init__(self):
        self.active = True
        self.blocked_actions: List[str] = []
        self.risk_thresholds = {"lab_operation": RiskLevel.MEDIUM, "data_access": RiskLevel.LOW, "external_communication": RiskLevel.MEDIUM}
    
    async def evaluate_action(self, action_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        risk = self._assess_risk(action_type, parameters)
        threshold = self.risk_thresholds.get(action_type, RiskLevel.MEDIUM)
        approved = self._compare_risk(risk, threshold)
        if not approved:
            self.blocked_actions.append(action_type)
            logger.warning(f"Blocked action: {action_type} (risk: {risk.value})")
        return {"approved": approved, "risk_level": risk.value, "action": action_type}
    
    def _assess_risk(self, action_type: str, parameters: Dict[str, Any]) -> RiskLevel:
        if "dangerous" in str(parameters).lower():
            return RiskLevel.CRITICAL
        if action_type in ["stimulate", "inject", "modify_genome"]:
            return RiskLevel.HIGH
        return RiskLevel.LOW
    
    def _compare_risk(self, risk: RiskLevel, threshold: RiskLevel) -> bool:
        levels = [RiskLevel.NONE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        return levels.index(risk) <= levels.index(threshold)
    
    def get_blocked_actions(self) -> List[str]:
        return self.blocked_actions
