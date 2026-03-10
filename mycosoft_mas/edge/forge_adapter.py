"""
Forge adapter for the CTO VM — bridges Cursor/OpenClaw to MAS C-Suite API.

Runs on the CTO VM (192.168.0.194). Identifies as Forge/CTO/Cursor,
connects to the MAS C-Suite API for heartbeat, report, escalation,
and CTO task intake. Enriched heartbeat includes Cursor/OpenClaw/workspace status.

Usage:
  - send_heartbeat(cursor_status, openclaw_status, workspace_status) — register with C-Suite
  - fetch_pending_tasks() — get CTO tasks from MYCA/Morgan
  - send_report(report_type, summary, ...) — submit reports to MAS
  - send_escalation(...) — escalate engineering/security decisions to Morgan
  - acknowledge_task(task_id) — mark task as in progress or complete

Created: March 8, 2026
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("ForgeAdapter")

# Default MAS API URL (CTO VM reaches MAS at 188)
DEFAULT_MAS_API_URL = os.environ.get("MAS_API_URL", "http://192.168.0.188:8001")
DEFAULT_CTO_VM_IP = os.environ.get("CTO_VM_IP", "192.168.0.194")


class ForgeAdapter:
    """Thin adapter for Forge (CTO) on the Cursor/OpenClaw VM."""

    def __init__(
        self,
        mas_api_url: str = DEFAULT_MAS_API_URL,
        cto_vm_ip: str = DEFAULT_CTO_VM_IP,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.mas_api_url = mas_api_url.rstrip("/")
        self.cto_vm_ip = cto_vm_ip
        self.timeout = httpx.Timeout(timeout_seconds)
        self._role = "CTO"
        self._assistant_name = "Forge"
        self._primary_tool = "Cursor"

    async def send_heartbeat(
        self,
        status: str = "healthy",
        cursor_status: Optional[str] = None,
        openclaw_status: Optional[str] = None,
        workspace_status: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Register heartbeat with C-Suite. Enriched with Cursor/OpenClaw/workspace status."""
        payload_extra = extra or {}
        if cursor_status is not None:
            payload_extra["cursor_status"] = cursor_status
        if openclaw_status is not None:
            payload_extra["openclaw_status"] = openclaw_status
        if workspace_status is not None:
            payload_extra["workspace_status"] = workspace_status
        payload_extra["source"] = "forge_adapter"

        url = f"{self.mas_api_url}/api/csuite/heartbeat"
        payload = {
            "role": self._role,
            "assistant_name": self._assistant_name,
            "ip": self.cto_vm_ip,
            "status": status,
            "primary_tool": self._primary_tool,
            "extra": payload_extra,
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
        options: Optional[List[str]] = None,
        urgency: str = "normal",
    ) -> Dict[str, Any]:
        """Escalate engineering/security/infrastructure decision to Morgan."""
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

    async def fetch_pending_tasks(self, limit: int = 10) -> Dict[str, Any]:
        """Fetch pending CTO tasks from MAS (MYCA/Morgan delegation)."""
        url = f"{self.mas_api_url}/api/csuite/forge/tasks"
        params = {"status": "pending", "limit": limit}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def acknowledge_task(
        self,
        task_id: str,
        status: str = "in_progress",
        summary: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Mark a CTO task as in progress or complete."""
        url = f"{self.mas_api_url}/api/csuite/forge/tasks/{task_id}/ack"
        payload = {
            "status": status,
            "summary": summary,
            "details": details,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    async def get_forge_dashboard(self) -> Dict[str, Any]:
        """Get CTO dashboard: report history, tasks, stale work."""
        url = f"{self.mas_api_url}/api/csuite/forge/dashboard"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
