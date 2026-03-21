"""
Finance discovery and delegation layer for the CFO MCP connector.

Provides a canonical CFO-facing surface for:
- list_finance_agents, list_finance_services, list_finance_workloads, list_finance_tasks
- delegate_finance_task, submit_finance_report
- get_finance_status, get_finance_alerts

New finance agents/services/workflows are discovered dynamically from the registry
and n8n; no hardcoded lists required.

Created: March 8, 2026
"""

from mycosoft_mas.finance.discovery import (
    delegate_finance_task,
    get_finance_alerts,
    get_finance_status,
    list_finance_agents,
    list_finance_services,
    list_finance_tasks,
    list_finance_workloads,
    submit_finance_report,
)

__all__ = [
    "list_finance_agents",
    "list_finance_services",
    "list_finance_workloads",
    "list_finance_tasks",
    "delegate_finance_task",
    "submit_finance_report",
    "get_finance_status",
    "get_finance_alerts",
]
