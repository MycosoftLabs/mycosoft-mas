"""Retest Google Directions + Distance Matrix after billing reopen. Never print keys."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

AIZA_RE = re.compile(r"AIza[0-9A-Za-z_-]{10,}")
ORIGIN = "31.8697,-81.6072"
HUNTER = "Hunter Army Airfield, Savannah, GA"
HINESVILLE = "Hinesville, GA"
CANDIDATES = (
    "GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY",
    "GOOGLE_API_KEY",
)


def redact(text: str) -> str:
    return AIZA_RE.sub("AIza***", text or "")


def load_key() -> tuple[str, str]:
    files = (
        Path(__file__).resolve().parents[1] / ".credentials.local",
        Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local"),
    )
    for path in files:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            if name in CANDIDATES and value:
                return name, value
    return "", ""


def probe(label: str, url: str, params: dict[str, str]) -> dict[str, str]:
    req = urllib.request.Request(
        url + "?" + urllib.parse.urlencode(params),
        headers={"User-Agent": "Mycosoft-MAS-ITDX/1.0 (public-osint)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8", "replace"))
            http_code = response.status
    except urllib.error.HTTPError as exc:
        raw = redact(exc.read().decode("utf-8", "replace"))[:240]
        return {"label": label, "http": str(exc.code), "status": "HTTP_ERROR", "detail": raw}
    except Exception as exc:  # noqa: BLE001
        return {"label": label, "http": "0", "status": "HTTP_ERROR", "detail": type(exc).__name__}
    status = str(body.get("status", "UNKNOWN"))
    err = redact(str(body.get("error_message") or ""))
    extra = ""
    if status == "OK":
        if isinstance(body.get("routes"), list):
            extra = f"routes={len(body['routes'])}"
            traffic = False
            for route in body.get("routes") or []:
                if not isinstance(route, dict):
                    continue
                for leg in route.get("legs") or []:
                    if isinstance(leg, dict) and isinstance(leg.get("duration_in_traffic"), dict):
                        traffic = True
            extra += f" duration_in_traffic={traffic}"
        if isinstance(body.get("rows"), list):
            els = ((body.get("rows") or [{}])[0].get("elements") or [])
            extra = "elements=" + ",".join(str(e.get("status")) for e in els if isinstance(e, dict))
            extra += " duration_in_traffic=" + str(
                any(
                    isinstance(e, dict) and isinstance(e.get("duration_in_traffic"), dict)
                    for e in els
                )
            )
    return {
        "label": label,
        "http": str(http_code),
        "status": status,
        "detail": err,
        "extra": extra,
    }


def main() -> int:
    name, key = load_key()
    print("KEY_NAME", name or "MISSING", "LEN", len(key), "PREFIX", (key[:4] if key else "NONE"))
    if not key:
        print("NO_KEY")
        return 2
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
            "directions_hinesville",
            "https://maps.googleapis.com/maps/api/directions/json",
            {
                "origin": ORIGIN,
                "destination": HINESVILLE,
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
    denied = False
    ok = True
    for label, url, params in checks:
        result = probe(label, url, params)
        print(
            "PROBE",
            result["label"],
            "HTTP",
            result["http"],
            result["status"],
            "|",
            result.get("detail") or "",
            "|",
            result.get("extra") or "",
        )
        if result["status"] == "REQUEST_DENIED":
            denied = True
            ok = False
        elif result["status"] != "OK":
            ok = False
    print("SUMMARY", "OK" if ok else ("REQUEST_DENIED" if denied else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
