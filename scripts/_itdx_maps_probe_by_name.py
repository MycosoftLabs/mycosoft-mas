"""Probe named keys from local creds. Never print values."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

AIZA = re.compile(r"AIza[0-9A-Za-z_-]{10,}")
CREDS = Path(__file__).resolve().parents[1] / ".credentials.local"
ORIGIN = "31.8697,-81.6072"
HUNTER = "Hunter Army Airfield, Savannah, GA"
HINESVILLE = "Hinesville, GA"


def load() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        out[name.strip()] = value.strip().strip('"').strip("'")
    return out


def probe(label: str, key: str) -> None:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    print("KEY", label, "sha256_12", digest, "len", len(key), "prefix", key[:4])
    checks = [
        (
            "directions_hunter",
            "https://maps.googleapis.com/maps/api/directions/json",
            {"origin": ORIGIN, "destination": HUNTER, "departure_time": "now", "mode": "driving", "key": key},
        ),
        (
            "matrix_hinesville",
            "https://maps.googleapis.com/maps/api/distancematrix/json",
            {
                "origins": ORIGIN,
                "destinations": f"{HUNTER}|{HINESVILLE}",
                "departure_time": "now",
                "mode": "driving",
                "key": key,
            },
        ),
    ]
    for name, url, params in checks:
        req = urllib.request.Request(
            url + "?" + urllib.parse.urlencode(params),
            headers={"User-Agent": "Mycosoft-MAS-ITDX/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                body = json.loads(response.read().decode("utf-8", "replace"))
            status = str(body.get("status", "UNKNOWN"))
            err = AIZA.sub("AIza***", str(body.get("error_message") or ""))
            print("PROBE", name, status, "|", err)
        except Exception as exc:  # noqa: BLE001
            print("PROBE", name, "HTTP_ERROR", type(exc).__name__)


def main() -> None:
    env = load()
    for name in ("GOOGLE_AI_API_KEY", "GOOGLE_MAPS_API_KEY"):
        value = env.get(name) or ""
        if value:
            probe(name, value)


if __name__ == "__main__":
    main()
