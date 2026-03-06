#!/usr/bin/env python3
"""
Asana channel setup and validation script.

Validates ASANA_API_KEY (Personal Access Token), tests API (list workspaces),
and reports pass/fail.

Usage:
    python scripts/setup_asana_channel.py

Environment:
    ASANA_API_KEY: Personal access token from Asana (My Profile > Apps > Personal Access Token)
"""

import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


async def validate_asana() -> dict:
    """Validate Asana credentials and connection."""
    result = {"channel": "asana", "status": "unknown", "message": "", "pass": False}

    api_key = os.getenv("ASANA_API_KEY", "")

    if not api_key:
        result["status"] = "missing_credential"
        result["message"] = (
            "ASANA_API_KEY is not set. "
            "Get PAT from Asana > My Profile > Apps > Personal Access Token."
        )
        return result

    try:
        from mycosoft_mas.integrations.asana_client import AsanaClient
        client = AsanaClient()
        workspaces = await client.get_workspaces()
        await client.close()
        if workspaces:
            result["status"] = "connected"
            result["message"] = f"Asana API OK. {len(workspaces)} workspace(s) accessible."
            result["pass"] = True
        else:
            result["status"] = "auth_failed"
            result["message"] = "Asana API returned no workspaces. Check PAT validity."
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


if __name__ == "__main__":
    r = asyncio.run(validate_asana())
    print(f"Asana: {r['status']} - {r['message']}")
    sys.exit(0 if r["pass"] else 1)
