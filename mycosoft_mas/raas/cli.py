"""RaaS CLI — command-line interface for external agent integration.

Usage:
    python -m mycosoft_mas.raas.cli catalog
    python -m mycosoft_mas.raas.cli register --name "MyAgent" --email agent@example.com
    python -m mycosoft_mas.raas.cli balance --api-key myca_raas_xxx
    python -m mycosoft_mas.raas.cli invoke nlm --query "Identify Amanita muscaria"
    python -m mycosoft_mas.raas.cli packages
    python -m mycosoft_mas.raas.cli usage --api-key myca_raas_xxx

Created: March 11, 2026
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    httpx = None


DEFAULT_BASE_URL = os.getenv("RAAS_API_URL", "http://192.168.0.188:8001")


async def _request(
    method: str,
    path: str,
    base_url: str,
    api_key: Optional[str] = None,
    json_body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Make an HTTP request to the RaaS API."""
    if httpx is None:
        print("Error: httpx is required. Install with: pip install httpx", file=sys.stderr)
        sys.exit(1)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    url = f"{base_url}{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        if method == "GET":
            resp = await client.get(url, headers=headers)
        else:
            resp = await client.post(url, json=json_body or {}, headers=headers)
        return resp.json()


async def cmd_catalog(args: argparse.Namespace) -> None:
    """List available services."""
    result = await _request("GET", "/api/raas/services", args.base_url)
    print(json.dumps(result, indent=2))


async def cmd_packages(args: argparse.Namespace) -> None:
    """List credit packages."""
    result = await _request("GET", "/api/raas/payments/packages", args.base_url)
    print(json.dumps(result, indent=2))


async def cmd_register(args: argparse.Namespace) -> None:
    """Register a new agent."""
    result = await _request(
        "POST",
        "/api/raas/agents/register",
        args.base_url,
        json_body={
            "agent_name": args.name,
            "contact_email": args.email,
            "payment_method": args.payment_method,
            "description": args.description,
        },
    )
    print(json.dumps(result, indent=2))
    if "api_key" in result:
        print(f"\nSave your API key: {result['api_key']}", file=sys.stderr)
        print(f"Complete signup at: {result.get('signup_payment_url', '')}", file=sys.stderr)


async def cmd_balance(args: argparse.Namespace) -> None:
    """Check credit balance."""
    result = await _request("GET", "/api/raas/agents/me", args.base_url, api_key=args.api_key)
    print(json.dumps(result, indent=2))


async def cmd_usage(args: argparse.Namespace) -> None:
    """Get usage history."""
    result = await _request("GET", "/api/raas/agents/me/usage", args.base_url, api_key=args.api_key)
    print(json.dumps(result, indent=2))


async def cmd_invoke(args: argparse.Namespace) -> None:
    """Invoke a RaaS service."""
    service = args.service
    body: Dict[str, Any] = {}

    if service == "nlm":
        body = {
            "query": args.query,
            "query_type": args.query_type or "general",
        }
    elif service == "crep":
        body = {"data_type": args.data_type or "weather"}
    elif service == "earth2":
        body = {"forecast_type": args.forecast_type or "medium_range"}
    elif service == "data":
        body = {
            "query_type": args.query_type or "species",
            "query": args.query or "",
        }
    elif service == "agent":
        body = {
            "agent_type": args.agent_type or "general",
            "task_type": args.task_type or "process",
            "payload": json.loads(args.payload) if args.payload else {},
        }
    elif service == "memory":
        body = {
            "query": args.query or "",
            "search_type": args.search_type or "semantic",
        }
    elif service == "simulation":
        body = {
            "sim_type": args.sim_type or "petri",
            "parameters": json.loads(args.params) if args.params else {},
        }
    elif service == "devices":
        body = {
            "device_id": args.device_id,
            "query_type": "telemetry" if args.device_id else "list",
        }

    result = await _request(
        "POST",
        f"/api/raas/invoke/{service}",
        args.base_url,
        api_key=args.api_key,
        json_body=body,
    )
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mycosoft-raas",
        description="MYCA Robot-as-a-Service CLI — interact with Mycosoft's agent services",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="RaaS API base URL (default: %(default)s)",
    )
    parser.add_argument("--api-key", default=os.getenv("RAAS_API_KEY", ""), help="API key")

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # catalog
    sub.add_parser("catalog", help="List available services")

    # packages
    sub.add_parser("packages", help="List credit packages")

    # register
    reg = sub.add_parser("register", help="Register a new agent")
    reg.add_argument("--name", required=True, help="Agent name")
    reg.add_argument("--email", default=None, help="Contact email")
    reg.add_argument("--description", default=None, help="Agent description")
    reg.add_argument("--payment-method", default="stripe", choices=["stripe", "crypto"])

    # balance
    sub.add_parser("balance", help="Check credit balance")

    # usage
    sub.add_parser("usage", help="Get usage history")

    # invoke
    inv = sub.add_parser("invoke", help="Invoke a RaaS service")
    inv.add_argument(
        "service",
        choices=["nlm", "crep", "earth2", "data", "agent", "memory", "simulation", "devices"],
        help="Service to invoke",
    )
    inv.add_argument("--query", default="", help="Query string (for nlm, data, memory)")
    inv.add_argument("--query-type", default=None, help="Query type")
    inv.add_argument("--data-type", default=None, help="CREP data type")
    inv.add_argument("--forecast-type", default=None, help="Earth2 forecast type")
    inv.add_argument("--agent-type", default=None, help="Agent type for agent invocation")
    inv.add_argument("--task-type", default=None, help="Task type for agent invocation")
    inv.add_argument("--payload", default=None, help="JSON payload for agent invocation")
    inv.add_argument("--search-type", default=None, help="Memory search type")
    inv.add_argument("--sim-type", default=None, help="Simulation type")
    inv.add_argument("--params", default=None, help="JSON parameters for simulation")
    inv.add_argument("--device-id", default=None, help="Device ID for telemetry")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "catalog": cmd_catalog,
        "packages": cmd_packages,
        "register": cmd_register,
        "balance": cmd_balance,
        "usage": cmd_usage,
        "invoke": cmd_invoke,
    }

    handler = cmd_map.get(args.command)
    if handler:
        asyncio.run(handler(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
