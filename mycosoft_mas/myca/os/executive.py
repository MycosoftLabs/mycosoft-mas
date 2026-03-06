"""
MYCA Executive System — COO / Co-CEO / Co-CTO decision engine.

MYCA serves as Morgan's number 2 across all executive functions:
- COO: Operations, daily execution, resource allocation, staff coordination
- Co-CEO: Strategic decisions (with Morgan), company direction, partnerships
- Co-CTO: Technical architecture, system design, infrastructure, R&D

Decision hierarchy:
1. Autonomous decisions — MYCA makes these alone (operations, routine, monitoring)
2. Inform decisions — MYCA decides but tells Morgan (moderate impact)
3. Consult decisions — MYCA proposes, Morgan approves (high impact)
4. Escalate decisions — Morgan must decide (existential, financial, external)

Date: 2026-03-04
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from dataclasses import dataclass, field

from mycosoft_mas.myca.os.staff_registry import load_staff_directory

logger = logging.getLogger("myca.os.executive")


class DecisionLevel(str, Enum):
    AUTONOMOUS = "autonomous"    # MYCA decides alone
    INFORM = "inform"            # MYCA decides, tells Morgan
    CONSULT = "consult"          # MYCA proposes, Morgan approves
    ESCALATE = "escalate"        # Morgan must decide


class TaskPriority(str, Enum):
    CRITICAL = "critical"   # Do immediately
    HIGH = "high"           # Do today
    MEDIUM = "medium"       # Do this week
    LOW = "low"             # Do when time allows
    BACKLOG = "backlog"     # Future consideration


@dataclass
class ExecutiveTask:
    """A task in MYCA's executive queue."""
    title: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    task_type: str = "general"  # coding, research, communication, deployment, decision, analysis
    source: str = "self"        # morgan, asana, discord, self, system
    assigned_to: Optional[str] = None  # morgan, garret, rj, beto — from org_roles.yaml
    assigned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    due: Optional[datetime] = None
    status: str = "pending"     # pending, in_progress, completed, blocked, cancelled
    result: Optional[dict] = None
    db_id: Optional[int] = None  # myca_task_queue.id for persistence


# Decision classification rules
DECISION_RULES = {
    # Autonomous — MYCA handles alone
    "system_health": DecisionLevel.AUTONOMOUS,
    "monitoring": DecisionLevel.AUTONOMOUS,
    "routine_task": DecisionLevel.AUTONOMOUS,
    "code_review": DecisionLevel.AUTONOMOUS,
    "documentation": DecisionLevel.AUTONOMOUS,
    "research": DecisionLevel.AUTONOMOUS,
    "test_fix": DecisionLevel.AUTONOMOUS,
    "message_routing": DecisionLevel.AUTONOMOUS,

    # Inform — MYCA decides, notifies Morgan
    "bug_fix": DecisionLevel.INFORM,
    "small_feature": DecisionLevel.INFORM,
    "agent_update": DecisionLevel.INFORM,
    "workflow_change": DecisionLevel.INFORM,
    "dependency_update": DecisionLevel.INFORM,
    "performance_optimization": DecisionLevel.INFORM,

    # Consult — MYCA proposes, Morgan approves
    "architecture_change": DecisionLevel.CONSULT,
    "new_integration": DecisionLevel.CONSULT,
    "infrastructure_change": DecisionLevel.CONSULT,
    "security_change": DecisionLevel.CONSULT,
    "deployment_production": DecisionLevel.CONSULT,
    "new_agent": DecisionLevel.CONSULT,
    "api_change": DecisionLevel.CONSULT,

    # Escalate — Morgan must decide
    "financial": DecisionLevel.ESCALATE,
    "external_communication": DecisionLevel.ESCALATE,
    "partnership": DecisionLevel.ESCALATE,
    "hiring": DecisionLevel.ESCALATE,
    "legal": DecisionLevel.ESCALATE,
    "data_deletion": DecisionLevel.ESCALATE,
    "security_incident": DecisionLevel.ESCALATE,
}


