"""Curl situation-assessment; print channel statuses only. No secrets."""

from __future__ import annotations

import json
import re
import urllib.request

AIZA = re.compile(r"AIza[0-9A-Za-z_-]{10,}")
URL = "http://192.168.0.188:8001/api/itdx/situation-assessment"
WANTED = ("traffic", "pathways", "navigation")


def walk_channels(obj: object) -> dict[str, dict]:
    found: dict[str, dict] = {}

    def rec(node: object) -> None:
        if isinstance(node, dict):
            for name in WANTED:
                row = node.get(name)
                if isinstance(row, dict) and (
                    "status" in row or "state" in row or "reason" in row or "error" in row
                ):
                    found.setdefault(name, row)
            for value in node.values():
                rec(value)
        elif isinstance(node, list):
            for item in node:
                rec(item)

    rec(obj)
    return found


def call(method: str, data: bytes | None = None) -> None:
    req = urllib.request.Request(
        URL,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "User-Agent": "Mycosoft-MAS-ITDX/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8", "replace"))
            print(method, "HTTP", response.status)
    except Exception as exc:  # noqa: BLE001
        print(method, "HTTP_ERROR", type(exc).__name__)
        return
    text = AIZA.sub("AIza***", json.dumps(body))
    body = json.loads(text)
    print("keys", sorted(body)[:20] if isinstance(body, dict) else type(body).__name__)
    for k in ("google_key_present", "google_key_env_name", "in_process", "self_http", "timed_out"):
        if isinstance(body, dict) and k in body:
            print("META", k, body.get(k))
    found = walk_channels(body)
    for name in WANTED:
        row = found.get(name)
        if not row:
            print("CHANNEL", name, "MISSING")
            continue
        status = row.get("status") or row.get("state")
        reason = str(row.get("reason") or row.get("error") or row.get("note") or "")[:200]
        print("CHANNEL", name, status, "|", reason)


def main() -> None:
    payload = json.dumps(
        {
            "slice": {
                "name": "Fort Stewart",
                "bbox": [-81.70, 31.80, -81.45, 32.05],
                "center": [31.88, -81.61],
            }
        }
    ).encode("utf-8")
    call("POST", payload)


if __name__ == "__main__":
    main()
