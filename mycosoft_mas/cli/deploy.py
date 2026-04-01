"""myca deploy — Deploy to MAS infrastructure VMs.

Supports --dry-run to preview changes and --yes to skip confirmations.
All deploys are idempotent — rerunning reports no-op if already at target version.
"""

from __future__ import annotations

from typing import Optional

import typer

from mycosoft_mas.cli import _client as client
from mycosoft_mas.cli import _output as output

deploy_app = typer.Typer(
    help="Deploy to MAS VMs — with dry-run and confirmation support.",
    no_args_is_help=True,
)


def _get_deploy_plan(target: str, tag: str) -> dict:
    """Build a deploy plan for the target VM."""
    plans = {
        "mas": {
            "target": "MAS (192.168.0.188)",
            "tag": tag,
            "steps": [
                f"Stop container myca-orchestrator-new",
                f"Remove container myca-orchestrator-new",
                f"Pull image mycosoft/mas-agent:{tag}",
                f"Start new container myca-orchestrator-new with image mycosoft/mas-agent:{tag}",
                "Verify health at http://192.168.0.188:8001/health",
            ],
            "port": 8001,
            "container": "myca-orchestrator-new",
            "image": f"mycosoft/mas-agent:{tag}",
        },
        "mindex": {
            "target": "MINDEX (192.168.0.189)",
            "tag": tag,
            "steps": [
                "Stop mindex-api container",
                f"Build mindex-api image with tag {tag}",
                "Start mindex-api container",
                "Verify health at http://192.168.0.189:8000/health",
            ],
            "port": 8000,
            "container": "mindex-api",
            "image": f"mindex-api:{tag}",
        },
        "website": {
            "target": "Website (192.168.0.187)",
            "tag": tag,
            "steps": [
                f"Build website image with tag {tag}",
                "Mount NAS assets volume",
                "Restart website container",
                "Purge Cloudflare cache",
                "Verify health at http://192.168.0.187:3000/api/health",
            ],
            "port": 3000,
            "container": "website",
            "image": f"website:{tag}",
        },
    }
    return plans.get(target, {})


@deploy_app.command("mas")
def deploy_mas(
    ctx: typer.Context,
    tag: str = typer.Option("latest", "--tag", "-t", help="Image tag to deploy"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview deployment without executing"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Deploy to the MAS VM (192.168.0.188).

    Examples:
      myca deploy mas --tag v1.2.3 --dry-run
      myca deploy mas --tag v1.2.3 --yes
      myca deploy mas --tag latest
    """
    _deploy(ctx, "mas", tag, dry_run, yes)


@deploy_app.command("mindex")
def deploy_mindex(
    ctx: typer.Context,
    tag: str = typer.Option("latest", "--tag", "-t", help="Image tag to deploy"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview deployment without executing"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Deploy to the MINDEX VM (192.168.0.189).

    Examples:
      myca deploy mindex --tag v1.2.3 --dry-run
      myca deploy mindex --tag v1.2.3 --yes
    """
    _deploy(ctx, "mindex", tag, dry_run, yes)


@deploy_app.command("website")
def deploy_website(
    ctx: typer.Context,
    tag: str = typer.Option("latest", "--tag", "-t", help="Image tag to deploy"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview deployment without executing"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Deploy to the Website VM (192.168.0.187).

    Examples:
      myca deploy website --tag v1.2.3 --dry-run
      myca deploy website --tag v1.2.3 --yes
    """
    _deploy(ctx, "website", tag, dry_run, yes)


def _deploy(ctx: typer.Context, target: str, tag: str, dry_run: bool, yes: bool) -> None:
    """Shared deploy logic with dry-run and confirmation support."""
    state = ctx.obj
    plan = _get_deploy_plan(target, tag)

    if not plan:
        output.print_error(
            f"Unknown deploy target: {target}",
            hint="Available targets: mas, mindex, website",
        )

    if dry_run:
        result = {
            "dry_run": True,
            "target": plan["target"],
            "tag": tag,
            "steps": plan["steps"],
            "message": "No changes made.",
        }
        if state.output != "json":
            print(f"Would deploy {tag} to {plan['target']}")
            for step in plan["steps"]:
                print(f"  - {step}")
            print("No changes made.")
        else:
            output.print_result(result, "json")
        return

    skip_confirm = yes or state.yes
    if not skip_confirm:
        output.print_error(
            "Deployment requires confirmation",
            hint=f"myca deploy {target} --tag {tag} --yes\n  myca deploy {target} --tag {tag} --dry-run  # preview first",
        )

    # Execute deploy via MAS API
    result = client.post(
        f"{state.config.mas_url}/api/deploy/{target}",
        config=state.config,
        json_body={"tag": tag, "target": target},
    )
    if not result.ok:
        output.print_error(result.error, hint=f"myca deploy {target} --tag {tag} --dry-run  # check plan")

    deploy_data = {
        "status": "deployed",
        "target": plan["target"],
        "tag": tag,
        "container": plan.get("container", ""),
        "image": plan.get("image", ""),
    }
    deploy_data.update(result.data)
    output.print_result(deploy_data, state.output)


@deploy_app.command("status")
def deploy_status(
    ctx: typer.Context,
    target: Optional[str] = typer.Option(None, "--target", "-t", help="Specific target (mas, mindex, website)"),
) -> None:
    """Check deployment status of VMs.

    Examples:
      myca deploy status
      myca deploy status --target mas
      myca deploy status --output table
    """
    state = ctx.obj

    if target:
        targets = [target]
    else:
        targets = ["mas", "mindex", "website"]

    statuses = []
    health_urls = {
        "mas": f"{state.config.mas_url}/health",
        "mindex": f"{state.config.mindex_url}/health",
        "website": "http://192.168.0.187:3000/api/health",
    }

    for t in targets:
        url = health_urls.get(t, "")
        if not url:
            continue
        r = client.get(url, config=state.config)
        statuses.append({
            "target": t,
            "status": "running" if r.ok else "unreachable",
            "url": url,
            "details": r.data if r.ok else {"error": r.error},
        })

    output.print_result(
        {"deployments": statuses},
        state.output,
        keys=["target", "status", "url"],
        headers=["TARGET", "STATUS", "URL"],
    )
