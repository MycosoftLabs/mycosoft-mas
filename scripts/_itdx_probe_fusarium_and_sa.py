"""Probe Fusarium Maps key + situation-assessment. Never print secrets."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

AIZA = re.compile(r"AIza[0-9A-Za-z_-]{10,}")
CREDS = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local")
ORIGIN = "31.8697,-81.6072"
HUNTER = "Hunter Army Airfield, Savannah, GA"
HINESVILLE = "Hinesville, GA"
SA_URL = "http://192.168.0.188:8001/api/itdx/situation-assessment"


def fusarium_key() -> str:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == "FUSARIUM_GOOGLE_MAPS_API_KEY":
            return value.strip().strip('"').strip("'")
    return ""


def probe(key: str) -> None:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    print("PROBE_KEY sha256_12", digest, "len", len(key), "AIza", key.startswith("AIza"))
    checks = [
        (
            "directions_hunter",
            "https://maps.googleapis.com/maps/api/directions/json",
            {
                "origin": ORIGIN,
                "destination": HUNTER,
                "departure_time": "now",
                "mode": "driving",
                "key": key,
            },
        ),
        (
            "matrix_hunter_hinesville",
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
    for label, url, params in checks:
        req = urllib.request.Request(
            url + "?" + urllib.parse.urlencode(params),
            headers={"User-Agent": "Mycosoft-MAS-ITDX/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                body = json.loads(response.read().decode("utf-8", "replace"))
            status = str(body.get("status", "UNKNOWN"))
            err = AIZA.sub("AIza***", str(body.get("error_message") or ""))
            extra = ""
            if status == "OK" and isinstance(body.get("routes"), list):
                extra = f"routes={len(body['routes'])}"
            if status == "OK" and isinstance(body.get("rows"), list):
                els = ((body.get("rows") or [{}])[0].get("elements") or [])
                extra = "elements=" + ",".join(
                    str(e.get("status")) for e in els if isinstance(e, dict)
                )
            print("PROBE", label, status, "|", err, "|", extra)
        except Exception as exc:  # noqa: BLE001
            print("PROBE", label, "HTTP_ERROR", type(exc).__name__)


def situation() -> None:
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
        SA_URL,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "Mycosoft-MAS-ITDX/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8", "replace"))
            http = response.status
    except urllib.error.HTTPError as exc:
        raw = AIZA.sub("AIza***", exc.read().decode("utf-8", "replace"))[:240]
        print("SA HTTP", exc.code, raw)
        return
    except Exception as exc:  # noqa: BLE001
        print("SA HTTP_ERROR", type(exc).__name__)
        return
    print("SA HTTP", http)
    channels = body.get("channels") or body.get("situation") or body
    if isinstance(channels, dict):
        wanted = ("traffic", "pathways", "navigation")
        src = channels.get("channels") if isinstance(channels.get("channels"), dict) else channels
        for name in wanted:
            row = src.get(name) if isinstance(src, dict) else None
            if isinstance(row, dict):
                status = row.get("status") or row.get("state") or row.get("qualification")
                reason = AIZA.sub("AIza***", str(row.get("reason") or row.get("error") or row.get("note") or ""))
                print("CHANNEL", name, status, "|", reason[:180])
            else:
                print("CHANNEL", name, "MISSING")
        extras = {
            k: channels.get(k)
            for k in ("google_key_present", "google_key_env_name", "in_process", "self_http")
            if k in channels or (isinstance(src, dict) and k in src)
        }
        if extras:
            print("META", extras)
        # also scan nested
        if isinstance(src, dict):
            meta = {
                k: src.get(k)
                for k in ("google_key_present", "google_key_env_name")
                if k in src
            }
            if meta:
                print("META2", meta)


if __name__ == "__main__":
    key = fusarium_key()
    if not key:
        print("NO_FUSARIUM_KEY")
    else:
        probe(key)
    situation()
