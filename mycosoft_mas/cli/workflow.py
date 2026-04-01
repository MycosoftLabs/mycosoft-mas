"""myca workflow — n8n workflow management.

Maps to:
  MCP:  workflow_trigger (orchestrator MCP)
  API:  /api/n8n/*, n8n webhook endpoints
"""

from __future__ import annotations

from typing import Optional

import typer

from mycosoft_mas.cli import _client as client
from mycosoft_mas.cli import _output as output

workflow_app = typer.Typer(
    help="Manage and trigger n8n workflows.",
    no_args_is_help=True,
)


@workflow_app.command("trigger")
def workflow_trigger(
    ctx: typer.Context,
    workflow_id: Optional[str] = typer.Option(None, "--id", help="Workflow ID to trigger"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Workflow name to trigger (alternative to --id)"),
    data: Optional[str] = typer.Option(None, "--data", "-d", help="JSON data to pass to workflow"),
    stdin: bool = typer.Option(False, "--stdin", help="Read workflow data from stdin"),
) -> None:
    """Trigger an n8n workflow by ID or name.

    Examples:
      myca workflow trigger --id wf_abc123
      myca workflow trigger --name "daily-report"
      myca workflow trigger --id wf_abc123 --data '{"env":"staging"}'
      echo '{"key":"value"}' | myca workflow trigger --id wf_abc123 --stdin
    """
    state = ctx.obj

    if not workflow_id and not name:
        output.print_error(
            "Either --id or --name is required",
            hint="myca workflow trigger --id <workflow-id>\n  myca workflow list  # see available workflows",
        )

    import json as json_mod

    if stdin:
        payload = client.read_stdin_json()
    elif data:
        try:
            payload = json_mod.loads(data)
        except json_mod.JSONDecodeError as e:
            output.print_error(f"Invalid JSON in --data: {e}", hint='myca workflow trigger --id wf_123 --data \'{"key":"value"}\'')
    else:
        payload = {}

    n8n_url = "http://192.168.0.188:5678"
    identifier = workflow_id or name
    result = client.post(
        f"{n8n_url}/webhook/{identifier}",
        config=state.config,
        json_body=payload,
    )
    if not result.ok:
        output.print_error(
            result.error,
            hint=f"myca workflow list  # verify workflow ID/name",
        )

    output.print_result(
        {"workflow": identifier, "status": "triggered", "result": result.data},
        state.output,
    )


@workflow_app.command("list")
def workflow_list(
    ctx: typer.Context,
    active: Optional[bool] = typer.Option(None, "--active/--inactive", help="Filter by active status"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max workflows to return"),
) -> None:
    """List n8n workflows.

    Examples:
      myca workflow list
      myca workflow list --active --output table
      myca workflow list --limit 10
    """
    state = ctx.obj
    params: dict = {"limit": limit}
    if active is not None:
        params["active"] = active

    result = client.get(
        f"{state.config.mas_url}/api/n8n/workflows",
        config=state.config,
        params=params,
    )
    if not result.ok:
        output.print_error(result.error, hint="myca system services  # check n8n status")

    output.print_result(
        result.data,
        state.output,
        keys=["id", "name", "active", "updated_at"],
        headers=["ID", "NAME", "ACTIVE", "UPDATED"],
    )
