"""myca memory — Memory CRUD and semantic search.

Maps to:
  MCP:  memory_write, memory_read, memory_search, memory_list, memory_delete (memory MCP)
  API:  Memory API endpoints
"""

from __future__ import annotations

from typing import Optional

import typer

from mycosoft_mas.cli import _client as client
from mycosoft_mas.cli import _output as output

memory_app = typer.Typer(
    help="Memory operations — write, read, search, list, delete.",
    no_args_is_help=True,
)


@memory_app.command("write")
def memory_write(
    ctx: typer.Context,
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Memory content to store"),
    layer: str = typer.Option("semantic", "--layer", "-l", help="Memory layer (ephemeral, session, working, semantic, episodic, system)"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID that owns this memory"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    stdin: bool = typer.Option(False, "--stdin", help="Read memory JSON from stdin"),
) -> None:
    """Store a new memory.

    Examples:
      myca memory write --content "Pleurotus ostreatus grows on hardwood" --layer semantic
      myca memory write --content "Deploy failed at 14:00" --layer episodic --agent deploy_agent
      myca memory write --content "User prefers table output" --tags "preference,cli"
      echo '{"content":"fact","layer":"semantic"}' | myca memory write --stdin
    """
    state = ctx.obj

    if stdin:
        data = client.read_stdin_json()
    elif content:
        data = {"content": content, "layer": layer}
        if agent:
            data["agent_id"] = agent
        if tags:
            data["tags"] = [t.strip() for t in tags.split(",")]
    else:
        output.print_error(
            "No content specified",
            hint="myca memory write --content 'Your memory text' --layer semantic",
        )

    result = client.post(
        f"{state.config.mas_url}/memory",
        config=state.config,
        json_body=data,
    )
    if not result.ok:
        output.print_error(result.error, hint="myca system health")

    output.print_result(result.data, state.output)


@memory_app.command("read")
def memory_read(
    ctx: typer.Context,
    memory_id: str = typer.Argument(..., help="Memory ID to retrieve"),
) -> None:
    """Read a specific memory by ID.

    Examples:
      myca memory read mem_abc123
      myca memory read mem_abc123 --output plain
    """
    state = ctx.obj
    result = client.get(
        f"{state.config.mas_url}/memory/{memory_id}",
        config=state.config,
    )
    if not result.ok:
        output.print_error(result.error, hint="myca memory list  # find valid memory IDs")

    output.print_result(result.data, state.output)


@memory_app.command("search")
def memory_search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query (natural language)"),
    layer: Optional[str] = typer.Option(None, "--layer", "-l", help="Filter by memory layer"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent ID"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max results"),
) -> None:
    """Semantic search across memories.

    Examples:
      myca memory search "mycology cultivation techniques"
      myca memory search "deployment errors" --layer episodic --limit 5
      myca memory search "user preferences" --agent secretary_agent
      myca memory search "weather data" --output table
    """
    state = ctx.obj
    params: dict = {"query": query, "limit": limit}
    if layer:
        params["layer"] = layer
    if agent:
        params["agent_id"] = agent

    result = client.post(
        f"{state.config.mas_url}/api/search/memory",
        config=state.config,
        json_body=params,
    )
    if not result.ok:
        result = client.get(
            f"{state.config.mas_url}/api/search/memory",
            config=state.config,
            params=params,
        )
    if not result.ok:
        output.print_error(result.error, hint="myca system health")

    output.print_result(
        result.data,
        state.output,
        keys=["id", "content", "layer", "score"],
        headers=["ID", "CONTENT", "LAYER", "SCORE"],
    )


@memory_app.command("list")
def memory_list(
    ctx: typer.Context,
    layer: Optional[str] = typer.Option(None, "--layer", "-l", help="Filter by memory layer"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
) -> None:
    """List memories with optional filters.

    Examples:
      myca memory list
      myca memory list --layer semantic --limit 10
      myca memory list --agent coding_agent --output table
    """
    state = ctx.obj
    params: dict = {"limit": limit}
    if layer:
        params["layer"] = layer
    if agent:
        params["agent_id"] = agent

    result = client.get(
        f"{state.config.mas_url}/memory",
        config=state.config,
        params=params,
    )
    if not result.ok:
        output.print_error(result.error, hint="myca system health")

    output.print_result(
        result.data,
        state.output,
        keys=["id", "content", "layer", "agent_id", "created_at"],
        headers=["ID", "CONTENT", "LAYER", "AGENT", "CREATED"],
    )


@memory_app.command("delete")
def memory_delete(
    ctx: typer.Context,
    memory_id: str = typer.Argument(..., help="Memory ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a memory by ID.

    Examples:
      myca memory delete mem_abc123 --yes
      myca memory delete mem_abc123
    """
    state = ctx.obj
    skip_confirm = yes or state.yes

    if not skip_confirm:
        output.print_error(
            "Destructive action requires confirmation",
            hint=f"myca memory delete {memory_id} --yes",
        )

    result = client.delete(
        f"{state.config.mas_url}/memory/{memory_id}",
        config=state.config,
    )
    if not result.ok:
        output.print_error(result.error, hint="myca memory list  # find valid memory IDs")

    output.print_success(f"Deleted memory {memory_id}", fmt=state.output)
