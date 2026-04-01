"""myca raas — Research-as-a-Service for external agent customers.

Maps to:
  MCP:  raas_catalog, raas_register, raas_balance, raas_invoke_* (RaaS MCP)
  API:  /api/raas/*
"""

from __future__ import annotations

from typing import Optional

import typer

from mycosoft_mas.cli import _client as client
from mycosoft_mas.cli import _output as output

raas_app = typer.Typer(
    help="Research-as-a-Service — catalog, register, invoke MYCA services.",
    no_args_is_help=True,
)


@raas_app.command("catalog")
def raas_catalog(
    ctx: typer.Context,
) -> None:
    """List all available RaaS services with pricing.

    Examples:
      myca raas catalog
      myca raas catalog --output table
    """
    state = ctx.obj
    result = client.get(f"{state.config.mas_url}/api/raas/services", config=state.config)
    if not result.ok:
        output.print_error(result.error, hint="myca system health")

    output.print_result(
        result.data,
        state.output,
        keys=["name", "description", "price_per_call", "status"],
        headers=["SERVICE", "DESCRIPTION", "PRICE", "STATUS"],
    )


@raas_app.command("register")
def raas_register(
    ctx: typer.Context,
    agent_name: str = typer.Option(..., "--name", "-n", help="Name of the agent being registered"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Contact email for the agent owner"),
    payment: str = typer.Option("stripe", "--payment", "-p", help="Payment method (stripe, crypto)"),
) -> None:
    """Register a new agent as a RaaS customer.

    Examples:
      myca raas register --name "WeatherBot" --email bot@example.com
      myca raas register --name "ResearchAgent" --payment crypto
    """
    state = ctx.obj
    data = {
        "agent_name": agent_name,
        "payment_method": payment,
    }
    if email:
        data["contact_email"] = email

    result = client.post(
        f"{state.config.mas_url}/api/raas/agents/register",
        config=state.config,
        json_body=data,
    )
    if not result.ok:
        output.print_error(result.error, hint="myca raas catalog  # check available services")

    output.print_result(result.data, state.output)


@raas_app.command("balance")
def raas_balance(
    ctx: typer.Context,
) -> None:
    """Check credit balance for the authenticated agent.

    Examples:
      myca raas balance
      myca raas balance --output plain
    """
    state = ctx.obj
    result = client.get(f"{state.config.mas_url}/api/raas/agents/me", config=state.config)
    if not result.ok:
        output.print_error(result.error, hint="myca raas register  # register first if needed")

    output.print_result(result.data, state.output)


@raas_app.command("packages")
def raas_packages(
    ctx: typer.Context,
) -> None:
    """List available credit packages with pricing.

    Examples:
      myca raas packages
      myca raas packages --output table
    """
    state = ctx.obj
    result = client.get(f"{state.config.mas_url}/api/raas/payments/packages", config=state.config)
    if not result.ok:
        output.print_error(result.error, hint="myca system health")

    output.print_result(result.data, state.output)


@raas_app.command("invoke")
def raas_invoke(
    ctx: typer.Context,
    service: str = typer.Argument(..., help="Service to invoke (nlm, crep, earth2, data)"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Query string"),
    query_type: Optional[str] = typer.Option(None, "--type", "-t", help="Query type (service-specific)"),
    latitude: Optional[float] = typer.Option(None, "--lat", help="Latitude (for earth2)"),
    longitude: Optional[float] = typer.Option(None, "--lon", help="Longitude (for earth2)"),
    stdin: bool = typer.Option(False, "--stdin", help="Read invocation JSON from stdin"),
) -> None:
    """Invoke a RaaS service.

    Available services: nlm, crep, earth2, data

    Examples:
      myca raas invoke nlm --query "Identify Pleurotus ostreatus" --type species_id
      myca raas invoke crep --type weather
      myca raas invoke earth2 --type medium_range --lat 59.33 --lon 18.07
      myca raas invoke data --query "Amanita muscaria" --type species
      echo '{"query":"mycorrhizal networks"}' | myca raas invoke nlm --stdin
    """
    state = ctx.obj

    if stdin:
        data = client.read_stdin_json()
    else:
        if service == "nlm":
            if not query:
                output.print_error("--query is required for NLM", hint="myca raas invoke nlm --query 'your query'")
            data = {"query": query, "query_type": query_type or "general"}
        elif service == "crep":
            data = {"data_type": query_type or "weather"}
        elif service == "earth2":
            data = {"forecast_type": query_type or "medium_range"}
            if latitude is not None and longitude is not None:
                data["location"] = {"lat": latitude, "lon": longitude}
        elif service == "data":
            if not query:
                output.print_error("--query is required for data", hint="myca raas invoke data --query 'search term'")
            data = {"query": query, "query_type": query_type or "species"}
        else:
            output.print_error(
                f"Unknown service: {service}",
                hint="Available services: nlm, crep, earth2, data\n  myca raas catalog  # see all services",
            )

    result = client.post(
        f"{state.config.mas_url}/api/raas/invoke/{service}",
        config=state.config,
        json_body=data,
    )
    if not result.ok:
        output.print_error(result.error, hint="myca raas balance  # check credits")

    output.print_result(result.data, state.output)
