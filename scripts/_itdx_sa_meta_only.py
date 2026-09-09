"""Print google key meta from last-style SA POST. No secrets."""

from __future__ import annotations

import json
import urllib.request

URL = "http://192.168.0.188:8001/api/itdx/situation-assessment"


def find(obj: object, names: tuple[str, ...]) -> dict[str, object]:
    out: dict[str, object] = {}

    def rec(node: object) -> None:
        if isinstance(node, dict):
            for name in names:
                if name in node and name not in out:
                    out[name] = node[name]
            for value in node.values():
                rec(value)
        elif isinstance(node, list):
            for item in node:
                rec(item)

    rec(obj)
    return out


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
    req = urllib.request.Request(
        URL,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        body = json.loads(response.read().decode("utf-8", "replace"))
        print("HTTP", response.status)
    meta = find(
        body,
        (
            "google_key_present",
            "google_key_env_name",
            "google_status",
            "timed_out",
            "in_process",
        ),
    )
    print("META", meta)
    channels = body.get("channels") if isinstance(body, dict) else {}
    if isinstance(channels, dict):
        for name in ("traffic", "pathways", "navigation"):
            row = channels.get(name) if isinstance(channels.get(name), dict) else {}
            print(
                "CHANNEL",
                name,
                row.get("status"),
                "reason",
                row.get("reason"),
                "gstatus",
                row.get("google_status"),
            )


if __name__ == "__main__":
    main()
