#!/usr/bin/env python3
"""
Discord channel setup and validation script.

Validates MYCA_DISCORD_TOKEN, tests auth, and verifies bot configuration.
If Message Content Intent is not enabled, logs clear instructions.

Usage:
    python scripts/setup_discord_channel.py

Environment:
    MYCA_DISCORD_TOKEN: Bot token for MYCA Discord bot
"""

import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


async def validate_discord() -> dict:
    """Validate Discord bot connection and configuration."""
    result = {"channel": "discord", "status": "unknown", "message": "", "pass": False}

    token = os.getenv("MYCA_DISCORD_TOKEN", "")

    if not token:
        result["status"] = "missing_credential"
        result["message"] = (
            "MYCA_DISCORD_TOKEN is not set. "
            "Get bot token from discord.com/developers > Your App > Bot."
        )
        return result

    try:
        from mycosoft_mas.integrations.discord_client import DiscordClient
        client = DiscordClient()
        ok = await client.auth_test()
        await client.close()

        if not ok:
            result["status"] = "auth_failed"
            result["message"] = "Discord auth failed. Check token validity."
            return result

        result["status"] = "connected"
        result["message"] = (
            "Discord bot connected. "
            "Ensure Message Content Intent is enabled at discord.com/developers > Bot > Privileged Gateway Intents "
            "if the bot must read message text."
        )
        result["pass"] = True
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


if __name__ == "__main__":
    r = asyncio.run(validate_discord())
    print(f"Discord: {r['status']} - {r['message']}")
    sys.exit(0 if r["pass"] else 1)
