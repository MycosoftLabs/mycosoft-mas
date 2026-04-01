"""myca task — Manage tasks and plans.

Maps to:
  MCP:  task_create, task_list, task_update, task_assign (task management MCP)
  API:  /tasks, /api/tasks
"""

from __future__ import annotations

from typing import Optional

import typer

from mycosoft_mas.cli import _client as client
from mycosoft_mas.cli import _output as output

task_app = typer.Typer(
    help="Manage tasks — create, list, update, assign to agents.",
    no_args_is_help=True,
)


@task_app.command("create")
def task_create(
    ctx: typer.Context,
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Task title"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Task description"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority (low, medium, high, critical)"),
    type: str = typer.Option("general", "--type", help="Task type"),
    assign: Optional[str] = typer.Option(None, "--assign", "-a", help="Assign to agent ID"),
    stdin: bool = typer.Option(False, "--stdin", help="Read task JSON from stdin"),
) -> None:
    """Create a new task.

    Examples:
      myca task create --title "Deploy website" --priority high
      myca task create --title "Review PRs" --description "Check all open PRs" --assign coding_agent
      myca task create --title "Research" --type research --priority critical
      echo '{"title":"Audit","priority":"high"}' | myca task create --stdin
    """
    state = ctx.obj

    if stdin:
        data = client.read_stdin_json()
    elif title:
        data = {
            "title": title,
            "description": description or title,
            "priority": priority,
            "type": type,
        }
        if assign:
            data["assigned_agent"] = assign
    else:
        output.print_error(
            "No task specified",
            hint="myca task create --title 'Deploy v2' --priority high",
        )

    result = client.post(
        f"{state.config.mas_url}/tasks",
        config=state.config,
        json_body=data,
    )
    if not result.ok:
        # Try gateway as fallback
        result = client.post(
            f"{state.config.gateway_url}/tasks",
            config=state.config,
            json_body=data,
        )
    if not result.ok:
        output.print_error(result.error, hint="myca system health  # check connectivity")

    output.print_result(result.data, state.output)


@task_app.command("list")
def task_list(
    ctx: typer.Context,
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (pending, active, completed, failed)"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="Filter by priority (low, medium, high, critical)"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by assigned agent ID"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max tasks to return"),
) -> None:
    """List tasks with optional filters.

    Examples:
      myca task list
      myca task list --status pending --priority high
      myca task list --agent coding_agent --output table
      myca task list --limit 5 --output plain
    """
    state = ctx.obj
    params: dict = {"limit": limit}
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority
    if agent:
        params["agent_id"] = agent

    result = client.get(f"{state.config.mas_url}/tasks", config=state.config, params=params)
    if not result.ok:
        result = client.get(f"{state.config.gateway_url}/tasks", config=state.config, params=params)
    if not result.ok:
        output.print_error(result.error, hint="myca system health")

    output.print_result(
        result.data,
        state.output,
        keys=["id", "title", "status", "priority", "assigned_agent"],
        headers=["ID", "TITLE", "STATUS", "PRIORITY", "AGENT"],
    )


@task_app.command("update")
def task_update(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID to update"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="New status"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="New priority"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    stdin: bool = typer.Option(False, "--stdin", help="Read update JSON from stdin"),
) -> None:
    """Update an existing task.

    Examples:
      myca task update task_123 --status completed
      myca task update task_456 --priority critical --description "Urgent fix needed"
      echo '{"status":"failed","reason":"timeout"}' | myca task update task_789 --stdin
    """
    state = ctx.obj

    if stdin:
        data = client.read_stdin_json()
    else:
        data = {}
        if status:
            data["status"] = status
        if priority:
            data["priority"] = priority
        if description:
            data["description"] = description
        if not data:
            output.print_error(
                "No fields to update",
                hint="myca task update <task-id> --status completed",
            )

    result = client.post(
        f"{state.config.mas_url}/tasks/{task_id}",
        config=state.config,
        json_body=data,
    )
    if not result.ok:
        output.print_error(result.error, hint=f"myca task list  # verify task ID")

    output.print_result(result.data, state.output)


@task_app.command("assign")
def task_assign(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID to assign"),
    agent: str = typer.Option(..., "--agent", "-a", help="Agent ID to assign to"),
) -> None:
    """Assign a task to a specific agent.

    Examples:
      myca task assign task_123 --agent coding_agent
      myca task assign task_456 --agent research_agent
    """
    state = ctx.obj
    result = client.post(
        f"{state.config.mas_url}/tasks/{task_id}/assign",
        config=state.config,
        json_body={"agent_id": agent},
    )
    if not result.ok:
        output.print_error(
            result.error,
            hint=f"myca agent list  # see available agents\n  myca task list  # verify task ID",
        )

    output.print_result(result.data, state.output)
