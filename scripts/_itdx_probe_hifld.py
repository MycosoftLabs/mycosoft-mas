"""Probe alternate public HIFLD / Esri military-base layers."""

from __future__ import annotations

import urllib.request

UA = {"User-Agent": "Mycosoft-MAS-ITDX/1.0 (public-osint; https://mycosoft.com)"}

URLS = (
    "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/USA_Military_Bases/FeatureServer/0/query?where=NAME%20LIKE%20%27%25Stewart%25%27&outFields=NAME,COMPONENT,STATE&f=json&resultRecordCount=5",
    "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/USA_Military_Installations_Ranges_and_Training_Areas/FeatureServer/0/query?where=SITE_NAME%20LIKE%20%27%25Stewart%25%27&outFields=SITE_NAME,COMPONENT,STATE_TERR&f=json&resultRecordCount=5",
    "http://192.168.0.189:8000/v1/taxa?limit=1",
    "http://192.168.0.189:8000/api/taxa?limit=1",
    "http://192.168.0.189:8000/unified-search?q=Fusarium",
    "http://192.168.0.189:8000/earth/search?q=Fort%20Stewart",
)


def main() -> None:
    for url in URLS:
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                body = response.read(240)
                print("OK", response.status, url[:140])
                print("  ", body[:200].replace(b"\n", b" "))
        except Exception as exc:  # noqa: BLE001
            print("ERR", url[:140], type(exc).__name__, str(exc)[:160])


if __name__ == "__main__":
    main()
