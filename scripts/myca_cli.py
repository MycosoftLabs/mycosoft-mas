#!/usr/bin/env python3
"""
MYCA CLI — Command-line interface to talk to MYCA via the gateway.

Usage:
  python scripts/myca_cli.py status
  python scripts/myca_cli.py tasks
  python scripts/myca_cli.py send "check emails"
  python scripts/myca_cli.py task "Deploy website" --priority high
  python scripts/myca_cli.py logs
  python scripts/myca_cli.py shell "uptime"

Date: 2026-03-05
"""

import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print("pip install requests", file=sys.stderr)
    sys.exit(1)

GATEWAY_URL = os.getenv("MYCA_GATEWAY_URL", "http://192.168.0.191:8100")


def get(path: str) -> dict:
    r = requests.get(f"{GATEWAY_URL.rstrip('/')}{path}", timeout=10)
    r.raise_for_status()
    return r.json()


def post(path: str, data: dict) -> dict:
    r = requests.post(f"{GATEWAY_URL.rstrip('/')}{path}", json=data, timeout=30)
    r.raise_for_status()
    return r.json()


def cmd_status(_):
    data = get("/status")
    print(json.dumps(data, indent=2))


def cmd_health(_):
    data = get("/health")
    print(json.dumps(data, indent=2))


def cmd_tasks(_):
    data = get("/tasks")
    for t in data.get("tasks", []):
        print(f"  [{t.get('status', '?')}] {t.get('title', '?')} ({t.get('priority', '?')})")
    print(f"\nTotal: {data.get('count', 0)}")


def cmd_send(args):
    msg = args.message or " ".join(args.extra) if args.extra else ""
    if not msg:
        print("Usage: myca_cli send <message>", file=sys.stderr)
        sys.exit(1)
    data = post("/message", {"content": msg, "sender": "cli", "is_morgan": True})
    print("Sent:", data.get("status", "ok"))


def cmd_task(args):
    title = args.title or " ".join(args.extra) if args.extra else "Untitled"
    data = post("/tasks", {
        "title": title,
        "description": args.description or title,
        "priority": args.priority or "medium",
        "type": args.type or "general",
    })
    print("Added:", data.get("status", "ok"), "-", data.get("title", title))


def cmd_logs(args):
    n = getattr(args, "n", 50) or 50
    data = get(f"/logs?n={n}")
    for line in data.get("logs", []):
        print(line)


def cmd_shell(args):
    cmd = args.command or " ".join(args.extra) if args.extra else ""
    if not cmd:
        print("Usage: myca_cli shell <command>", file=sys.stderr)
        sys.exit(1)
    data = post("/shell", {"command": cmd})
    print("Return code:", data.get("returncode", "?"))
    if data.get("stdout"):
        print("--- stdout ---")
        print(data["stdout"])
    if data.get("stderr"):
        print("--- stderr ---", file=sys.stderr)
        print(data["stderr"], file=sys.stderr)


def main():
    global GATEWAY_URL
    p = argparse.ArgumentParser(description="MYCA CLI — talk to MYCA via gateway")
    p.add_argument("--url", default=None, help="Gateway URL (default: http://192.168.0.191:8100)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Daemon status").set_defaults(func=cmd_status)
    sub.add_parser("health", help="Health check").set_defaults(func=cmd_health)
    sub.add_parser("tasks", help="List task queue").set_defaults(func=cmd_tasks)
    sp = sub.add_parser("send", help="Send message to MYCA")
    sp.add_argument("message", nargs="?", help="Message content")
    sp.add_argument("extra", nargs="*")
    sp.set_defaults(func=cmd_send)
    sp = sub.add_parser("task", help="Add task")
    sp.add_argument("title", nargs="?", help="Task title")
    sp.add_argument("--description", "-d", help="Task description")
    sp.add_argument("--priority", "-p", choices=["critical", "high", "medium", "low"], default="medium")
    sp.add_argument("--type", "-t", default="general")
    sp.add_argument("extra", nargs="*")
    sp.set_defaults(func=cmd_task)
    sp = sub.add_parser("shell", help="Run shell command")
    sp.add_argument("command", nargs="?", help="Shell command")
    sp.add_argument("extra", nargs="*")
    sp.set_defaults(func=cmd_shell)
    lp = sub.add_parser("logs", help="Tail logs")
    lp.add_argument("-n", type=int, default=50)
    lp.set_defaults(func=cmd_logs, n=50)

    args = p.parse_args()
    if args.url is not None:
        GATEWAY_URL = args.url

    try:
        args.func(args)
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to {GATEWAY_URL}. Is MYCA running?", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
