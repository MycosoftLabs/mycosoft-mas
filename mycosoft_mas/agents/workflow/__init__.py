"""
Workflow agents - n8n, trigger, scheduler, notification.
Phase 1 AGENT_CATALOG implementation.
"""

from mycosoft_mas.agents.workflow.n8n_workflow_agent import N8NWorkflowAgent
from mycosoft_mas.agents.workflow.trigger_agent import TriggerAgent
from mycosoft_mas.agents.workflow.scheduler_agent import SchedulerAgent
from mycosoft_mas.agents.workflow.notification_agent import NotificationAgent

__all__ = [
    "N8NWorkflowAgent",
    "TriggerAgent",
    "SchedulerAgent",
    "NotificationAgent",
]