class ExecutiveSystem:
    """MYCA's executive decision-making system."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._task_queue: list[ExecutiveTask] = []
        self._decisions_log: list[dict] = []
        self._current_priorities: list[str] = []
        self._daily_plan: Optional[dict] = None
        self._llm_brain: Optional["LLMBrain"] = None
        self._staff_directory = load_staff_directory()

    @property
    def llm_brain(self) -> "LLMBrain":
        if self._llm_brain is None:
            from mycosoft_mas.myca.os.llm_brain import LLMBrain
            self._llm_brain = LLMBrain(os_ref=self._os)
        return self._llm_brain

    async def initialize(self):
        """Load pending tasks from DB if available."""
        logger.info("ExecutiveSystem initialized")
        logger.info("Roles: COO, Co-CEO, Co-CTO")
        try:
            bridge = getattr(self._os, "mindex_bridge", None)
            if bridge and getattr(bridge, "_pg_pool", None) and bridge._pg_pool:
                async with bridge._pg_pool.acquire() as conn:
                    rows = await conn.fetch(
                        """SELECT id, title, description, priority, task_type, source, status, assigned_to
                           FROM myca_task_queue WHERE status IN ('pending', 'in_progress')
                           ORDER BY assigned_at"""
                    )
                    for row in rows:
                        self._task_queue.append(ExecutiveTask(
                            title=row["title"],
                            description=row.get("description") or "",
                            priority=TaskPriority(row.get("priority", "medium")),
                            task_type=row.get("task_type", "general"),
                            source=row.get("source", "self"),
                            status=row.get("status", "pending"),
                            assigned_to=row.get("assigned_to"),
                            db_id=row["id"],
                        ))
                    if rows:
                        logger.info("Loaded %d tasks from DB", len(rows))
        except Exception as e:
            logger.warning("Could not load tasks from DB: %s", e)

    async def cleanup(self):
        pass

    # ── Task Queue ───────────────────────────────────────────────

    async def get_next_task(self) -> Optional[dict]:
        """Get the next task to execute, sorted by priority. Recalls task-related context from memory."""
        pending = [t for t in self._task_queue if t.status == "pending"]
        if not pending:
            return None

        # Sort: critical > high > medium > low > backlog
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
            TaskPriority.BACKLOG: 4,
        }
        pending.sort(key=lambda t: priority_order.get(t.priority, 5))

        task = pending[0]
        task.status = "in_progress"
        asyncio.create_task(self._persist_task_status(task, "in_progress"))

        # Recall task-related context from memory (Phase 0)
        mindex = getattr(self._os, "mindex_bridge", None)
        if mindex and hasattr(mindex, "recall"):
            try:
                ctx = await mindex.recall(f"working:task:{task.title[:50]}")
                if ctx:
                    task.description = f"{task.description}\n[Context from memory]: {ctx[:500]}"
            except Exception:
                pass

        return {
            "title": task.title,
            "description": task.description,
            "priority": task.priority.value,
            "type": task.task_type,
            "source": task.source,
            "_task_obj": task,  # for core to call mark_task_completed
        }

    def add_task(self, title: str, description: str, priority: str = "medium",
                 task_type: str = "general", source: str = "self",
                 assigned_to: Optional[str] = None) -> ExecutiveTask:
        """Add a task to the queue. assigned_to defaults to role from task_type (org_roles)."""
        if assigned_to is None:
            assigned_to = self._suggest_role_for_task_type(task_type)
        task = ExecutiveTask(
            title=title,
            description=description,
            priority=TaskPriority(priority),
            task_type=task_type,
            source=source,
            assigned_to=assigned_to,
        )
        self._task_queue.append(task)
        asyncio.create_task(self._persist_task_add(task))
        logger.info(f"Task added [{priority}]: {title}")
        return task

    def _suggest_role_for_task_type(self, task_type: str) -> str:
        """Suggest assigned_to role from task_type using org_roles.yaml task_type_to_role."""
        try:
            from pathlib import Path
            import yaml
            roles_path = Path(__file__).resolve().parents[4] / "config" / "org_roles.yaml"
            if roles_path.exists():
                cfg = yaml.safe_load(roles_path.read_text())
                mapping = cfg.get("task_type_to_role", {})
                return mapping.get(task_type, "morgan")
        except Exception as e:
            logger.debug("org_roles load failed, defaulting to morgan: %s", e)
        return "morgan"

    async def _persist_task_add(self, task: ExecutiveTask):
        """Insert task into myca_task_queue."""
        try:
            bridge = getattr(self._os, "mindex_bridge", None)
            if bridge and getattr(bridge, "_pg_pool", None) and bridge._pg_pool:
                async with bridge._pg_pool.acquire() as conn:
                    task.db_id = await conn.fetchval(
                        """INSERT INTO myca_task_queue (title, description, priority, task_type, source, status, assigned_to)
                           VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id""",
                        task.title, task.description, task.priority.value, task.task_type, task.source, task.status,
                        task.assigned_to,
                    )
        except Exception as e:
            logger.warning("Task DB insert failed: %s", e)

    async def _persist_task_status(self, task: ExecutiveTask, status: str, result: dict = None):
        """Update task status in DB."""
        if not task.db_id:
            return
        try:
            bridge = getattr(self._os, "mindex_bridge", None)
            if bridge and getattr(bridge, "_pg_pool", None) and bridge._pg_pool:
                import json
                async with bridge._pg_pool.acquire() as conn:
                    now = datetime.now(timezone.utc)
                    if status == "in_progress":
                        await conn.execute(
                            "UPDATE myca_task_queue SET status = $1, started_at = $2 WHERE id = $3",
                            status, now, task.db_id,
                        )
                    elif status in ("completed", "blocked", "cancelled"):
                        await conn.execute(
                            """UPDATE myca_task_queue SET status = $1, completed_at = $2, result = $3
                               WHERE id = $4""",
                            status, now, json.dumps(result or {}) if result else None, task.db_id,
                        )
        except Exception as e:
            logger.warning("Task DB update failed: %s", e)

    async def _persist_decision(self, decision: dict):
        """Insert decision into myca_decisions."""
        try:
            bridge = getattr(self._os, "mindex_bridge", None)
            if bridge and getattr(bridge, "_pg_pool", None) and bridge._pg_pool:
                async with bridge._pg_pool.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO myca_decisions (decision_type, decision_level, description, action_taken, rationale)
                           VALUES ($1, $2, $3, $4, $5)""",
                        decision.get("type", ""),
                        decision.get("level", ""),
                        decision.get("description", ""),
                        decision.get("action", ""),
                        decision.get("rationale", ""),
                    )
        except Exception as e:
            logger.warning("Decision DB insert failed: %s", e)

    def mark_task_completed(self, task_dict: dict, result: dict):
        """Mark the task returned by get_next_task as completed."""
        task = task_dict.get("_task_obj")
        if task:
            task.status = "completed"
            task.result = result
            asyncio.create_task(self._persist_task_status(task, "completed", result))

    def mark_task_failed(self, task_dict: dict, error: str):
        """Mark the task as failed."""
        task = task_dict.get("_task_obj")
        if task:
            task.status = "blocked"
            task.result = {"error": error}
            asyncio.create_task(self._persist_task_status(task, "blocked", {"error": error}))

    # ── Morgan Interaction ───────────────────────────────────────

    async def handle_morgan_directive(self, msg: dict) -> str:
        """Handle a direct directive from Morgan."""
        content = msg.get("content", "")

        # Parse Morgan's message for actionable directives
        if any(kw in content.lower() for kw in ["do", "build", "fix", "create", "deploy", "update"]):
            # Action directive — create task (Morgan's directives go to Morgan)
            task = self.add_task(
                title=content[:100],
                description=content,
                priority="high",
                task_type=self._classify_task_type(content),
                source="morgan",
                assigned_to="morgan",
            )
            return (
                f"Got it. I've added this to my queue as high priority: '{task.title}'. "
                f"I'll get started on it now."
            )

        elif any(kw in content.lower() for kw in ["status", "report", "how", "what's"]):
            # Status request
            status = self._os.status()
            return (
                f"Current status:\n"
                f"- State: {status['state']}\n"
                f"- Tasks completed today: {status['tasks_completed_today']}\n"
                f"- Messages processed: {status['messages_processed_today']}\n"
                f"- Current task: {status['current_task'] or 'None'}\n"
                f"- Queue depth: {len([t for t in self._task_queue if t.status == 'pending'])}"
            )

        elif any(kw in content.lower() for kw in ["priority", "focus", "important"]):
            # Priority shift
            self._current_priorities = [content]
            return f"Understood. Shifting focus to: {content}"

        else:
            # General conversation — respond as MYCA
            return await self._generate_executive_response(content)

    async def classify_and_route(self, msg: dict) -> dict:
        """Classify an incoming message and determine routing."""
        content = msg.get("content", "").lower()
        sender = msg.get("sender", "")
        person_id = msg.get("person_id")
        staff = self._staff_directory.get(person_id or "", {})
        sender_role = staff.get("role", "staff") if staff else "staff"

        # Simple classification — enhance with LLM later
        if any(kw in content for kw in ["deploy", "restart", "server", "docker"]):
            return {"action": "delegate_to_agent", "agent_id": "deployment_agent", "task": msg}
        elif any(kw in content for kw in ["money", "budget", "invoice", "payment"]):
            return {"action": "escalate_to_morgan"}
        else:
            response = await self.llm_brain.respond(
                msg.get("content", ""),
                context={
                    "sender": staff.get("name", sender),
                    "source": msg.get("source", "unknown"),
                    "status": (
                        f"Role: {sender_role}; "
                        f"Pending tasks: {len([t for t in self._task_queue if t.status == 'pending'])}"
                    ),
                    "person_id": person_id,
                    "role": sender_role,
                },
            )
            return {"action": "respond_directly", "response": response}

    # ── Decision Making ──────────────────────────────────────────

    async def make_decision(self, task: dict) -> dict:
        """Make an executive decision based on type and impact."""
        decision_type = task.get("decision_type", "routine_task")
        level = DECISION_RULES.get(decision_type, DecisionLevel.CONSULT)

        decision = {
            "type": decision_type,
            "level": level.value,
            "description": task.get("description", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if level == DecisionLevel.AUTONOMOUS:
            decision["action"] = "approved"
            decision["rationale"] = "Within autonomous authority"
        elif level == DecisionLevel.INFORM:
            decision["action"] = "approved"
            decision["rationale"] = "Within authority — Morgan will be informed"
            # Notify Morgan asynchronously
            asyncio.create_task(self._os.comms.send_to_morgan(
                f"FYI: I've decided to {task.get('description', '')}",
                channel="discord",
            ))
        elif level == DecisionLevel.CONSULT:
            decision["action"] = "pending_approval"
            decision["rationale"] = "Requires Morgan's approval"
            await self._os.comms.send_to_morgan(
                f"I'd like to {task.get('description', '')}. Approve? (yes/no)",
                channel="discord",
            )
        elif level == DecisionLevel.ESCALATE:
            decision["action"] = "escalated"
            decision["rationale"] = "Morgan must decide"
            await self._os.comms.send_to_morgan(
                f"DECISION NEEDED: {task.get('description', '')}",
                channel="signal",
                urgency="critical",
            )

        self._decisions_log.append(decision)
        asyncio.create_task(self._persist_decision(decision))
        return {"status": "completed", "decision": decision}

    # ── Intention & Reflection ───────────────────────────────────

    async def review_intentions(self) -> dict:
        """Review and potentially reprioritize goals and tasks."""
        pending = [t for t in self._task_queue if t.status == "pending"]
        in_progress = [t for t in self._task_queue if t.status == "in_progress"]

        # Check if current work aligns with priorities
        if self._current_priorities and in_progress:
            current = in_progress[0]
            if not any(p.lower() in current.title.lower() for p in self._current_priorities):
                return {
                    "reprioritized": True,
                    "reason": f"Current task '{current.title}' doesn't align with priority: {self._current_priorities[0]}",
                }

        return {"reprioritized": False, "pending_count": len(pending)}

    async def reflect(self) -> dict:
        """Reflect on recent outcomes and extract learnings."""
        completed = [t for t in self._task_queue if t.status == "completed"]
        failed = [t for t in self._task_queue if t.status == "failed"]

        learnings = []
        if failed:
            for t in failed[-5:]:  # Last 5 failures
                learnings.append(f"Task '{t.title}' failed — investigate root cause")

        return {
            "learnings": learnings,
            "completed_count": len(completed),
            "failed_count": len(failed),
            "reflection_time": datetime.now(timezone.utc).isoformat(),
        }

    # ── Daily Rhythm Actions ─────────────────────────────────────

    async def trigger_daily_action(self, action: str):
        """Execute a daily rhythm action."""
        if action == "morning_briefing":
            await self._morning_briefing()
        elif action == "midday_sync":
            await self._midday_sync()
        elif action == "end_of_day":
            await self._end_of_day()
        elif action == "night_mode":
            await self._night_mode()

    async def _morning_briefing(self):
        """8 AM: Morning briefing to Morgan."""
        status = self._os.status()
        pending = len([t for t in self._task_queue if t.status == "pending"])

        briefing = (
            f"Good morning Morgan. Here's your briefing:\n"
            f"- System uptime: {int(status['uptime_seconds'] / 3600)}h\n"
            f"- Pending tasks: {pending}\n"
            f"- Errors overnight: {status['errors_today']}\n"
            f"- Ready to work. What should I focus on today?"
        )
        await self._os.comms.send_to_morgan(briefing, channel="discord")

    async def _midday_sync(self):
        """12 PM: Midday sync."""
        status = self._os.status()
        await self._os.comms.send_to_morgan(
            f"Midday sync: {status['tasks_completed_today']} tasks done, "
            f"{len([t for t in self._task_queue if t.status == 'pending'])} remaining.",
            channel="discord",
        )

    async def _end_of_day(self):
        """5 PM: End of day summary."""
        status = self._os.status()
        await self._os.comms.send_to_morgan(
            f"End of day report:\n"
            f"- Tasks completed: {status['tasks_completed_today']}\n"
            f"- Messages processed: {status['messages_processed_today']}\n"
            f"- Decisions made: {status['decisions_made_today']}\n"
            f"- Switching to monitoring mode at 10 PM.",
            channel="discord",
        )

    async def _night_mode(self):
        """10 PM: Switch to monitoring-only mode."""
        logger.info("Entering night mode — monitoring only")
        # Reduce activity, only critical alerts

    # ── Helpers ──────────────────────────────────────────────────

    def _classify_task_type(self, content: str) -> str:
        """Classify a task type from natural language."""
        content = content.lower()
        if any(kw in content for kw in ["code", "fix", "build", "implement", "refactor"]):
            return "coding"
        elif any(kw in content for kw in ["research", "find", "look up", "investigate"]):
            return "research"
        elif any(kw in content for kw in ["github", "pull request", "pr ", "issue", "repo"]):
            return "github"
        elif any(kw in content for kw in ["asana", "workspace", "project task", "story comment"]):
            return "asana"
        elif any(kw in content for kw in ["natureos", "ecosystem", "matlab", "digital twin"]):
            return "natureos"
        elif any(kw in content for kw in ["search", "lookup", "query knowledge", "what do we know"]):
            return "search"
        elif any(kw in content for kw in ["deploy", "restart", "update server"]):
            return "deployment"
        elif any(kw in content for kw in ["email", "message", "notify", "tell"]):
            return "communication"
        elif any(kw in content for kw in ["decide", "approve", "choose"]):
            return "decision"
        elif any(kw in content for kw in ["analyze", "review", "audit"]):
            return "analysis"
        elif any(kw in content for kw in ["workflow", "automate", "n8n"]):
            return "workflow"
        return "general"

    async def _generate_executive_response(self, content: str) -> str:
        """Generate a response as an executive using Claude (SOUL + MEMORY context)."""
        status = self._os.status() if hasattr(self._os, "status") else {}
        context = {
            "sender": "Morgan",
            "source": "direct",
            "status": (
                f"State: {status.get('state', 'unknown')}, "
                f"Tasks today: {status.get('tasks_completed_today', 0)}, "
                f"Queue: {len([t for t in self._task_queue if t.status == 'pending'])} pending"
            ),
        }
        return await self.llm_brain.respond(content, context=context)
