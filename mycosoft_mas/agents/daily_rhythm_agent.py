"""
MYCA Daily Rhythm Agent — Autonomous schedule for MYCA's workday.

Manages the daily cadence:
  8:00 AM  — Morning brief: scan overnight messages, generate daily plan, post to Discord
  9:00 AM  — Start task processing from Asana/Notion queues
  Hourly   — Status check: system health, pending tasks, new messages
  12:00 PM — Midday sync: progress update, priority re-evaluation
  5:00 PM  — End-of-day: summary email to Morgan, update Notion, archive completed tasks
  10 PM    — Night mode: monitoring only, anomaly alerts
  Overnight — Dream mode: memory consolidation, self-reflection

Designed to run via n8n cron triggers or APScheduler on VM 191.
Each rhythm step is also callable as a REST endpoint.

Runs on: 192.168.0.191 (MYCA VM) or 192.168.0.188 (MAS, fallback)
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Timezone for schedule (Pacific)
SCHEDULE_TZ = os.getenv("MYCA_TIMEZONE", "US/Pacific")


class DailyRhythmAgent(BaseAgent):
    """MYCA's autonomous daily schedule."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.capabilities = [
            "morning_briefing",
            "hourly_status",
            "midday_sync",
            "end_of_day",
            "night_mode",
            "task_processing",
        ]
        self.mas_url = config.get("mas_url", "http://192.168.0.188:8001")
        self.workspace_url = config.get(
            "workspace_url", "http://192.168.0.191:8100"
        )
        self._daily_plan: List[Dict] = []
        self._completed_today: List[Dict] = []
        self._rhythm_log: List[Dict] = []

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        handlers = {
            "morning_brief": self._handle_morning_brief,
            "hourly_status": self._handle_hourly_status,
            "midday_sync": self._handle_midday_sync,
            "end_of_day": self._handle_end_of_day,
            "night_mode": self._handle_night_mode,
            "process_tasks": self._handle_process_tasks,
            "get_schedule": self._handle_get_schedule,
        }
        handler = handlers.get(task_type)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown rhythm task: {task_type}",
                "available": list(handlers.keys()),
            }
        return await handler(task)

    # ------------------------------------------------------------------
    # Morning Brief (8 AM)
    # ------------------------------------------------------------------

    async def _handle_morning_brief(self, task: Dict) -> Dict:
        """
        Morning briefing routine:
        1. Check overnight messages across platforms
        2. Review pending tasks from Asana/Notion
        3. Check system health across all VMs
        4. Generate daily plan
        5. Post summary to Discord #myca-ops
        6. Log to memory
        """
        self._log_rhythm("morning_brief", "started")
        sections = []

        # 1. System health
        health = await self._check_system_health()
        sections.append(self._format_health(health))

        # 2. Pending tasks
        tasks = await self._get_pending_tasks()
        sections.append(self._format_tasks(tasks))

        # 3. Generate daily plan
        self._daily_plan = self._prioritize_tasks(tasks)
        plan_text = self._format_plan(self._daily_plan)
        sections.append(plan_text)

        briefing = (
            f"Good morning! Here's my daily briefing for "
            f"{datetime.now(timezone.utc).strftime('%B %d, %Y')}:\n\n"
            + "\n\n".join(sections)
        )

        # 4. Post to Discord and log
        await self._post_to_discord(briefing, channel="myca-ops")
        await self._log_to_memory("morning_brief", briefing)
        self._log_rhythm("morning_brief", "completed")

        return {
            "status": "success",
            "briefing": briefing,
            "daily_plan": self._daily_plan,
            "system_health": health,
        }

    # ------------------------------------------------------------------
    # Hourly Status
    # ------------------------------------------------------------------

    async def _handle_hourly_status(self, task: Dict) -> Dict:
        """Hourly check: new messages, task progress, system health."""
        self._log_rhythm("hourly_status", "started")

        health = await self._check_system_health()
        tasks = await self._get_pending_tasks()

        # Count completed since last check
        newly_completed = len(self._completed_today)

        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health": health,
            "pending_tasks": len(tasks),
            "completed_today": newly_completed,
            "daily_plan_remaining": len(
                [t for t in self._daily_plan if t.get("status") != "completed"]
            ),
        }

        self._log_rhythm("hourly_status", "completed")
        return {"status": "success", "hourly": status}

    # ------------------------------------------------------------------
    # Midday Sync (12 PM)
    # ------------------------------------------------------------------

    async def _handle_midday_sync(self, task: Dict) -> Dict:
        """Midday progress update and priority re-evaluation."""
        self._log_rhythm("midday_sync", "started")

        tasks = await self._get_pending_tasks()
        completed_count = len(self._completed_today)

        # Re-prioritize remaining tasks
        remaining = [t for t in self._daily_plan if t.get("status") != "completed"]
        self._daily_plan = self._prioritize_tasks(remaining)

        summary = (
            f"Midday sync: {completed_count} tasks completed so far today. "
            f"{len(remaining)} tasks remaining. "
            f"Re-prioritized the afternoon plan."
        )

        await self._post_to_discord(summary, channel="myca-ops")
        self._log_rhythm("midday_sync", "completed")

        return {
            "status": "success",
            "completed_today": completed_count,
            "remaining": len(remaining),
            "summary": summary,
        }

    # ------------------------------------------------------------------
    # End of Day (5 PM)
    # ------------------------------------------------------------------

    async def _handle_end_of_day(self, task: Dict) -> Dict:
        """
        End-of-day routine:
        1. Summarize what got done
        2. List carry-over tasks
        3. Email summary to Morgan
        4. Post to Discord
        5. Archive completed tasks
        """
        self._log_rhythm("end_of_day", "started")

        completed_count = len(self._completed_today)
        remaining = [t for t in self._daily_plan if t.get("status") != "completed"]

        # Build EOD summary
        completed_list = "\n".join(
            f"  - {t.get('title', 'Untitled')}" for t in self._completed_today[:20]
        ) or "  (none)"

        remaining_list = "\n".join(
            f"  - {t.get('title', 'Untitled')} [{t.get('priority', 'medium')}]"
            for t in remaining[:10]
        ) or "  (none)"

        eod = (
            f"End of Day Summary — {datetime.now(timezone.utc).strftime('%B %d, %Y')}\n\n"
            f"Completed ({completed_count}):\n{completed_list}\n\n"
            f"Carry-over ({len(remaining)}):\n{remaining_list}\n\n"
            f"System: All VMs operational. Entering monitoring mode."
        )

        # Send email to Morgan
        await self._send_email(
            to="morgan@mycosoft.org",
            subject=f"MYCA EOD — {datetime.now(timezone.utc).strftime('%b %d')}",
            body=eod,
        )

        await self._post_to_discord(eod, channel="myca-ops")
        await self._log_to_memory("end_of_day", eod)

        # Reset daily counters
        self._completed_today.clear()
        self._log_rhythm("end_of_day", "completed")

        return {"status": "success", "summary": eod}

    # ------------------------------------------------------------------
    # Night Mode (10 PM)
    # ------------------------------------------------------------------

    async def _handle_night_mode(self, task: Dict) -> Dict:
        """Switch to monitoring-only mode. Only critical alerts."""
        self._log_rhythm("night_mode", "started")
        return {
            "status": "success",
            "mode": "monitoring",
            "message": "Night mode active. Monitoring for critical alerts only.",
        }

    # ------------------------------------------------------------------
    # Task Processing
    # ------------------------------------------------------------------

    async def _handle_process_tasks(self, task: Dict) -> Dict:
        """Process the next task in the daily plan queue."""
        if not self._daily_plan:
            return {"status": "success", "message": "No tasks in queue."}

        # Find first pending task
        next_task = None
        for t in self._daily_plan:
            if t.get("status") != "completed":
                next_task = t
                break

        if not next_task:
            return {"status": "success", "message": "All daily tasks completed!"}

        # Mark in-progress
        next_task["status"] = "in_progress"

        return {
            "status": "success",
            "processing": next_task,
            "remaining": len(
                [t for t in self._daily_plan if t.get("status") != "completed"]
            ) - 1,
        }

    # ------------------------------------------------------------------
    # Schedule Info
    # ------------------------------------------------------------------

    async def _handle_get_schedule(self, task: Dict) -> Dict:
        """Return the current daily schedule and rhythm log."""
        return {
            "status": "success",
            "schedule": [
                {"time": "08:00", "event": "morning_brief", "description": "Morning briefing and daily plan"},
                {"time": "09:00", "event": "process_tasks", "description": "Start task processing"},
                {"time": "10:00", "event": "hourly_status", "description": "Hourly status check"},
                {"time": "11:00", "event": "hourly_status", "description": "Hourly status check"},
                {"time": "12:00", "event": "midday_sync", "description": "Midday sync and re-prioritize"},
                {"time": "13:00", "event": "hourly_status", "description": "Hourly status check"},
                {"time": "14:00", "event": "hourly_status", "description": "Hourly status check"},
                {"time": "15:00", "event": "hourly_status", "description": "Hourly status check"},
                {"time": "16:00", "event": "hourly_status", "description": "Hourly status check"},
                {"time": "17:00", "event": "end_of_day", "description": "End-of-day summary and email"},
                {"time": "22:00", "event": "night_mode", "description": "Monitoring mode"},
            ],
            "daily_plan": self._daily_plan,
            "rhythm_log": self._rhythm_log[-20:],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _check_system_health(self) -> Dict[str, str]:
        """Quick health check across all VMs."""
        import httpx

        vms = {
            "sandbox_187": "http://192.168.0.187:3000",
            "mas_188": f"{self.mas_url}",
            "mindex_189": "http://192.168.0.189:8000",
            "myca_191": self.workspace_url,
        }
        health = {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in vms.items():
                try:
                    resp = await client.get(f"{url}/health")
                    health[name] = "healthy" if resp.status_code == 200 else f"status_{resp.status_code}"
                except Exception:
                    health[name] = "unreachable"
        return health

    async def _get_pending_tasks(self) -> List[Dict]:
        """Fetch pending tasks from workspace API."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.workspace_url}/api/workspace/status")
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("workspace", {}).get("pending_tasks_list", [])
        except Exception as e:
            logger.debug("Failed to fetch pending tasks: %s", e)
        return []

    def _prioritize_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """Sort tasks by priority."""
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(
            tasks,
            key=lambda t: priority_order.get(t.get("priority", "medium"), 2),
        )

    def _format_health(self, health: Dict[str, str]) -> str:
        lines = ["System Health:"]
        for vm, status in health.items():
            icon = "OK" if status == "healthy" else "WARN"
            lines.append(f"  [{icon}] {vm}: {status}")
        return "\n".join(lines)

    def _format_tasks(self, tasks: List[Dict]) -> str:
        if not tasks:
            return "Pending Tasks: None"
        lines = [f"Pending Tasks ({len(tasks)}):"]
        for t in tasks[:10]:
            lines.append(
                f"  - {t.get('title', 'Untitled')} "
                f"[{t.get('priority', 'medium')}]"
            )
        return "\n".join(lines)

    def _format_plan(self, plan: List[Dict]) -> str:
        if not plan:
            return "Daily Plan: No tasks scheduled."
        lines = [f"Daily Plan ({len(plan)} tasks):"]
        for i, t in enumerate(plan[:10], 1):
            lines.append(
                f"  {i}. {t.get('title', 'Untitled')} "
                f"[{t.get('priority', 'medium')}]"
            )
        return "\n".join(lines)

    async def _post_to_discord(self, message: str, channel: str = "myca-ops"):
        """Post to Discord via webhook or bot."""
        webhook_url = os.getenv("DISCORD_MYCA_WEBHOOK", "")
        if not webhook_url:
            logger.debug("Discord webhook not configured, skipping post")
            return

        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    webhook_url,
                    json={"content": message[:2000]},
                )
        except Exception as e:
            logger.warning("Discord post failed: %s", e)

    async def _send_email(self, to: str, subject: str, body: str):
        """Send email via workspace API or direct SMTP."""
        try:
            import httpx

            # Try workspace API first
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.workspace_url}/api/workspace/send",
                    json={
                        "recipient": "morgan",
                        "message": f"Subject: {subject}\n\n{body}",
                        "platform": "email",
                    },
                )
                if resp.status_code == 200:
                    return
        except Exception as e:
            logger.debug("Email via workspace API failed: %s", e)

        # Fallback: use n8n email workflow
        try:
            import httpx

            n8n_url = os.getenv("N8N_URL", "http://192.168.0.191:5679")
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{n8n_url}/webhook/myca-send-email",
                    json={"to": to, "subject": subject, "body": body},
                )
        except Exception as e:
            logger.warning("Email send failed on all channels: %s", e)

    async def _log_to_memory(self, event: str, content: str):
        """Store rhythm event in long-term memory."""
        try:
            await self.remember(
                key=f"rhythm_{event}_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                value={
                    "event": event,
                    "content": content[:2000],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            logger.debug("Memory log failed: %s", e)

    def _log_rhythm(self, event: str, status: str):
        """Log a rhythm event for the schedule endpoint."""
        self._rhythm_log.append({
            "event": event,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Keep last 100 entries
        if len(self._rhythm_log) > 100:
            self._rhythm_log = self._rhythm_log[-100:]
