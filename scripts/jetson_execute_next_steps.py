#!/usr/bin/env python3
"""
Execution helper for Jetson next steps.

Runs smoke checks against:
- on-device operator (Jetson16) at :8110
- gateway router (Jetson4) at :8120
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict
import httpx


def _print(title: str, payload: Dict[str, Any]) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Jetson execution stack")
    parser.add_argument("--ondevice-url", default="http://127.0.0.1:8110")
    parser.add_argument("--gateway-url", default="http://127.0.0.1:8120")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    timeout = httpx.Timeout(args.timeout)
    with httpx.Client(timeout=timeout) as client:
        ondevice_health = client.get(f"{args.ondevice_url.rstrip('/')}/health").json()
        _print("On-Device Health", ondevice_health)

        side_a = client.post(
            f"{args.ondevice_url.rstrip('/')}/side-a/command",
            json={"command": "health", "params": {}, "ack_requested": True, "source": "smoke"},
        ).json()
        _print("Side A Health Command", side_a)

        side_b = client.post(
            f"{args.ondevice_url.rstrip('/')}/side-b/command",
            json={"command": "transport_status", "params": {}, "ack_requested": True, "source": "smoke"},
        ).json()
        _print("Side B Transport Status", side_b)

        gateway_health = client.get(f"{args.gateway_url.rstrip('/')}/health").json()
        _print("Gateway Health", gateway_health)

        reg = client.post(f"{args.gateway_url.rstrip('/')}/gateway/register").json()
        _print("Gateway Register", reg)

        ingest = client.post(
            f"{args.gateway_url.rstrip('/')}/ingest",
            json={
                "device_id": "mushroom1-smoke",
                "transport": "lora",
                "payload": {"readings": [{"sensor": "bme688_a", "temperature": 23.4}]},
            },
        ).json()
        _print("Gateway Ingest", ingest)

        flush = client.post(f"{args.gateway_url.rstrip('/')}/flush").json()
        _print("Gateway Flush", flush)


if __name__ == "__main__":
    main()
