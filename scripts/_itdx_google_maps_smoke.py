"""Smoke-test Google Directions with a local maps-family key. Never print the key."""

from __future__ import annotations

import urllib.parse
import urllib.request
from pathlib import Path

CANDIDATES = (
    "GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
    "GOOGLE_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY",
)


def _load() -> tuple[str, str] | tuple[None, None]:
    files = (
        Path(__file__).resolve().parents[1] / ".credentials.local",
        Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local"),
        Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13\.env.local"),
    )
    for path in files:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in CANDIDATES and value:
                return key, value
    return None, None


def main() -> None:
    name, key = _load()
    if not key:
        print("NO_KEY")
        return
    print("USING_ENV_NAME", name)
    params = urllib.parse.urlencode(
        {
            "origin": "31.8697,-81.6072",
            "destination": "Hinesville,GA",
            "departure_time": "now",
            "mode": "driving",
            "key": key,
        }
    )
    url = "https://maps.googleapis.com/maps/api/directions/json?" + params
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mycosoft-MAS-ITDX/1.0 (public-osint)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            body = response.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        print("HTTP_ERROR", type(exc).__name__)
        return
    status = "UNKNOWN"
    if '"status"' in body:
        start = body.find('"status"')
        status = body[start : start + 40].replace("\n", " ")
    print("HTTP_OK status_excerpt", status)
    print("has_routes", '"routes"' in body and '"overview_polyline"' in body)
    print("denied", "REQUEST_DENIED" in body)
    print("invalid", "INVALID_REQUEST" in body)


if __name__ == "__main__":
    main()
