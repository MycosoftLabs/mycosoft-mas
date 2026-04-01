"""myca agent — Manage MAS agents.

Maps to:
  MCP:  agent_list, agent_invoke, agent_status (orchestrator MCP)
  API:  /api/registry/agents, /api/orchestrator/task
"""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer

from mycosoft_mas.cli import _client as client
from mycosoft_mas.cli import _output as output

agent_app = typer.Typer(
    help="Manage MAS agents — list, invoke, check status.",
    no_args_is_help=True,
)


@agent_app.command("list")
def agent_list(
    ctx: typer.Context,
    category: str = typer.Option(
        "all",
        "--category",
        "-c",
        help="Filter by category (corporate, infrastructure, scientific, device, data, "
        "integration, financial, security, mycology, earth2, simulation, business, core, custom, all)",
    ),
    status: str = typer.Option(
        "all",
        "--status",
        "-s",
        help="Filter by status (active, idle, error, offline, all)",
    ),
    limit: int = typer.Option(50, "--limit", "-l", help="Max agents to return"),
) -> None:
    """List all registered MAS agents.

    Examples:
      myca agent list
      myca agent list --category corporate --status active
      myca agent list --output table --limit 10
      myca agent list --category scientific --output plain
    """
    state = ctx.obj
    params = {}
    if category != "all":
        params["category"] = category
    if status != "all":
        params["status"] = status
    if limit != 50:
        params["limit"] = limit

    result = client.get(f"{state.config.mas_url}/api/registry/agents", config=state.config, params=params)
    if not result.ok:
        output.print_error(result.error, hint="myca system health  # check if MAS is running")

    data = result.data
    # Apply client-side filters if API doesn't support them
    agents = data.get("agents", data if isinstance(data, list) else [data])
    if category != "all" and isinstance(agents, list):
        agents = [a for a in agents if a.get("category", "").lower() == category.lower()]
    if status != "all" and isinstance(agents, list):
        agents = [a for a in agents if a.get("status", "").lower() == status.lower()]
    agents = agents[:limit]

    out = {"count": len(agents), "agents": agents}
    output.print_result(
        out,
        state.output,
        keys=["agent_id", "name", "category", "status", "capabilities"],
        headers=["ID", "NAME", "CATEGORY", "STATUS", "CAPABILITIES"],
    )


@agent_app.command("invoke")
def agent_invoke(
    ctx: typer.Context,
    agent_id: str = typer.Argument(..., help="Agent ID to invoke (e.g., coding_agent)"),
    type: str = typer.Option(..., "--type", "-t", help="Task type (depends on agent capabilities)"),
    description: str = typer.Option(..., "--description", "-d", help="Human-readable task description"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Task priority (low, medium, high, critical)"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for result (max 30s)"),
    stdin: bool = typer.Option(False, "--stdin", help="Read task JSON from stdin"),
) -> None:
    """Invoke a MAS agent with a task.

    Examples:
      myca agent invoke coding_agent --type code_review --description "Review auth module"
      myca agent invoke research_agent --type research --description "Latest mycology papers" --wait
      myca agent invoke deploy_agent --type deploy --description "Deploy v2" --priority critical
      echo '{"type":"analyze","description":"Check logs"}' | myca agent invoke debug_agent --stdin
    """
    state = ctx.obj

    if stdin:
        task = client.read_stdin_json()
    else:
        task = {
            "type": type,
            "description": description,
            "priority": priority,
        }

    result = client.post(
        f"{state.config.mas_url}/api/orchestrator/task",
        config=state.config,
        json_body={"agent_id": agent_id, "task": task, "wait_for_result": wait},
    )
    if not result.ok:
        output.print_error(
            result.error,
            hint=f"myca agent status {agent_id}  # check if agent is available",
        )

    output.print_result(result.data, state.output)


@agent_app.command("status")
def agent_status(
    ctx: typer.Context,
    agent_id: str = typer.Argument(..., help="Agent ID to check"),
    metrics: bool = typer.Option(True, "--metrics/--no-metrics", help="Include performance metrics"),
    history: bool = typer.Option(False, "--history", help="Include recent task history"),
) -> None:
    """Get detailed status and metrics for an agent.

    Examples:
      myca agent status coding_agent
      myca agent status research_agent --history
      myca agent status orchestrator --no-metrics --output table
    """
    state = ctx.obj
    result = client.get(
        f"{state.config.mas_url}/api/registry/agents/{agent_id}",
        config=state.config,
    )
    if not result.ok:
        output.print_error(
            result.error,
            hint=f"myca agent list  # see available agents",
        )

    data = result.data

    if metrics:
        metrics_result = client.get(
            f"{state.config.mas_url}/api/registry/agents/{agent_id}/metrics",
            config=state.config,
        )
        if metrics_result.ok:
            data["metrics"] = metrics_result.data

    if history:
        history_result = client.get(
            f"{state.config.mas_url}/api/orchestrator/tasks",
            config=state.config,
            params={"agent_id": agent_id, "limit": 10},
        )
        if history_result.ok:
            data["recent_tasks"] = history_result.data.get("tasks", [])

    output.print_result(data, state.output)
