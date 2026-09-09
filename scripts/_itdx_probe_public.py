"""Probe public OSINT endpoints used by ITDX. No secrets printed."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mycosoft-MAS-ITDX/1.0 (public-osint; https://mycosoft.com)"}


def get(url: str, timeout: float = 8.0) -> None:
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read(220)
            print("OK", response.status, url[:120], body[:160].replace(b"\n", b" "))
    except Exception as exc:  # noqa: BLE001 — probe
        print("ERR", url[:120], type(exc).__name__, str(exc)[:160])


def main() -> None:
    query = (
        '[out:json][timeout:8];'
        '(way["landuse"="military"](31.80,-81.70,32.05,-81.45);'
        'relation["landuse"="military"](31.80,-81.70,32.05,-81.45);'
        'way["aeroway"="aerodrome"](31.80,-81.70,32.05,-81.45);'
        'way["highway"](31.80,-81.70,32.05,-81.45););'
        "out tags center 6;"
    )
    get("https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query))
    get("https://nominatim.openstreetmap.org/search?q=Hunter+Army+Airfield&format=json&limit=1")
    get("https://nominatim.openstreetmap.org/search?q=Hinesville+Georgia&format=json&limit=1")
    get(
        "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/"
        "Military_Bases/FeatureServer/0/query?where=SITE_NAME%20LIKE%20%27%25STEWART%25%27"
        "&outFields=SITE_NAME,SITE_TYPE,COMPONENT,STATE_TERR&f=json&resultRecordCount=5"
    )
    get("https://home.army.mil/stewart/")
    get("http://192.168.0.189:8000/taxa?limit=1")
    get("http://192.168.0.189:8000/observations?limit=1")
    get("http://127.0.0.1:8003/health")
    get("http://192.168.0.188:8001/api/itdx/health")


if __name__ == "__main__":
    main()
