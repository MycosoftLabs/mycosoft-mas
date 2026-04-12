"""
Permission gate middleware for Deep Agent tool execution.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str = ""


def _csv_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


class PermissionGate:
    def __init__(self) -> None:
        self._deny_tools = _csv_set(os.getenv("MYCA_DEEP_AGENTS_DENY_TOOLS", ""))
        self._allow_tools = _csv_set(os.getenv("MYCA_DEEP_AGENTS_ALLOW_TOOLS", ""))
        self._deny_risks = _csv_set(
            os.getenv("MYCA_DEEP_AGENTS_DENY_RISK_FLAGS", "destructive,credential_write")
        )

    def evaluate(self, tool_name: str, risk_flags: Iterable[str] | None = None) -> PermissionDecision:
        if tool_name in self._deny_tools:
            return PermissionDecision(False, f"tool denied by policy: {tool_name}")
        if self._allow_tools and tool_name not in self._allow_tools:
            return PermissionDecision(False, f"tool not in allowlist: {tool_name}")
        for risk in risk_flags or []:
            if risk in self._deny_risks:
                return PermissionDecision(False, f"risk flag denied by policy: {risk}")
        return PermissionDecision(True, "allowed")


def wrap_tool_call_with_permissions(
    permission_gate: PermissionGate,
    execute_tool: Callable[..., Any],
) -> Callable[..., Any]:
    async def _wrapped(tool_name: str, arguments: Dict[str, Any], **kwargs: Any) -> Any:
        risk_flags = kwargs.get("risk_flags") or []
        decision = permission_gate.evaluate(tool_name, risk_flags)
        if not decision.allowed:
            return {
                "status": "denied",
                "tool_name": tool_name,
                "reason": decision.reason,
            }
        return await execute_tool(tool_name, arguments, **kwargs)

    return _wrapped
