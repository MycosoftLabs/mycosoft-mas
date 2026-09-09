"""Local smoke of public OSINT gather. No secrets printed."""

from __future__ import annotations

import asyncio
import json

from mycosoft_mas.core.routers.itdx_public_sources import gather_public_osint


async def main() -> None:
    ao = {
        "name": "Fort Stewart",
        "bbox": [-81.70, 31.80, -81.45, 32.05],
        "center": {"lat": 31.8697, "lon": -81.6072},
    }
    data = await gather_public_osint(ao)
    summary = {
        "google_key_present": data.get("google_key_present"),
        "google_key_env_name": data.get("google_key_env_name"),
        "open_meteo_ok": (data.get("open_meteo") or {}).get("ok"),
        "open_meteo_error": (data.get("open_meteo") or {}).get("error"),
        "gbif_ok": (data.get("gbif") or {}).get("ok"),
        "gbif_error": (data.get("gbif") or {}).get("error"),
        "gbif_count": (data.get("gbif") or {}).get("count"),
        "inat_ok": (data.get("inaturalist") or {}).get("ok"),
        "inat_total": (data.get("inaturalist") or {}).get("total"),
        "osm_ok": (data.get("osm_military") or {}).get("ok"),
        "nominatim_ok": (data.get("nominatim") or {}).get("ok"),
        "wiki_ok": (data.get("wikipedia") or {}).get("ok"),
        "nws_ok": (data.get("nws") or {}).get("ok"),
        "pubchem_ok": (data.get("pubchem") or {}).get("ok"),
        "directions_ok": (data.get("google_directions") or {}).get("ok"),
        "directions_error": (data.get("google_directions") or {}).get("error"),
        "geojson_features": len((data.get("geojson") or {}).get("features") or []),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
