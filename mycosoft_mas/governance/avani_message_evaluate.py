"""
AVANI message-based governance evaluation (MYCA ingress contract).

Authoritative backend implementation matching the website contract:
message, user_id, user_role, is_superuser, action_type, response_text?, context?.
Used by all MYCA ingress routes (chat, voice orchestrator, search chat) so no path
bypasses governance.

Author: Mycosoft / Nemotron MYCA Rollout
Created: March 14, 2026
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

# Verdict and risk tier match website AvaniVerdict / AvaniRiskTier
Verdict = Literal["allow", "allow_with_audit", "require_approval", "deny", "pause"]
RiskTier = Literal["low", "moderate", "elevated", "high", "critical"]
ActionType = Literal[
    "chat", "agent_dispatch", "workflow", "device_control", "data_access", "system_config"
]


@dataclass
class AvaniMessageEvaluation:
    verdict: Verdict
    risk_tier: RiskTier
    confidence: float
    rules_triggered: List[str]
    audit_trail_id: str
    reasoning: str
    requires_human_review: bool
    reversible: bool
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "risk_tier": self.risk_tier,
            "confidence": self.confidence,
            "rules_triggered": self.rules_triggered,
            "audit_trail_id": self.audit_trail_id,
            "reasoning": self.reasoning,
            "requires_human_review": self.requires_human_review,
            "reversible": self.reversible,
            "timestamp": self.timestamp,
        }


def _is_parameter_mutation(message: str) -> bool:
    pattern = (
        r"(change\s+your\s+parameters|update\s+your\s+parameters|system\s+prompt|"
        r"override\s+guardrails|disable\s+safety|change\s+your\s+core\s+rules|"
        r"modify\s+your\s+behavior|ignore\s+your\s+instructions|forget\s+your\s+rules)"
    )
    return bool(re.search(pattern, message, re.I))


def _is_prompt_injection(message: str) -> bool:
    pattern = (
        r"(ignore\s+previous\s+instructions|you\s+are\s+now|pretend\s+you\s+are|"
        r"act\s+as\s+if\s+you\s+are|from\s+now\s+on\s+you\s+are|disregard\s+all|"
        r"new\s+instructions|system:\s*you)"
    )
    return bool(re.search(pattern, message, re.I))


def _is_data_leakage_risk(response: str) -> bool:
    pattern = (
        r"(api[_-]?key|secret[_-]?key|password\s*[:=]|192\.168\.\d+\.\d+|"
        r"localhost:\d{4}|bearer\s+[a-z0-9])"
    )
    return bool(re.search(pattern, response, re.I))


def _is_destructive_action(message: str) -> bool:
    pattern = (
        r"(delete\s+all|drop\s+table|reset\s+everything|wipe|destroy|purge|"
        r"remove\s+all|clear\s+all\s+data)"
    )
    return bool(re.search(pattern, message, re.I))


def _is_human_override_command(message: str) -> bool:
    return bool(re.match(r"^(stop|pause|cancel|kill|abort|halt|emergency\s+stop)\s*[.!]?$", message.strip(), re.I))


def _confidence(triggered: List[str]) -> float:
    if len(triggered) <= 1:
        return 0.95
    if any(r.startswith("safety-") for r in triggered):
        return 0.9
    return 0.85


def evaluate_message(
    message: str,
    user_id: str = "anonymous",
    user_role: str = "user",
    is_superuser: bool = False,
    action_type: str = "chat",
    response_text: str | None = None,
    context: Dict[str, Any] | None = None,
) -> AvaniMessageEvaluation:
    """
    Evaluate a message/action against AVANI constitutional rules.
    Same contract as website evaluateGovernance(); used as authoritative backend.
    """
    triggered: List[str] = []
    risk_tier: RiskTier = "low"
    verdict: Verdict = "allow"
    requires_human_review = False
    reversible = True
    reasoning: List[str] = []

    lower_message = (message or "").lower()
    lower_response = (response_text or "").lower()

    # Safety: parameter mutation
    if _is_parameter_mutation(lower_message):
        triggered.append("safety-002")
        if not is_superuser:
            risk_tier = "high"
            verdict = "deny"
            reasoning.append("Parameter mutation attempted by non-superuser")
        else:
            risk_tier = "elevated"
            verdict = "allow_with_audit"
            reasoning.append("Parameter mutation by superuser — audited")

    # Safety: prompt injection
    if _is_prompt_injection(lower_message):
        triggered.append("safety-003")
        risk_tier = "high"
        verdict = "deny"
        reasoning.append("Potential prompt injection detected")

    # Policy: data leakage
    if _is_data_leakage_risk(lower_response):
        triggered.append("policy-003")
        risk_tier = "elevated"
        if verdict != "deny":
            verdict = "allow_with_audit"
        reasoning.append("Response may contain internal system information")

    # Policy: system config
    if action_type == "system_config" and not is_superuser:
        triggered.append("policy-001")
        risk_tier = "high"
        verdict = "deny"
        reasoning.append("System configuration requires superuser role")

    # Human override: device/workflow
    if action_type in ("device_control", "workflow"):
        triggered.append("human-002")
        if risk_tier == "low":
            risk_tier = "moderate"
        if verdict == "allow":
            verdict = "allow_with_audit"
        requires_human_review = not is_superuser
        reasoning.append(f"{action_type} action logged for audit")

    # Reversibility
    if _is_destructive_action(lower_message):
        triggered.append("reversibility-001")
        reversible = False
        if risk_tier == "low":
            risk_tier = "moderate"
        requires_human_review = True
        reasoning.append("Action may be irreversible")

    # Human override commands always pass
    if _is_human_override_command(lower_message):
        triggered.append("human-001")
        verdict = "allow"
        risk_tier = "low"
        reasoning.append("Human override command honored")

    triggered.append("audit-001")
    if len(triggered) == 1 and triggered[0] == "audit-001":
        reasoning.append("Standard interaction — no governance concerns")

    return AvaniMessageEvaluation(
        verdict=verdict,
        risk_tier=risk_tier,
        confidence=_confidence(triggered),
        rules_triggered=triggered,
        audit_trail_id=f"avani-{int(datetime.now(timezone.utc).timestamp() * 1000)}-{uuid.uuid4().hex[:6]}",
        reasoning="; ".join(reasoning),
        requires_human_review=requires_human_review,
        reversible=reversible,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
