#!/usr/bin/env python3
"""
Signal channel setup and validation script.

Validates MYCA_SIGNAL_CLI_URL and MYCA_SIGNAL_NUMBER.
Tests signal-cli REST API health and number registration.

Usage:
    python scripts/setup_signal_channel.py

Environment:
    MYCA_SIGNAL_CLI_URL: signal-cli REST base URL (default http://192.168.0.191:8089)
    MYCA_SIGNAL_NUMBER: MYCA's Signal phone number (e.g. +1234567890)
"""

import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


async def validate_signal() -> dict:
    """Validate Signal (signal-cli) connection."""
    result = {"channel": "signal", "status": "unknown", "message": "", "pass": False}

    base_url = os.getenv("MYCA_SIGNAL_CLI_URL", "http://192.168.0.191:8089").rstrip("/")
    number = os.getenv("MYCA_SIGNAL_NUMBER", "")

    if not number:
        result["status"] = "missing_credential"
        result["message"] = (
            "MYCA_SIGNAL_NUMBER is not set. "
            "Configure signal-cli on VM 191 and register a number. "
            "See docs/MYCA_PLATFORM_STATUS_AND_GAPS_MAR05_2026.md"
        )
        return result

    try:
        from mycosoft_mas.integrations.signal_client import SignalClient
        client = SignalClient()
        health_ok = await client.health_check()
        await client.close()

        if not health_ok:
            result["status"] = "unreachable"
            result["message"] = (
                f"signal-cli REST API at {base_url} is not reachable. "
                "Ensure signal-cli-rest-api container is running on VM 191 (port 8089)."
            )
            return result

        result["status"] = "connected"
        result["message"] = f"signal-cli REST API OK at {base_url}. Number {number} configured."
        result["pass"] = True
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


if __name__ == "__main__":
    r = asyncio.run(validate_signal())
    print(f"Signal: {r['status']} - {r['message']}")
    sys.exit(0 if r["pass"] else 1)
