#!/usr/bin/env python3
"""
Meridian adapter runner — CFO VM bridge to MAS CFO MCP.

Runs on the CFO VM (192.168.0.193). Sends heartbeats to C-Suite, optionally
exposes an HTTP server for Perplexity desktop to submit prompts as tasks.

Usage:
  python scripts/run_meridian_adapter.py
  python scripts/run_meridian_adapter.py --no-http          # Heartbeat only
  python scripts/run_meridian_adapter.py --http-port 8995   # Custom port

Env:
  MAS_API_URL — MAS API base (default http://192.168.0.188:8001)
  CFO_VM_IP   — This VM's IP (default 192.168.0.193)

Created: March 8, 2026
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add repo root so imports work when run from scripts/
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from mycosoft_mas.edge.meridian_adapter import MeridianAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("MeridianRunner")

HEARTBEAT_INTERVAL_SEC = int(os.environ.get("MERIDIAN_HEARTBEAT_INTERVAL", "60"))
DEFAULT_HTTP_PORT = int(os.environ.get("MERIDIAN_HTTP_PORT", "8995"))


async def heartbeat_loop(adapter: MeridianAdapter) -> None:
    """Send heartbeats to C-Suite every HEARTBEAT_INTERVAL_SEC."""
    while True:
        try:
            await adapter.send_heartbeat()
            logger.info("Heartbeat OK")
        except Exception as e:
            logger.warning("Heartbeat failed: %s", e)
        await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)


async def handle_prompt(adapter: MeridianAdapter, prompt: str) -> dict:
    """Submit a prompt as a finance task and return the result."""
    result = await adapter.submit_prompt_as_task(prompt)
    if "error" in result:
        return {"success": False, "error": result["error"]}
    return {"success": True, "result": result}


def main() -> None:
    parser = argparse.ArgumentParser(description="Meridian adapter for CFO VM")
    parser.add_argument("--no-http", action="store_true", help="Run heartbeat only, no HTTP server")
    parser.add_argument("--http-port", type=int, default=DEFAULT_HTTP_PORT, help="HTTP server port")
    args = parser.parse_args()

    mas_url = os.environ.get("MAS_API_URL", "http://192.168.0.188:8001")
    cfo_ip = os.environ.get("CFO_VM_IP", "192.168.0.193")
    adapter = MeridianAdapter(mas_api_url=mas_url, cfo_vm_ip=cfo_ip)

    async def run() -> None:
        if args.no_http:
            await heartbeat_loop(adapter)
            return

        # Run heartbeat loop and HTTP server concurrently
        try:
            from aiohttp import web
        except ImportError:
            logger.warning("aiohttp not installed; running heartbeat only. pip install aiohttp for HTTP server.")
            await heartbeat_loop(adapter)
            return

        async def prompt_handler(request: web.Request) -> web.Response:
            try:
                body = await request.json()
                prompt = body.get("prompt", "").strip()
                if not prompt:
                    return web.json_response({"success": False, "error": "prompt required"}, status=400)
                result = await handle_prompt(adapter, prompt)
                return web.json_response(result)
            except Exception as e:
                logger.exception("Prompt handler failed")
                return web.json_response({"success": False, "error": str(e)}, status=500)

        app = web.Application()
        app.router.add_post("/prompt", prompt_handler)
        app.router.add_get("/health", lambda r: web.json_response({"status": "ok", "role": "CFO"}))

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", args.http_port)
        await site.start()
        logger.info("Meridian adapter HTTP on port %d (POST /prompt, GET /health)", args.http_port)

        # Start heartbeat loop in background
        hb_task = asyncio.create_task(heartbeat_loop(adapter))
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            hb_task.cancel()

    asyncio.run(run())


if __name__ == "__main__":
    main()
