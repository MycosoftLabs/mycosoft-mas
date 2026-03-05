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
    assigned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    due: Optional[datetime] = None
    status: str = "pending"     # pending, in_progress, completed, blocked, cancelled
    result: Optional[dict] = None


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

    @property
    def llm_brain(self) -> "LLMBrain":
        if self._llm_brain is None:
            from mycosoft_mas.myca.os.llm_brain import LLMBrain
            self._llm_brain = LLMBrain()
        return self._llm_brain

    async def initialize(self):
        logger.info("ExecutiveSystem initialized")
        logger.info("Roles: COO, Co-CEO, Co-CTO")

    async def cleanup(self):
        pass

    # ── Task Queue ───────────────────────────────────────────────

    async def get_next_task(self) -> Optional[dict]:
        """Get the next task to execute, sorted by priority."""
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

        return {
            "title": task.title,
            "description": task.description,
            "priority": task.priority.value,
            "type": task.task_type,
            "source": task.source,
        }

    def add_task(self, title: str, description: str, priority: str = "medium",
                 task_type: str = "general", source: str = "self") -> ExecutiveTask:
        """Add a task to the queue."""
        task = ExecutiveTask(
            title=title,
            description=description,
            priority=TaskPriority(priority),
            task_type=task_type,
            source=source,
        )
        self._task_queue.append(task)
        logger.info(f"Task added [{priority}]: {title}")
        return task

    # ── Morgan Interaction ───────────────────────────────────────

    async def handle_morgan_directive(self, msg: dict) -> str:
        """Handle a direct directive from Morgan."""
        content = msg.get("content", "")

        # Parse Morgan's message for actionable directives
        if any(kw in content.lower() for kw in ["do", "build", "fix", "create", "deploy", "update"]):
            # Action directive — create task
            task = self.add_task(
                title=content[:100],
                description=content,
                priority="high",
                task_type=self._classify_task_type(content),
                source="morgan",
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

        # Simple classification — enhance with LLM later
        if any(kw in content for kw in ["deploy", "restart", "server", "docker"]):
            return {"action": "delegate_to_agent", "agent_id": "deployment_agent", "task": msg}
        elif any(kw in content for kw in ["money", "budget", "invoice", "payment"]):
            return {"action": "escalate_to_morgan"}
        elif any(kw in content for kw in ["help", "question", "how to"]):
            return {"action": "respond_directly", "response": f"I'll look into that for you, {sender}."}
        else:
            return {"action": "respond_directly", "response": f"Thanks {sender}, I've noted your message."}

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
