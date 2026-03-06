"""
MYCA channel health — unified per-channel status for /channels endpoint.

Runs validation for Slack, Asana, Signal, Discord, WhatsApp and returns
status: connected | configured | missing_credential | error.

Date: 2026-03-05
"""

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger("myca.os.channels")


def _env_any(*names: str) -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


async def _validate_slack() -> dict[str, Any]:
    token = _env_any("SLACK_APP_TOKEN", "MYCA_SLACK_APP_TOKEN", "SLACK_OAUTH_TOKEN", "MYCA_SLACK_BOT_TOKEN")
    if not token:
        return {"channel": "slack", "status": "missing_credential", "message": "No Slack token set.", "pass": False}
    try:
        from mycosoft_mas.integrations.slack_client import SlackClient
        client = SlackClient(config={"token": token})
        ok = await client.auth_test()
        await client.close()
        return {"channel": "slack", "status": "connected", "message": "OK.", "pass": True} if ok else {"channel": "slack", "status": "auth_failed", "message": "Auth failed.", "pass": False}
    except Exception as e:
        return {"channel": "slack", "status": "error", "message": str(e), "pass": False}


async def _validate_asana() -> dict[str, Any]:
    if not _env_any("ASANA_API_KEY", "ASANA_PAT", "MYCA_ASANA_TOKEN"):
        return {"channel": "asana", "status": "missing_credential", "message": "Asana credential not set.", "pass": False}
    try:
        from mycosoft_mas.integrations.asana_client import AsanaClient
        client = AsanaClient()
        workspaces = await client.get_workspaces()
        await client.close()
        if workspaces:
            return {"channel": "asana", "status": "connected", "message": f"OK. {len(workspaces)} workspace(s).", "pass": True}
        return {"channel": "asana", "status": "auth_failed", "message": "No workspaces returned.", "pass": False}
    except Exception as e:
        return {"channel": "asana", "status": "error", "message": str(e), "pass": False}


async def _validate_signal() -> dict[str, Any]:
    if not _env_any("MYCA_SIGNAL_NUMBER", "SIGNAL_SENDER_NUMBER"):
        return {"channel": "signal", "status": "missing_credential", "message": "MYCA_SIGNAL_NUMBER not set.", "pass": False}
    try:
        from mycosoft_mas.integrations.signal_client import SignalClient
        client = SignalClient()
        ok = await client.health_check()
        await client.close()
        return {"channel": "signal", "status": "connected", "message": "signal-cli OK.", "pass": True} if ok else {"channel": "signal", "status": "unreachable", "message": "signal-cli REST API not reachable.", "pass": False}
    except Exception as e:
        return {"channel": "signal", "status": "error", "message": str(e), "pass": False}


async def _validate_discord() -> dict[str, Any]:
    if not _env_any("MYCA_DISCORD_TOKEN", "DISCORD_BOT_TOKEN"):
        return {"channel": "discord", "status": "missing_credential", "message": "Discord bot token not set.", "pass": False}
    try:
        from mycosoft_mas.integrations.discord_client import DiscordClient
        client = DiscordClient()
        ok = await client.auth_test()
        await client.close()
        return {"channel": "discord", "status": "connected", "message": "Bot connected.", "pass": True} if ok else {"channel": "discord", "status": "auth_failed", "message": "Auth failed.", "pass": False}
    except Exception as e:
        return {"channel": "discord", "status": "error", "message": str(e), "pass": False}


async def _validate_whatsapp() -> dict[str, Any]:
    try:
        from mycosoft_mas.integrations.whatsapp_client import WhatsAppClient
        client = WhatsAppClient()
        ok = await client.health_check()
        await client.close()
        return {"channel": "whatsapp", "status": "connected", "message": "Evolution API OK.", "pass": True} if ok else {"channel": "whatsapp", "status": "unreachable", "message": "Evolution API not reachable.", "pass": False}
    except Exception as e:
        return {"channel": "whatsapp", "status": "error", "message": str(e), "pass": False}


async def get_all_channel_status() -> dict[str, Any]:
    """Return per-channel status for all MYCA channels."""
    tasks = [_validate_slack(), _validate_asana(), _validate_signal(), _validate_discord(), _validate_whatsapp()]
    raw = await asyncio.gather(*tasks, return_exceptions=True)

    results: dict[str, Any] = {}
    for r in raw:
        if isinstance(r, Exception):
            logger.warning("Channel validation exception: %s", r)
            continue
        ch = r.get("channel", "unknown")
        results[ch] = {
            "status": r.get("status", "unknown"),
            "message": r.get("message", ""),
            "connected": r.get("pass", False),
        }

    return {"channels": results}
