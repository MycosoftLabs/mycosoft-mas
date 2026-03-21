"""
CFO MCP Server — MAS-hosted finance control plane for Meridian/Perplexity.

Exposes model-safe tools for:
- Discovering finance agents, services, workloads, tasks dynamically
- Inspecting workload/task queues and last reports
- Delegating tasks to finance agents
- Submitting CFO directives and receiving structured summaries

Backed by the finance discovery layer; newly added finance agents become visible
automatically without code changes.

Created: March 8, 2026
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from mycosoft_mas.finance import discovery

logger = logging.getLogger("CFOMCP")


@dataclass
class MCPToolDefinition:
    """Definition of an MCP tool."""

    name: str
    description: str
    parameters: Dict[str, Any]


class CFOMCPServer:
    """
    MCP Server for CFO/Finance control plane.

    Tools:
    - list_finance_agents: List all finance agents (dynamic discovery)
    - list_finance_services: List finance integration services
    - list_finance_workloads: List finance n8n workflows
    - list_finance_tasks: List recent CFO reports and tasks
    - delegate_finance_task: Delegate a task to a finance agent
    - submit_finance_report: Submit a finance report to C-Suite
    - get_finance_status: Aggregate finance status and visibility
    - get_finance_alerts: Get escalations and stale heartbeat alerts
    """

    def __init__(self):
        self._tools = self._define_tools()

    def _define_tools(self) -> List[MCPToolDefinition]:
        """Define MCP tool specifications."""
        return [
            MCPToolDefinition(
                name="list_finance_agents",
                description="List all finance agents from the MAS registry. Discovers dynamically; new agents appear automatically.",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
            MCPToolDefinition(
                name="list_finance_services",
                description="List finance-related integration services (Mercury, QuickBooks, Relay, etc.).",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
            MCPToolDefinition(
                name="list_finance_workloads",
                description="List finance-related n8n workflows (dynamic discovery by name/tags).",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
            MCPToolDefinition(
                name="list_finance_tasks",
                description="List recent CFO reports and tasks from C-Suite.",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
            MCPToolDefinition(
                name="delegate_finance_task",
                description="Delegate a task to a specific finance agent. The agent will process the task and return a result.",
                parameters={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID of the finance agent (e.g., financial, financial_operations)",
                        },
                        "task": {
                            "type": "object",
                            "description": "Task object with type and parameters",
                            "properties": {
                                "type": {"type": "string"},
                                "description": {"type": "string"},
                                "params": {"type": "object"},
                            },
                        },
                    },
                    "required": ["agent_id", "task"],
                },
            ),
            MCPToolDefinition(
                name="submit_finance_report",
                description="Submit a finance report to C-Suite (persists and routes to MYCA and Meridian).",
                parameters={
                    "type": "object",
                    "properties": {
                        "role": {"type": "string", "default": "CFO"},
                        "assistant_name": {"type": "string", "default": "Meridian"},
                        "report_type": {
                            "type": "string",
                            "description": "task_completion | executive_summary | operating_report",
                            "default": "operating_report",
                        },
                        "summary": {"type": "string"},
                        "details": {"type": "object"},
                        "task_id": {"type": "string"},
                        "escalated": {"type": "boolean", "default": False},
                    },
                    "required": ["summary"],
                },
            ),
            MCPToolDefinition(
                name="get_finance_status",
                description="Get aggregate finance status: agents, services, workloads, recent tasks, CFO assistant state.",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
            MCPToolDefinition(
                name="get_finance_alerts",
                description="Get finance-related alerts: escalations, stale heartbeats (>2 min).",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions in MCP format."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.parameters,
            }
            for tool in self._tools
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call."""
        handlers = {
            "list_finance_agents": self._handle_list_agents,
            "list_finance_services": self._handle_list_services,
            "list_finance_workloads": self._handle_list_workloads,
            "list_finance_tasks": self._handle_list_tasks,
            "delegate_finance_task": self._handle_delegate_task,
            "submit_finance_report": self._handle_submit_report,
            "get_finance_status": self._handle_get_status,
            "get_finance_alerts": self._handle_get_alerts,
        }

        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}

        try:
            return await handler(arguments)
        except Exception as e:
            logger.error("CFO MCP tool %s failed: %s", name, e)
            return {"error": str(e)}

    async def _handle_list_agents(self, args: Dict[str, Any]) -> Dict[str, Any]:
        agents = discovery.list_finance_agents()
        return {"success": True, "count": len(agents), "agents": agents}

    async def _handle_list_services(self, args: Dict[str, Any]) -> Dict[str, Any]:
        services = discovery.list_finance_services()
        return {"success": True, "count": len(services), "services": services}

    async def _handle_list_workloads(self, args: Dict[str, Any]) -> Dict[str, Any]:
        workloads = await discovery.list_finance_workloads()
        return {"success": True, "count": len(workloads), "workloads": workloads}

    async def _handle_list_tasks(self, args: Dict[str, Any]) -> Dict[str, Any]:
        tasks = await discovery.list_finance_tasks()
        return {"success": True, "count": len(tasks), "tasks": tasks}

    async def _handle_delegate_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        agent_id = args.get("agent_id")
        task = args.get("task")
        if not agent_id or not task:
            return {"error": "agent_id and task are required"}
        result = await discovery.delegate_finance_task(agent_id, task)
        return result

    async def _handle_submit_report(self, args: Dict[str, Any]) -> Dict[str, Any]:
        result = await discovery.submit_finance_report(
            role=args.get("role", "CFO"),
            assistant_name=args.get("assistant_name", "Meridian"),
            report_type=args.get("report_type", "operating_report"),
            summary=args.get("summary", ""),
            details=args.get("details"),
            task_id=args.get("task_id"),
            escalated=args.get("escalated", False),
        )
        return {"success": "error" not in result, **result}

    async def _handle_get_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        status = await discovery.get_finance_status()
        return {"success": True, **status}

    async def _handle_get_alerts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        alerts = await discovery.get_finance_alerts()
        return {"success": True, "count": len(alerts), "alerts": alerts}


# Singleton instance
_cfo_mcp_server: CFOMCPServer | None = None


def get_cfo_mcp_server() -> CFOMCPServer:
    """Get or create the singleton CFO MCP server instance."""
    global _cfo_mcp_server
    if _cfo_mcp_server is None:
        _cfo_mcp_server = CFOMCPServer()
    return _cfo_mcp_server
