#!/usr/bin/env python3
"""
WhatsApp channel setup and validation script.

Validates MYCA_EVOLUTION_API_URL and MYCA_WHATSAPP_INSTANCE.
Tests Evolution API reachability.

Usage:
    python scripts/setup_whatsapp_channel.py

Environment:
    MYCA_EVOLUTION_API_URL: Evolution API base URL (default http://192.168.0.191:8083)
    MYCA_WHATSAPP_INSTANCE: Instance name for Evolution API (default: myca)
"""

import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


async def validate_whatsapp() -> dict:
    """Validate WhatsApp (Evolution API) connection."""
    result = {"channel": "whatsapp", "status": "unknown", "message": "", "pass": False}

    base_url = os.getenv("MYCA_EVOLUTION_API_URL", "http://192.168.0.191:8083").rstrip("/")
    instance = os.getenv("MYCA_WHATSAPP_INSTANCE", "myca")

    try:
        from mycosoft_mas.integrations.whatsapp_client import WhatsAppClient
        client = WhatsAppClient()
        health_ok = await client.health_check()
        await client.close()

        if not health_ok:
            result["status"] = "unreachable"
            result["message"] = (
                f"Evolution API at {base_url} is not reachable. "
                "Add Evolution API container to deploy_myca_191_v2.py or run it on VM 191 (port 8083)."
            )
            return result

        result["status"] = "connected"
        result["message"] = f"Evolution API OK at {base_url}. Instance: {instance}."
        result["pass"] = True
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


if __name__ == "__main__":
    r = asyncio.run(validate_whatsapp())
    print(f"WhatsApp: {r['status']} - {r['message']}")
    sys.exit(0 if r["pass"] else 1)
