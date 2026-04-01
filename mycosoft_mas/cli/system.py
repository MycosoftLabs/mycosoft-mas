"""myca system — System health and service status.

Maps to:
  MCP:  system_health, service_status (orchestrator MCP)
  API:  /health, /api/registry/agents, service health endpoints
"""

from __future__ import annotations

from typing import Optional

import typer

from mycosoft_mas.cli import _client as client
from mycosoft_mas.cli import _output as output

system_app = typer.Typer(
    help="System health, services, and infrastructure info.",
    no_args_is_help=True,
)


@system_app.command("health")
def system_health(
    ctx: typer.Context,
    check_vms: bool = typer.Option(True, "--vms/--no-vms", help="Check VM connectivity"),
    check_services: bool = typer.Option(True, "--services/--no-services", help="Check service health"),
    check_agents: bool = typer.Option(True, "--agents/--no-agents", help="Check agent health"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Detailed output"),
) -> None:
    """Get comprehensive MAS system health.

    Checks VMs (187-191), core services, and agent status.
    Returns overall health as healthy, degraded, or unhealthy.

    Examples:
      myca system health
      myca system health --verbose
      myca system health --no-vms --no-agents
      myca system health --output table
    """
    state = ctx.obj
    health: dict = {"overall": "healthy", "issues": []}

    if check_vms:
        health["vms"] = {}
        vm_checks = [
            ("mas_188", state.config.mas_url, "/health"),
            ("mindex_189", state.config.mindex_url, "/health"),
        ]
        for vm_name, base_url, path in vm_checks:
            r = client.get(f"{base_url}{path}", config=state.config)
            health["vms"][vm_name] = {
                "status": "healthy" if r.ok else "unhealthy",
                "url": base_url,
            }
            if not r.ok:
                health["issues"].append(f"{vm_name}: {r.error}")

    if check_services:
        health["services"] = {}
        svc_checks = [
            ("orchestrator", f"{state.config.mas_url}/health"),
            ("mindex", f"{state.config.mindex_url}/health"),
        ]
        for svc_name, url in svc_checks:
            r = client.get(url, config=state.config)
            status = "healthy" if r.ok else "unhealthy"
            health["services"][svc_name] = {"status": status}
            if verbose and r.ok:
                health["services"][svc_name]["details"] = r.data
            if not r.ok:
                health["issues"].append(f"{svc_name}: {r.error}")

    if check_agents:
        r = client.get(f"{state.config.mas_url}/api/registry/agents", config=state.config)
        if r.ok:
            agents = r.data.get("agents", r.data if isinstance(r.data, list) else [])
            health["agents"] = {
                "total": len(agents),
                "active": len([a for a in agents if a.get("status") == "active"]),
                "error": len([a for a in agents if a.get("status") == "error"]),
            }
        else:
            health["agents"] = {"status": "unavailable", "error": r.error}
            health["issues"].append(f"agent_registry: {r.error}")

    if health["issues"]:
        health["overall"] = "degraded" if len(health["issues"]) < 3 else "unhealthy"

    output.print_result(health, state.output)


@system_app.command("services")
def system_services(
    ctx: typer.Context,
) -> None:
    """Check status of all MAS infrastructure services.

    Examples:
      myca system services
      myca system services --output table
    """
    state = ctx.obj
    services = [
        ("orchestrator", f"{state.config.mas_url}/health"),
        ("mindex", f"{state.config.mindex_url}/health"),
        ("website", "http://192.168.0.187:3000/api/health"),
        ("n8n", "http://192.168.0.188:5678/healthz"),
        ("ollama", "http://192.168.0.188:11434/api/tags"),
    ]

    results = []
    for name, url in services:
        r = client.get(url, config=state.config)
        results.append({
            "service": name,
            "url": url,
            "status": "healthy" if r.ok else "unhealthy",
            "error": r.error if not r.ok else "",
        })

    output.print_result(
        {"services": results},
        state.output,
        keys=["service", "status", "url", "error"],
        headers=["SERVICE", "STATUS", "URL", "ERROR"],
    )


@system_app.command("info")
def system_info(
    ctx: typer.Context,
) -> None:
    """Show MAS system info — version, agent count, uptime.

    Examples:
      myca system info
      myca system info --output plain
    """
    state = ctx.obj

    info: dict = {"version": "myca-cli 1.0.0", "mas_url": state.config.mas_url}

    # Try to get orchestrator info
    r = client.get(f"{state.config.mas_url}/health", config=state.config)
    if r.ok:
        info["orchestrator"] = r.data

    r = client.get(f"{state.config.mas_url}/api/registry/agents", config=state.config)
    if r.ok:
        agents = r.data.get("agents", r.data if isinstance(r.data, list) else [])
        info["agent_count"] = len(agents)

    output.print_result(info, state.output)
