"""myca CLI — Agent-friendly command-line interface for the Mycosoft Multi-Agent System.

Three access layers to the same system:
  CLI:  myca agent list --category corporate --output json
  MCP:  agent_list tool via orchestrator MCP server
  API:  GET http://192.168.0.188:8001/api/registry/agents?category=corporate

Design principles (agent-friendly):
  - Non-interactive: every input is a flag, no prompts
  - Progressive discovery: --help at every level with examples
  - Structured output: JSON by default (--output json|table|plain)
  - Pipeable: accepts --stdin, returns machine-readable data
  - Fail fast: actionable errors with correct invocation hints
  - Idempotent: same command twice = same result
  - --dry-run: preview destructive actions
  - --yes: skip confirmations
"""

from __future__ import annotations

from typing import Optional

import typer

from mycosoft_mas.cli._client import APIConfig

# ── Main app ────────────────────────────────────────────────────────────
app = typer.Typer(
    name="myca",
    help="Agent-friendly CLI for the Mycosoft Multi-Agent System.",
    no_args_is_help=True,
    rich_markup_mode=None,  # Keep help text plain for agents
    add_completion=False,
)


# ── Global state ────────────────────────────────────────────────────────
class CLIState:
    """Global state passed through typer.Context.obj."""

    def __init__(self) -> None:
        self.config = APIConfig()
        self.output: str = "json"
        self.verbose: bool = False
        self.yes: bool = False


@app.callback()
def main(
    ctx: typer.Context,
    url: Optional[str] = typer.Option(
        None,
        "--url",
        help="MAS API base URL (default: $MAS_API_URL or http://192.168.0.188:8001)",
        envvar="MAS_API_URL",
    ),
    output: str = typer.Option(
        "json",
        "--output",
        "-o",
        help="Output format: json, table, plain",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmations"),
) -> None:
    """Mycosoft MAS CLI — manage agents, tasks, memory, and infrastructure.

    Global options apply to all subcommands.

    Examples:
      myca agent list
      myca --output table agent list --category corporate
      myca --url http://localhost:8001 system health
      myca --yes deploy mas --tag v1.2.3
    """
    state = CLIState()
    if url:
        state.config.mas_url = url
    state.output = output
    state.verbose = verbose
    state.yes = yes
    ctx.ensure_object(type(None))
    ctx.obj = state


@app.command()
def version() -> None:
    """Print myca CLI version.

    Examples:
      myca version
    """
    print("myca 1.0.0 (Mycosoft MAS CLI)")


# ── Register sub-apps ───────────────────────────────────────────────────
from mycosoft_mas.cli.agent import agent_app  # noqa: E402
from mycosoft_mas.cli.deploy import deploy_app  # noqa: E402
from mycosoft_mas.cli.memory import memory_app  # noqa: E402
from mycosoft_mas.cli.raas import raas_app  # noqa: E402
from mycosoft_mas.cli.registry import registry_app  # noqa: E402
from mycosoft_mas.cli.system import system_app  # noqa: E402
from mycosoft_mas.cli.task import task_app  # noqa: E402
from mycosoft_mas.cli.workflow import workflow_app  # noqa: E402

app.add_typer(agent_app, name="agent")
app.add_typer(task_app, name="task")
app.add_typer(system_app, name="system")
app.add_typer(memory_app, name="memory")
app.add_typer(raas_app, name="raas")
app.add_typer(workflow_app, name="workflow")
app.add_typer(registry_app, name="registry")
app.add_typer(deploy_app, name="deploy")
