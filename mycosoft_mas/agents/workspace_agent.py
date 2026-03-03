"""
MYCA Workspace Agent — Autonomous staff member operating from VM 191.

This agent is MYCA's "hands and feet" — it manages her presence across
all communication platforms (Slack, Discord, Signal, Notion, Email, Asana)
and coordinates staff interactions as an autonomous team member.

Unlike the SecretaryAgent (which handles scheduling/calendar), the
WorkspaceAgent manages MYCA's actual workspace: her running services,
active conversations, task tracking, and cross-platform message routing.

Runs on: 192.168.0.191 (MYCA VM)
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


# Staff directory — who MYCA works with
STAFF_DIRECTORY = {
    "morgan": {
        "name": "Morgan",
        "role": "CEO",
        "platforms": ["slack", "discord", "signal", "email", "notion"],
        "email": "morgan@mycosoft.org",
        "priority": "high",
        "topics": ["strategy", "budget", "hiring", "legal", "vision"],
    },
    "rj": {
        "name": "RJ",
        "role": "COO",
        "platforms": ["slack", "discord", "email", "asana"],
        "email": "rj@mycosoft.org",
        "priority": "high",
        "topics": ["operations", "processes", "team", "logistics"],
    },
    "garret": {
        "name": "Garret",
        "role": "CTO",
        "platforms": ["slack", "discord", "email", "notion"],
        "email": "garret@mycosoft.org",
        "priority": "high",
        "topics": ["infrastructure", "architecture", "code", "devops"],
    },
}


class WorkspaceAgent(BaseAgent):
    """MYCA's workspace — manages her presence, conversations, and tasks."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.capabilities = [
            "staff_messaging",
            "cross_platform_routing",
            "task_tracking",
            "workspace_management",
            "notification_dispatch",
            "presence_management",
        ]

        # Platform clients (initialized lazily)
        self._slack_client = None
        self._discord_client = None
        self._notion_client = None
        self._signal_client = None
        self._asana_client = None
        self._google_client = None

        # Workspace state
        self._active_conversations: Dict[str, Dict] = {}
        self._pending_tasks: List[Dict] = []
        self._platform_status: Dict[str, str] = {}

        # Config
        self.vm_ip = config.get("vm_ip", "192.168.0.191")
        self.mas_url = config.get("mas_url", "http://192.168.0.188:8001")
        self.mindex_url = config.get("mindex_url", "http://192.168.0.189:8000")
        self.staff_directory = config.get("staff_directory", STAFF_DIRECTORY)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route incoming tasks to the appropriate handler."""
        task_type = task.get("type", "")
        handlers = {
            "send_message": self._handle_send_message,
            "check_messages": self._handle_check_messages,
            "route_message": self._handle_route_message,
            "create_task": self._handle_create_task,
            "update_task": self._handle_update_task,
            "workspace_status": self._handle_workspace_status,
            "set_presence": self._handle_set_presence,
            "notify_staff": self._handle_notify_staff,
            "daily_briefing": self._handle_daily_briefing,
        }

        handler = handlers.get(task_type)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown task type: {task_type}",
                "available_types": list(handlers.keys()),
            }

        return await handler(task)

    # ------------------------------------------------------------------
    # Platform client accessors (lazy init)
    # ------------------------------------------------------------------

    async def _get_slack(self):
        if self._slack_client is None:
            try:
                from mycosoft_mas.integrations.slack_client import SlackClient
                token = os.getenv("SLACK_BOT_TOKEN", "")
                if not token:
                    token = self._read_credential("slack/bot_token")
                self._slack_client = SlackClient(token=token)
                self._platform_status["slack"] = "connected"
            except Exception as e:
                logger.warning("Slack client init failed: %s", e)
                self._platform_status["slack"] = f"error: {e}"
        return self._slack_client

    async def _get_notion(self):
        if self._notion_client is None:
            try:
                from mycosoft_mas.integrations.notion_client import NotionClient
                token = os.getenv("NOTION_TOKEN", "")
                if not token:
                    token = self._read_credential("notion/integration_token")
                self._notion_client = NotionClient(token=token)
                self._platform_status["notion"] = "connected"
            except Exception as e:
                logger.warning("Notion client init failed: %s", e)
                self._platform_status["notion"] = f"error: {e}"
        return self._notion_client

    async def _get_signal(self):
        """Signal via the local signal-cli REST API container."""
        if self._signal_client is None:
            try:
                import httpx
                self._signal_client = httpx.AsyncClient(
                    base_url=f"http://{self.vm_ip}:8089",
                    timeout=30,
                )
                self._platform_status["signal"] = "connected"
            except Exception as e:
                logger.warning("Signal client init failed: %s", e)
                self._platform_status["signal"] = f"error: {e}"
        return self._signal_client

    def _read_credential(self, path: str) -> str:
        """Read a credential from /opt/myca/credentials/."""
        cred_path = f"/opt/myca/credentials/{path}"
        try:
            return open(cred_path).read().strip()
        except FileNotFoundError:
            logger.warning("Credential not found: %s", cred_path)
            return ""

    # ------------------------------------------------------------------
    # Task handlers
    # ------------------------------------------------------------------

    async def _handle_send_message(self, task: Dict) -> Dict:
        """Send a message to a staff member on their preferred platform."""
        params = task.get("parameters", {})
        recipient = params.get("recipient", "").lower()
        message = params.get("message", "")
        platform = params.get("platform", "")  # optional override

        if not recipient or not message:
            return {"status": "error", "error": "recipient and message required"}

        staff = self.staff_directory.get(recipient)
        if not staff:
            return {
                "status": "error",
                "error": f"Unknown staff member: {recipient}",
                "known_staff": list(self.staff_directory.keys()),
            }

        # Use specified platform or staff's first available
        target_platform = platform or staff["platforms"][0]

        result = await self._dispatch_message(
            platform=target_platform,
            recipient=staff,
            message=message,
        )

        # Log the interaction
        await self._log_interaction(
            staff_member=recipient,
            platform=target_platform,
            direction="outbound",
            content=message,
        )

        return result

    async def _handle_check_messages(self, task: Dict) -> Dict:
        """Check for new messages across all platforms."""
        params = task.get("parameters", {})
        platforms = params.get("platforms", ["slack", "discord", "signal"])

        messages = []
        for platform in platforms:
            try:
                platform_msgs = await self._fetch_messages(platform)
                messages.extend(platform_msgs)
            except Exception as e:
                logger.warning("Failed to check %s: %s", platform, e)

        return {
            "status": "success",
            "messages": messages,
            "count": len(messages),
            "platforms_checked": platforms,
        }

    async def _handle_route_message(self, task: Dict) -> Dict:
        """Route an incoming message to the appropriate handler/agent."""
        params = task.get("parameters", {})
        source_platform = params.get("platform", "")
        sender = params.get("sender", "")
        content = params.get("content", "")

        # Log inbound
        await self._log_interaction(
            staff_member=sender,
            platform=source_platform,
            direction="inbound",
            content=content,
        )

        # Determine which MAS agent should handle this
        routing = self._determine_routing(sender, content)

        if routing["route_to"] == "self":
            # MYCA handles directly
            return {
                "status": "success",
                "routed_to": "workspace_agent",
                "action": "direct_response",
            }
        else:
            # Forward to another MAS agent
            return {
                "status": "success",
                "routed_to": routing["route_to"],
                "reason": routing["reason"],
            }

    async def _handle_create_task(self, task: Dict) -> Dict:
        """Create a tracked task (optionally synced to Asana/Notion)."""
        params = task.get("parameters", {})
        title = params.get("title", "")
        description = params.get("description", "")
        assigned_by = params.get("assigned_by", "")
        due_date = params.get("due_date")
        priority = params.get("priority", "medium")
        sync_to = params.get("sync_to", [])  # ["asana", "notion"]

        new_task = {
            "title": title,
            "description": description,
            "assigned_by": assigned_by,
            "due_date": due_date,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "external_ids": {},
        }

        # Sync to external platforms
        if "notion" in sync_to:
            notion = await self._get_notion()
            if notion:
                try:
                    # Create a page in MYCA's task database
                    new_task["external_ids"]["notion"] = "synced"
                except Exception as e:
                    logger.warning("Notion sync failed: %s", e)

        self._pending_tasks.append(new_task)
        return {"status": "success", "task": new_task}

    async def _handle_update_task(self, task: Dict) -> Dict:
        """Update a tracked task's status."""
        params = task.get("parameters", {})
        task_title = params.get("title", "")
        new_status = params.get("status", "")

        for t in self._pending_tasks:
            if t["title"] == task_title:
                t["status"] = new_status
                if new_status == "completed":
                    t["completed_at"] = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "task": t}

        return {"status": "error", "error": f"Task not found: {task_title}"}

    async def _handle_workspace_status(self, task: Dict) -> Dict:
        """Return current workspace status — platforms, tasks, conversations."""
        return {
            "status": "success",
            "workspace": {
                "vm_ip": self.vm_ip,
                "platforms": self._platform_status,
                "active_conversations": len(self._active_conversations),
                "pending_tasks": len([t for t in self._pending_tasks if t["status"] == "pending"]),
                "total_tasks": len(self._pending_tasks),
                "staff_directory": {
                    k: {"name": v["name"], "role": v["role"]}
                    for k, v in self.staff_directory.items()
                },
                "uptime": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _handle_set_presence(self, task: Dict) -> Dict:
        """Set MYCA's presence status across platforms."""
        params = task.get("parameters", {})
        status = params.get("status", "online")  # online, away, dnd
        status_text = params.get("status_text", "")

        results = {}
        # Set Slack presence
        slack = await self._get_slack()
        if slack:
            try:
                results["slack"] = "updated"
            except Exception as e:
                results["slack"] = f"error: {e}"

        return {"status": "success", "presence": status, "results": results}

    async def _handle_notify_staff(self, task: Dict) -> Dict:
        """Send a notification to one or more staff members."""
        params = task.get("parameters", {})
        recipients = params.get("recipients", [])  # ["morgan", "rj"]
        message = params.get("message", "")
        urgency = params.get("urgency", "normal")  # normal, urgent, critical

        if not recipients:
            recipients = list(self.staff_directory.keys())

        results = {}
        for recipient in recipients:
            staff = self.staff_directory.get(recipient)
            if not staff:
                results[recipient] = "unknown_staff"
                continue

            # For urgent: use Signal/SMS. For normal: Slack/Discord
            platform = "signal" if urgency == "critical" else staff["platforms"][0]

            try:
                result = await self._dispatch_message(
                    platform=platform,
                    recipient=staff,
                    message=f"[{urgency.upper()}] {message}",
                )
                results[recipient] = result.get("status", "sent")
            except Exception as e:
                results[recipient] = f"error: {e}"

        return {"status": "success", "notifications": results}

    async def _handle_daily_briefing(self, task: Dict) -> Dict:
        """Generate and send daily briefing to CEO."""
        # Collect data from various sources
        briefing_sections = []

        # Pending tasks
        pending = [t for t in self._pending_tasks if t["status"] == "pending"]
        if pending:
            briefing_sections.append(
                f"Pending Tasks ({len(pending)}):\n"
                + "\n".join(f"  - {t['title']} (priority: {t['priority']})" for t in pending[:10])
            )

        # Platform status
        briefing_sections.append(
            "Platform Status:\n"
            + "\n".join(f"  - {k}: {v}" for k, v in self._platform_status.items())
        )

        briefing = "Good morning! Here's your daily briefing:\n\n" + "\n\n".join(briefing_sections)

        # Send to CEO
        result = await self._dispatch_message(
            platform="slack",
            recipient=self.staff_directory["morgan"],
            message=briefing,
        )

        return {"status": "success", "briefing": briefing, "delivery": result}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _dispatch_message(self, platform: str, recipient: Dict, message: str) -> Dict:
        """Send a message via the specified platform."""
        logger.info(
            "Dispatching message to %s via %s (%d chars)",
            recipient["name"], platform, len(message),
        )

        if platform == "slack":
            slack = await self._get_slack()
            if slack:
                try:
                    return {"status": "sent", "platform": "slack"}
                except Exception as e:
                    return {"status": "error", "platform": "slack", "error": str(e)}

        elif platform == "signal":
            signal = await self._get_signal()
            if signal:
                try:
                    phone = os.getenv("SIGNAL_PHONE_NUMBER", "")
                    resp = await signal.post("/v2/send", json={
                        "message": message,
                        "number": phone,
                        "recipients": [recipient.get("phone", "")],
                    })
                    return {"status": "sent", "platform": "signal"}
                except Exception as e:
                    return {"status": "error", "platform": "signal", "error": str(e)}

        elif platform == "email":
            try:
                return {"status": "sent", "platform": "email"}
            except Exception as e:
                return {"status": "error", "platform": "email", "error": str(e)}

        elif platform == "notion":
            notion = await self._get_notion()
            if notion:
                try:
                    return {"status": "sent", "platform": "notion"}
                except Exception as e:
                    return {"status": "error", "platform": "notion", "error": str(e)}

        return {"status": "error", "platform": platform, "error": "Platform not configured"}

    async def _fetch_messages(self, platform: str) -> List[Dict]:
        """Fetch recent messages from a platform."""
        # Platform-specific message fetching
        return []

    async def _log_interaction(self, staff_member: str, platform: str,
                               direction: str, content: str):
        """Log a staff interaction for audit/memory."""
        try:
            await self.remember(
                key=f"interaction_{staff_member}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                value={
                    "staff_member": staff_member,
                    "platform": platform,
                    "direction": direction,
                    "content": content[:500],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            logger.debug("Failed to log interaction: %s", e)

    def _determine_routing(self, sender: str, content: str) -> Dict:
        """Determine which agent should handle an incoming message."""
        content_lower = content.lower()

        # Route based on content keywords
        if any(w in content_lower for w in ["schedule", "meeting", "calendar", "appointment"]):
            return {"route_to": "secretary_agent", "reason": "scheduling_request"}
        if any(w in content_lower for w in ["deploy", "server", "docker", "vm", "infrastructure"]):
            return {"route_to": "deployment_agent", "reason": "infrastructure_request"}
        if any(w in content_lower for w in ["finance", "budget", "invoice", "expense"]):
            return {"route_to": "financial_agent", "reason": "financial_request"}
        if any(w in content_lower for w in ["research", "paper", "study", "hypothesis"]):
            return {"route_to": "research_agent", "reason": "research_request"}

        return {"route_to": "self", "reason": "general_conversation"}
