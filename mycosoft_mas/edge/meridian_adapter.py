"""
Meridian adapter for the CFO VM — bridges Perplexity desktop to MAS CFO MCP.

Runs on the CFO VM (192.168.0.193). Identifies as Meridian/CFO/Perplexity,
connects to the MAS-hosted CFO MCP API, and relays outputs to C-Suite report
and escalation endpoints.

Usage:
  - call_cfo_tool(name, args) — delegate to CFO MCP
  - send_heartbeat() — register with C-Suite
  - send_report(report_type, summary, ...) — submit reports to MAS
  - send_escalation(...) — escalate to Morgan when needed

Created: March 8, 2026
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("MeridianAdapter")

# Default MAS API URL (CFO VM reaches MAS at 188)
DEFAULT_MAS_API_URL = os.environ.get("MAS_API_URL", "http://192.168.0.188:8001")
DEFAULT_CFO_VM_IP = os.environ.get("CFO_VM_IP", "192.168.0.193")


class MeridianAdapter:
    """Thin adapter for Meridian (CFO) on the Perplexity desktop VM."""

    def __init__(
        self,
        mas_api_url: str = DEFAULT_MAS_API_URL,
        cfo_vm_ip: str = DEFAULT_CFO_VM_IP,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.mas_api_url = mas_api_url.rstrip("/")
        self.cfo_vm_ip = cfo_vm_ip
        self.timeout = httpx.Timeout(timeout_seconds)
        self._role = "CFO"
        self._assistant_name = "Meridian"
        self._primary_tool = "Perplexity"

    async def call_cfo_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call a CFO MCP tool and return the result."""
        url = f"{self.mas_api_url}/api/cfo-mcp/tools/call"
        payload = {"name": name, "arguments": arguments or {}}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    async def send_heartbeat(self, status: str = "healthy") -> Dict[str, Any]:
        """Register heartbeat with C-Suite."""
        url = f"{self.mas_api_url}/api/csuite/heartbeat"
        payload = {
            "role": self._role,
            "assistant_name": self._assistant_name,
            "ip": self.cfo_vm_ip,
            "status": status,
            "primary_tool": self._primary_tool,
            "extra": {"source": "meridian_adapter"},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    async def send_report(
        self,
        report_type: str,
        summary: str,
        details: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        escalated: bool = False,
    ) -> Dict[str, Any]:
        """Submit a report to the C-Suite API."""
        url = f"{self.mas_api_url}/api/csuite/report"
        payload = {
            "role": self._role,
            "assistant_name": self._assistant_name,
            "report_type": report_type,
            "summary": summary,
            "details": details,
            "task_id": task_id,
            "escalated": escalated,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    async def send_escalation(
        self,
        subject: str,
        context: str,
        options: Optional[list[str]] = None,
        urgency: str = "normal",
    ) -> Dict[str, Any]:
        """Escalate to Morgan when a decision is needed."""
        url = f"{self.mas_api_url}/api/csuite/escalate"
        payload = {
            "role": self._role,
            "assistant_name": self._assistant_name,
            "subject": subject,
            "context": context,
            "options": options,
            "urgency": urgency,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    async def list_finance_tools(self) -> Dict[str, Any]:
        """List available CFO MCP tools."""
        url = f"{self.mas_api_url}/api/cfo-mcp/tools"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def submit_prompt_as_task(
        self,
        prompt: str,
        agent_id: str = "financial",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Package a Perplexity desktop prompt as a finance task and delegate.
        Uses delegate_finance_task; defaults to 'financial' agent.
        """
        task = {
            "type": "research",
            "description": prompt,
            "params": {"priority": "normal", "task_id": task_id},
        }
        return await self.call_cfo_tool("delegate_finance_task", {
            "agent_id": agent_id,
            "task": task,
        })
