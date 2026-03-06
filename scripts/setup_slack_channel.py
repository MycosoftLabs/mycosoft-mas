#!/usr/bin/env python3
"""
Slack channel setup and validation script.

Validates SLACK_APP_TOKEN (xapp-) for Socket Mode or SLACK_OAUTH_TOKEN for Web API.
Tests connection and reports pass/fail.

Usage:
    python scripts/setup_slack_channel.py

Environment:
    SLACK_APP_TOKEN: xapp- token for Socket Mode (slack_gateway.py)
    SLACK_OAUTH_TOKEN: xoxb- or xoxp- for Web API (slack_client.py)
"""

import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


async def validate_slack() -> dict:
    """Validate Slack credentials and connection."""
    result = {"channel": "slack", "status": "unknown", "message": "", "pass": False}

    # Check tokens
    app_token = os.getenv("SLACK_APP_TOKEN", "")
    oauth_token = os.getenv("SLACK_OAUTH_TOKEN", "")

    if not app_token and not oauth_token:
        result["status"] = "missing_credential"
        result["message"] = (
            "Neither SLACK_APP_TOKEN nor SLACK_OAUTH_TOKEN is set. "
            "Get xapp- from api.slack.com > App > Socket Mode > Enable > generate. "
            "Or use xoxb- OAuth token for Web API."
        )
        return result

    # Prefer OAuth for auth_test (SlackClient uses it)
    token_to_test = oauth_token or app_token
    if app_token and not app_token.startswith("xapp-"):
        result["status"] = "wrong_format"
        result["message"] = "SLACK_APP_TOKEN should start with xapp- for Socket Mode."
        return result
    if oauth_token and not (oauth_token.startswith("xoxb-") or oauth_token.startswith("xoxp-")):
        result["status"] = "wrong_format"
        result["message"] = "SLACK_OAUTH_TOKEN should start with xoxb- (bot) or xoxp- (user)."
        return result

    try:
        from mycosoft_mas.integrations.slack_client import SlackClient
        client = SlackClient(config={"token": token_to_test})
        ok = await client.auth_test()
        await client.close()
        if ok:
            result["status"] = "connected"
            result["message"] = "Slack auth test passed."
            result["pass"] = True
        else:
            result["status"] = "auth_failed"
            result["message"] = "Slack auth.test returned not ok. Check token validity."
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


def main():
    asyncio.run(validate_slack())


if __name__ == "__main__":
    r = asyncio.run(validate_slack())
    print(f"Slack: {r['status']} - {r['message']}")
    sys.exit(0 if r["pass"] else 1)
