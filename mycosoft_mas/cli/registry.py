"""myca registry — Agent, API, and skill registration.

Maps to:
  MCP:  registry_add_agent, registry_add_api, registry_add_skill, registry_sync (registry MCP)
  API:  /api/registry/*
"""

from __future__ import annotations

from typing import Optional

import typer

from mycosoft_mas.cli import _client as client
from mycosoft_mas.cli import _output as output

registry_app = typer.Typer(
    help="Registry management — register agents, APIs, skills, and sync.",
    no_args_is_help=True,
)


@registry_app.command("add-agent")
def registry_add_agent(
    ctx: typer.Context,
    agent_id: str = typer.Option(..., "--id", help="Unique agent ID"),
    name: str = typer.Option(..., "--name", "-n", help="Agent display name"),
    category: str = typer.Option(..., "--category", "-c", help="Agent category"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Agent description"),
    capabilities: Optional[str] = typer.Option(None, "--capabilities", help="Comma-separated capabilities"),
    module_path: Optional[str] = typer.Option(None, "--module", help="Python module path"),
    class_name: Optional[str] = typer.Option(None, "--class", help="Agent class name"),
    stdin: bool = typer.Option(False, "--stdin", help="Read agent definition from stdin"),
) -> None:
    """Register a new agent in the MAS registry.

    Examples:
      myca registry add-agent --id weather_bot --name WeatherBot --category custom
      myca registry add-agent --id my_agent --name MyAgent --category integration \\
          --capabilities "search,analyze" --module mycosoft_mas.agents.my_agent --class MyAgent
      echo '{"agent_id":"x","name":"X","category":"custom"}' | myca registry add-agent --stdin
    """
    state = ctx.obj

    if stdin:
        data = client.read_stdin_json()
    else:
        data = {"agent_id": agent_id, "name": name, "category": category}
        if description:
            data["description"] = description
        if capabilities:
            data["capabilities"] = [c.strip() for c in capabilities.split(",")]
        if module_path:
            data["module_path"] = module_path
        if class_name:
            data["class_name"] = class_name

    result = client.post(
        f"{state.config.mas_url}/api/registry/agents",
        config=state.config,
        json_body=data,
    )
    if not result.ok:
        output.print_error(result.error, hint="myca agent list  # check existing agents")

    output.print_result(result.data, state.output)


@registry_app.command("add-api")
def registry_add_api(
    ctx: typer.Context,
    path: str = typer.Option(..., "--path", help="API endpoint path (e.g., /api/myservice/health)"),
    method: str = typer.Option("GET", "--method", "-m", help="HTTP method (GET, POST, PUT, DELETE)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Endpoint description"),
    router: Optional[str] = typer.Option(None, "--router", help="Router file path"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    stdin: bool = typer.Option(False, "--stdin", help="Read API definition from stdin"),
) -> None:
    """Register a new API endpoint.

    Examples:
      myca registry add-api --path /api/weather/forecast --method GET --description "Get forecast"
      myca registry add-api --path /api/deploy --method POST --tags "deploy,infrastructure"
    """
    state = ctx.obj

    if stdin:
        data = client.read_stdin_json()
    else:
        data = {"path": path, "method": method.upper()}
        if description:
            data["description"] = description
        if router:
            data["router"] = router
        if tags:
            data["tags"] = [t.strip() for t in tags.split(",")]

    result = client.post(
        f"{state.config.mas_url}/api/registry/apis",
        config=state.config,
        json_body=data,
    )
    if not result.ok:
        output.print_error(result.error, hint="myca system health")

    output.print_result(result.data, state.output)


@registry_app.command("add-skill")
def registry_add_skill(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Skill name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Skill description"),
    agent_id: Optional[str] = typer.Option(None, "--agent", "-a", help="Owning agent ID"),
    stdin: bool = typer.Option(False, "--stdin", help="Read skill definition from stdin"),
) -> None:
    """Register a new skill.

    Examples:
      myca registry add-skill --name "code_review" --description "Review code PRs" --agent coding_agent
      myca registry add-skill --name "species_id" --agent mycology_agent
    """
    state = ctx.obj

    if stdin:
        data = client.read_stdin_json()
    else:
        data = {"name": name}
        if description:
            data["description"] = description
        if agent_id:
            data["agent_id"] = agent_id

    result = client.post(
        f"{state.config.mas_url}/api/registry/skills",
        config=state.config,
        json_body=data,
    )
    if not result.ok:
        output.print_error(result.error, hint="myca agent list  # check agent IDs")

    output.print_result(result.data, state.output)


@registry_app.command("sync")
def registry_sync(
    ctx: typer.Context,
) -> None:
    """Trigger a full registry sync across all registries.

    Idempotent — safe to run multiple times.

    Examples:
      myca registry sync
    """
    state = ctx.obj
    result = client.post(
        f"{state.config.mas_url}/api/registry/sync",
        config=state.config,
        json_body={},
    )
    if not result.ok:
        output.print_error(result.error, hint="myca system health")

    output.print_success("Registry sync triggered", data=result.data, fmt=state.output)


@registry_app.command("list")
def registry_list(
    ctx: typer.Context,
    type: str = typer.Option("agents", "--type", "-t", help="Registry type (agents, apis, skills)"),
) -> None:
    """List registry entries.

    Examples:
      myca registry list
      myca registry list --type apis --output table
      myca registry list --type skills
    """
    state = ctx.obj
    result = client.get(
        f"{state.config.mas_url}/api/registry/{type}",
        config=state.config,
    )
    if not result.ok:
        output.print_error(result.error, hint="myca system health")

    output.print_result(result.data, state.output)
