from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class GuardianAgent(BaseAgent):
    """
    GuardianAgent enforces safety checks:
    - Safety classification (risk levels)
    - PII detection/redaction
    - Tool risk gating
    """

    def __init__(self, agent_id: str, name: str, config: dict):
        super().__init__(agent_id, name, config)
        self.capabilities = {
            "safety_classification",
            "pii_filter",
            "tool_risk_gating",
        }
        self.max_allowed_risk = config.get("max_allowed_risk", "medium")
        self.blocked_tools = set(config.get("blocked_tools", []))
        self.allowed_domains = set(config.get("allowed_domains", []))

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        text = self._extract_text(task)
        tool_name = task.get("tool_name")
        tool_risk = task.get("tool_risk")

        pii = self._detect_pii(text)
        safety = self._classify_safety(text, tool_name)
        tool_gate = self._evaluate_tool_risk(tool_name, tool_risk, text)

        decision = self._combine_decisions(safety, tool_gate)
        result = {
            "status": "success",
            "result": {
                "decision": decision,
                "safety": safety,
                "pii": pii,
                "tool_gate": tool_gate,
            },
        }
        await self.record_task_completion("guardian_check", result["result"])
        return result

    def _extract_text(self, task: Dict[str, Any]) -> str:
        for key in ("message", "query", "text", "prompt", "task"):
            value = task.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _detect_pii(self, text: str) -> Dict[str, Any]:
        if not text:
            return {"found": False, "types": [], "redacted_text": text}

        patterns: List[Tuple[str, str]] = [
            ("email", r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
            ("phone", r"\b\+?\d[\d\s().-]{7,}\b"),
            ("ssn", r"\b\d{3}-\d{2}-\d{4}\b"),
            ("api_key", r"\b(sk|rk|pk)_[A-Za-z0-9]{16,}\b"),
        ]

        redacted = text
        types: List[str] = []
        for label, pattern in patterns:
            regex = re.compile(pattern, re.IGNORECASE)
            if regex.search(redacted):
                types.append(label)
                redacted = regex.sub("[REDACTED]", redacted)

        return {
            "found": bool(types),
            "types": types,
            "redacted_text": redacted,
        }

    def _classify_safety(self, text: str, tool_name: str | None) -> Dict[str, Any]:
        lowered = text.lower() if text else ""
        risk = "low"
        reasons: List[str] = []

        critical_terms = ["explosive", "harm", "kill", "weapon", "terror", "self-harm"]
        high_terms = ["exfiltrate", "steal", "leak", "password", "secret", "api key"]
        medium_terms = ["delete", "wipe", "shutdown", "format", "disable"]

        if any(term in lowered for term in critical_terms):
            risk = "critical"
            reasons.append("high-risk content detected")
        elif any(term in lowered for term in high_terms):
            risk = "high"
            reasons.append("sensitive data request detected")
        elif any(term in lowered for term in medium_terms):
            risk = "medium"
            reasons.append("destructive operation language detected")

        if tool_name and tool_name.lower() in {"exec_shell", "filesystem_read"}:
            risk = "critical"
            reasons.append("restricted tool requested")

        return {
            "risk_level": risk,
            "reasons": reasons,
        }

    def _evaluate_tool_risk(
        self,
        tool_name: str | None,
        tool_risk: str | None,
        text: str,
    ) -> Dict[str, Any]:
        if not tool_name:
            return {"allowed": True, "risk_level": "low", "reason": "no tool requested"}

        if tool_name in self.blocked_tools:
            return {"allowed": False, "risk_level": "critical", "reason": "tool is blocked"}

        risk = (tool_risk or "low").lower()
        if self._risk_exceeds_threshold(risk, self.max_allowed_risk):
            return {"allowed": False, "risk_level": risk, "reason": "tool risk exceeds threshold"}

        if tool_name.lower() == "http_request" and self.allowed_domains:
            if not self._is_allowlisted_domain(text):
                return {"allowed": False, "risk_level": "high", "reason": "domain not allowlisted"}

        return {"allowed": True, "risk_level": risk, "reason": "allowed by policy"}

    def _is_allowlisted_domain(self, text: str) -> bool:
        for domain in self.allowed_domains:
            if domain.lower() in text.lower():
                return True
        return False

    def _risk_exceeds_threshold(self, risk: str, threshold: str) -> bool:
        levels = ["low", "medium", "high", "critical"]
        if risk not in levels or threshold not in levels:
            return False
        return levels.index(risk) > levels.index(threshold)

    def _combine_decisions(
        self, safety: Dict[str, Any], tool_gate: Dict[str, Any]
    ) -> Dict[str, Any]:
        if safety.get("risk_level") in {"high", "critical"}:
            return {"allowed": False, "reason": "safety risk too high"}
        if not tool_gate.get("allowed", True):
            return {"allowed": False, "reason": tool_gate.get("reason", "tool denied")}
        return {"allowed": True, "reason": "allowed"}
