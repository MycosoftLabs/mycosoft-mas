"""ITDX public + MINDEX probes for situation-assessment.

UNCLASSIFIED commercial OSINT only. No FOUO/CUI, no Army inject PDFs,
no MGRS derived from those packs. Official 1–5 rubric stays NOT_SUPPLIED.

Callers use these in-process. Never HTTP-loop to MAS :8001.

Public weather point (declared): 31.8697, -81.6072.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

MINDEX_URL = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
GBIF_OCCURRENCE_URL = "https://api.gbif.org/v1/occurrence/search"
GBIF_SPECIES_MATCH_URL = "https://api.gbif.org/v1/species/match"
USGS_QUAKES_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
INAT_OBS_URL = "https://api.inaturalist.org/v1/observations"
OVERPASS_URL = os.getenv("OSM_OVERPASS_URL", "https://overpass-api.de/api/interpreter")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HIFLD_QUERY_URL = os.getenv(
    "HIFLD_MILITARY_QUERY_URL",
    "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/"
    "Military_Installations_National/FeatureServer/0/query",
)

PUBLIC_WEATHER_LAT = 31.8697
PUBLIC_WEATHER_LON = -81.6072
USER_AGENT = "Mycosoft-ITDX/1.0 (unclassified commercial exercise; +https://mycosoft.com)"
PROBE_S = 2.0
GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
GOOGLE_DISTANCE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
GOOGLE_PLACES_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
NWS_POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
OPENSKY_URL = "https://opensky-network.org/api/states/all"
PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/fusaric%20acid/property/Title,MolecularFormula,IUPACName/JSON"
MYCOBRAIN_HEALTH = os.getenv("MYCOBRAIN_HEALTH_URL", "http://127.0.0.1:8003/health")
HUNTER_AAF_PUBLIC_NAME = "Hunter Army Airfield, Savannah, GA"
FORT_STEWART_PUBLIC_NAME = "Fort Stewart, Georgia, USA"
HINESVILLE_PUBLIC_NAME = "Hinesville, Georgia, USA"
GOOGLE_KEY_NAMES = (
    "GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_MAPS_KEY",
    "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _scan_env_files() -> Dict[str, str]:
    """Read gitignored env files. Values are never logged."""
    roots = [
        Path(__file__).resolve().parents[3],
        Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"),
        Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13"),
        Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex"),
    ]
    out: Dict[str, str] = {}
    for root in roots:
        for name in (".credentials.local", ".env", ".env.local"):
            path = root / name
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                if not line or line.lstrip().startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value and key not in out:
                    out[key] = value
    return out


def _bbox(ao: Dict[str, Any]) -> Tuple[float, float, float, float]:
    bbox = ao.get("bbox") if isinstance(ao.get("bbox"), list) else None
    if bbox and len(bbox) == 4:
        return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    return -81.70, 31.80, -81.45, 32.05


def _center(ao: Dict[str, Any]) -> Tuple[float, float]:
    center = ao.get("center")
    if isinstance(center, dict) and center.get("lat") is not None:
        return float(center["lat"]), float(center.get("lon") or center.get("lng") or PUBLIC_WEATHER_LON)
    if isinstance(center, (list, tuple)) and len(center) >= 2:
        return float(center[0]), float(center[1])
    return PUBLIC_WEATHER_LAT, PUBLIC_WEATHER_LON


def _mindex_headers() -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    secret = (os.getenv("MINDEX_INTERNAL_SECRET") or "").strip()
    token = ""
    if secret:
        try:
            from mycosoft_mas.integrations.mqtt_mycobrain_bridge import _mindex_hmac_token

            svc = (os.getenv("MINDEX_INTERNAL_SERVICE_NAME") or "mas-orchestrator").strip()
            token = _mindex_hmac_token(svc, secret)
        except Exception:
            token = ""
    if not token:
        token = (
            os.getenv("MINDEX_INTERNAL_TOKEN")
            or (os.getenv("MINDEX_INTERNAL_TOKENS") or "").split(",")[0]
            or ""
        ).strip()
    if token:
        headers["X-Internal-Token"] = token
    api_key = (os.getenv("MINDEX_API_KEY") or "").strip()
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


async def _get_json(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = PROBE_S,
) -> Dict[str, Any]:
    hdrs = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, params=params, headers=hdrs)
            try:
                body = response.json()
            except Exception:
                body = {"raw": (response.text or "")[:240]}
            return {
                "ok": response.is_success,
                "status_code": response.status_code,
                "url": str(response.url),
                "data": body,
            }
    except Exception as exc:
        return {"ok": False, "status_code": 0, "url": url, "error": str(exc), "data": {}}


async def fetch_mindex_slice(ao: Dict[str, Any]) -> Dict[str, Any]:
    """MINDEX first. Empty/401/down is honest — callers fall back to public APIs."""
    health = await _get_json(f"{MINDEX_URL}/health")
    headers = _mindex_headers()
    west, south, east, north = _bbox(ao)
    taxa = await _get_json(
        f"{MINDEX_URL}/api/mindex/taxa",
        params={
            "q": "Fusarium",
            "kingdom": "Fungi",
            "limit": 8,
            "min_lat": south,
            "max_lat": north,
            "min_lon": west,
            "max_lon": east,
        },
        headers=headers,
        timeout=1.6,
    )
    observations = await _get_json(
        f"{MINDEX_URL}/api/mindex/observations",
        params={"q": "Fusarium", "limit": 8, "min_lat": south, "max_lat": north, "min_lon": west, "max_lon": east},
        headers=headers,
        timeout=1.6,
    )
    def _rows(payload: Any, keys: tuple[str, ...]) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if not isinstance(payload, dict):
            return []
        out: List[Dict[str, Any]] = []
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                out.extend(row for row in value if isinstance(row, dict))
        return out

    taxa_rows = _rows(taxa.get("data"), ("data", "items", "species", "taxa"))
    obs_rows = _rows(observations.get("data"), ("data", "items", "observations"))
    has_taxa = bool(taxa.get("ok") and taxa_rows)
    has_obs = bool(observations.get("ok") and obs_rows)
    note = "MINDEX /api/mindex/taxa + /observations cheap Fusarium slice."
    if not taxa.get("ok") and not observations.get("ok"):
        note = (
            f"MINDEX slice routes returned "
            f"taxa={taxa.get('status_code')} observations={observations.get('status_code')}. "
            "GBIF/iNat used instead."
        )
    return {
        "source": "mindex",
        "base": MINDEX_URL,
        "health": health,
        "stats": {},
        "taxa": {"status_code": taxa.get("status_code"), "count": len(taxa_rows)},
        "observations": {"status_code": observations.get("status_code"), "count": len(obs_rows)},
        "compounds": {},
        "has_taxa": has_taxa,
        "has_observations": has_obs,
        "has_compounds": False,
        "note": note,
    }


async def fetch_open_meteo(ao: Dict[str, Any]) -> Dict[str, Any]:
    """Public weather at the declared Fort Stewart point. Not Earth-2."""
    lat, lon = PUBLIC_WEATHER_LAT, PUBLIC_WEATHER_LON
    _c_lat, _c_lon = _center(ao)
    probe = await _get_json(
        OPEN_METEO_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "timezone": "UTC",
        },
    )
    current = {}
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    if isinstance(data.get("current"), dict):
        current = data["current"]
    return {
        "ok": bool(probe.get("ok") and current),
        "source": "open-meteo",
        "citation": OPEN_METEO_URL,
        "url": probe.get("url"),
        "lat": lat,
        "lon": lon,
        "current": current,
        "error": None if probe.get("ok") and current else (probe.get("error") or "no current weather"),
        "note": "Public Open-Meteo at declared Fort Stewart point. Earth-2 249 not required.",
    }


async def fetch_gbif_occurrences(ao: Dict[str, Any]) -> Dict[str, Any]:
    west, south, east, north = _bbox(ao)
    probe = await _get_json(
        GBIF_OCCURRENCE_URL,
        params={
            "decimalLongitude": f"{west},{east}",
            "decimalLatitude": f"{south},{north}",
            "kingdomKey": 5,
            "hasCoordinate": "true",
            "limit": 8,
        },
    )
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    results = data.get("results") if isinstance(data.get("results"), list) else []
    count = data.get("count")
    excerpt = []
    for row in results[:5]:
        if not isinstance(row, dict):
            continue
        excerpt.append(
            {
                "scientificName": row.get("scientificName") or row.get("species"),
                "eventDate": row.get("eventDate"),
                "decimalLatitude": row.get("decimalLatitude"),
                "decimalLongitude": row.get("decimalLongitude"),
                "datasetKey": row.get("datasetKey"),
            }
        )
    return {
        "ok": bool(probe.get("ok") and (excerpt or count)),
        "source": "gbif",
        "citation": "https://api.gbif.org/v1/occurrence/search",
        "url": probe.get("url"),
        "count": count,
        "returned": len(results),
        "excerpt": excerpt,
        "error": None if probe.get("ok") else probe.get("error"),
    }


async def fetch_inaturalist(ao: Dict[str, Any]) -> Dict[str, Any]:
    west, south, east, north = _bbox(ao)
    probe = await _get_json(
        INAT_OBS_URL,
        params={
            "swlng": west,
            "swlat": south,
            "nelng": east,
            "nelat": north,
            "iconic_taxa": "Fungi",
            "per_page": 5,
            "order_by": "observed_on",
        },
    )
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    results = data.get("results") if isinstance(data.get("results"), list) else []
    excerpt = []
    for row in results[:5]:
        if not isinstance(row, dict):
            continue
        taxon = row.get("taxon") if isinstance(row.get("taxon"), dict) else {}
        excerpt.append(
            {
                "id": row.get("id"),
                "name": taxon.get("name") or taxon.get("preferred_common_name"),
                "observed_on": row.get("observed_on"),
                "uri": row.get("uri"),
            }
        )
    return {
        "ok": bool(probe.get("ok") and excerpt),
        "source": "inaturalist",
        "citation": "https://api.inaturalist.org/v1/observations",
        "url": probe.get("url"),
        "total": data.get("total_results"),
        "excerpt": excerpt,
        "error": None if probe.get("ok") else probe.get("error"),
    }


async def fetch_osm_military(ao: Dict[str, Any]) -> Dict[str, Any]:
    west, south, east, north = _bbox(ao)
    query = (
        f"[out:json][timeout:8];"
        f"("
        f'way["landuse"="military"]({south},{west},{north},{east});'
        f'relation["landuse"="military"]({south},{west},{north},{east});'
        f'way["military"]({south},{west},{north},{east});'
        f'relation["aeroway"="aerodrome"]["name"~"Hunter",i]({south-0.4},{west-0.6},{north+0.4},{east+0.6});'
        f");"
        f"out tags center 12;"
    )
    try:
        async with httpx.AsyncClient(timeout=PROBE_S, follow_redirects=True) as client:
            response = await client.post(
                OVERPASS_URL,
                data={"data": query},
                headers={"User-Agent": USER_AGENT},
            )
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            elements = body.get("elements") if isinstance(body, dict) else []
            if not isinstance(elements, list):
                elements = []
            places = []
            for el in elements[:12]:
                tags = el.get("tags") if isinstance(el.get("tags"), dict) else {}
                name = tags.get("name") or tags.get("official_name")
                if not name and not tags.get("landuse"):
                    continue
                places.append(
                    {
                        "id": el.get("id"),
                        "name": name,
                        "landuse": tags.get("landuse"),
                        "military": tags.get("military"),
                        "aeroway": tags.get("aeroway"),
                    }
                )
            return {
                "ok": bool(response.is_success and places),
                "source": "osm-overpass",
                "citation": OVERPASS_URL,
                "count": len(places),
                "places": places,
                "error": None if response.is_success else f"HTTP {response.status_code}",
            }
    except Exception as exc:
        return {"ok": False, "source": "osm-overpass", "citation": OVERPASS_URL, "error": str(exc), "places": []}


async def fetch_hifld_military(ao: Dict[str, Any]) -> Dict[str, Any]:
    """HIFLD Open military installations (public ArcGIS). Fail closed if the layer is gone."""
    west, south, east, north = _bbox(ao)
    probe = await _get_json(
        HIFLD_QUERY_URL,
        params={
            "where": "1=1",
            "geometry": f"{west},{south},{east},{north}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "SITE_NAME,COMPONENT,OPER_STAT,STATE_TERR,INSTALLATI",
            "returnGeometry": "false",
            "f": "json",
            "resultRecordCount": 8,
        },
    )
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    features = data.get("features") if isinstance(data.get("features"), list) else []
    sites = []
    for feat in features[:8]:
        attrs = feat.get("attributes") if isinstance(feat, dict) else None
        if not isinstance(attrs, dict):
            continue
        name = attrs.get("SITE_NAME") or attrs.get("INSTALLATI") or attrs.get("Name")
        if name:
            sites.append({k: attrs.get(k) for k in ("SITE_NAME", "COMPONENT", "OPER_STAT", "STATE_TERR") if attrs.get(k)})
    return {
        "ok": bool(probe.get("ok") and sites),
        "source": "hifld-open",
        "citation": HIFLD_QUERY_URL,
        "url": probe.get("url"),
        "sites": sites,
        "error": None
        if probe.get("ok")
        else (probe.get("error") or data.get("error") or f"HTTP {probe.get('status_code')}"),
        "note": "HIFLD Open / public ArcGIS only. Not FOUO. Not a weapons score.",
    }


async def fetch_nominatim_places() -> Dict[str, Any]:
    """Public OSM Nominatim names only — Fort Stewart, Hunter AAF, Hinesville."""
    import asyncio

    queries = (
        "Fort Stewart, Georgia, USA",
        "Hunter Army Airfield, Georgia, USA",
    )
    probes = await asyncio.gather(
        *[
            _get_json(NOMINATIM_URL, params={"q": q, "format": "json", "limit": 1})
            for q in queries
        ],
        return_exceptions=True,
    )
    out: List[Dict[str, Any]] = []
    errors: List[str] = []
    for q, probe in zip(queries, probes):
        if isinstance(probe, Exception):
            errors.append(f"{q}: {probe}")
            continue
        rows = probe.get("data") if isinstance(probe.get("data"), list) else []
        if probe.get("ok") and rows:
            row = rows[0] if isinstance(rows[0], dict) else {}
            out.append(
                {
                    "query": q,
                    "display_name": row.get("display_name"),
                    "lat": row.get("lat"),
                    "lon": row.get("lon"),
                    "osm_type": row.get("osm_type"),
                    "osm_id": row.get("osm_id"),
                    "citation": NOMINATIM_URL,
                }
            )
        else:
            errors.append(f"{q}: {probe.get('error') or probe.get('status_code')}")
    return {
        "ok": bool(out),
        "source": "nominatim",
        "citation": NOMINATIM_URL,
        "places": out,
        "error": "; ".join(errors) if errors and not out else None,
        "note": "Public geocode / OSM names. Not MGRS from Army PDFs.",
    }


def _row_count(probe: Dict[str, Any]) -> int:
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    for key in ("items", "data", "results", "compounds", "observations", "taxa"):
        rows = data.get(key)
        if isinstance(rows, list):
            return len(rows)
    if isinstance(data.get("total"), int) and data.get("total", 0) > 0:
        return int(data["total"])
    return 0


async def _gather_named(mapping: Dict[str, Any]) -> Tuple[Dict[str, Any], ...]:
    import asyncio

    keys = list(mapping.keys())
    values = await asyncio.gather(*mapping.values(), return_exceptions=True)
    out: List[Dict[str, Any]] = []
    for key, value in zip(keys, values):
        if isinstance(value, Exception):
            out.append({"ok": False, "error": str(value), "data": {}})
        elif isinstance(value, dict):
            out.append(value)
        else:
            out.append({"ok": False, "error": f"bad {key}", "data": {}})
    return tuple(out)


def _google_maps_key() -> str:
    """Read Google Directions-capable key from env or gitignored files. Never log it."""
    files = _scan_env_files()
    for name in GOOGLE_KEY_NAMES:
        value = (os.getenv(name) or files.get(name) or "").strip()
        if value:
            return value
    return ""


def _google_key_name() -> Optional[str]:
    files = _scan_env_files()
    for name in GOOGLE_KEY_NAMES:
        if (os.getenv(name) or files.get(name) or "").strip():
            return name
    return None


def _redact_url(url: str) -> str:
    import re

    return re.sub(r"(key=)[^&]+", r"\1REDACTED", url or "", flags=re.IGNORECASE)


def _google_key_present() -> bool:
    return bool(_google_maps_key())


def _decode_polyline(encoded: str) -> List[List[float]]:
    """Google encoded polyline → [[lon, lat], ...] for GeoJSON. Official algorithm only."""
    coords: List[List[float]] = []
    index = 0
    lat = 0
    lon = 0
    length = len(encoded or "")
    while index < length:
        result = 1
        shift = 0
        while True:
            b = ord(encoded[index]) - 63 - 1
            index += 1
            result += b << shift
            shift += 5
            if b < 0x1F:
                break
        lat += ~(result >> 1) if result & 1 else (result >> 1)
        result = 1
        shift = 0
        while True:
            b = ord(encoded[index]) - 63 - 1
            index += 1
            result += b << shift
            shift += 5
            if b < 0x1F:
                break
        lon += ~(result >> 1) if result & 1 else (result >> 1)
        coords.append([lon / 1e5, lat / 1e5])
    return coords


def _route_from_google(route: Dict[str, Any], destination: str) -> Dict[str, Any]:
    legs = route.get("legs") if isinstance(route.get("legs"), list) else []
    first = legs[0] if legs and isinstance(legs[0], dict) else {}
    duration = first.get("duration") if isinstance(first.get("duration"), dict) else {}
    traffic = (
        first.get("duration_in_traffic")
        if isinstance(first.get("duration_in_traffic"), dict)
        else {}
    )
    distance = first.get("distance") if isinstance(first.get("distance"), dict) else {}
    overview = route.get("overview_polyline") if isinstance(route.get("overview_polyline"), dict) else {}
    encoded = str(overview.get("points") or "")
    return {
        "summary": route.get("summary"),
        "destination": destination,
        "travel_mode": "driving",
        "warnings": route.get("warnings") or [],
        "distance_text": distance.get("text"),
        "duration_text": duration.get("text"),
        "duration_in_traffic_text": traffic.get("text"),
        "duration_in_traffic_s": traffic.get("value"),
        "start": first.get("start_address"),
        "end": first.get("end_address"),
        "polyline": encoded or None,
        "retrieved_at": _utc_now(),
    }


async def fetch_google_directions(ao: Dict[str, Any]) -> Dict[str, Any]:
    """Public-road pathways via Directions + live traffic duration. No FOUO routes."""
    import asyncio

    _ = ao
    key = _google_maps_key()
    if not key:
        return {
            "ok": False,
            "source": "google-directions",
            "key_present": False,
            "error": "GOOGLE_MAPS_API_KEY unset",
            "reason": "google_maps_key_missing",
            "routes": [],
        }
    origin = f"{PUBLIC_WEATHER_LAT},{PUBLIC_WEATHER_LON}"
    destinations = (HUNTER_AAF_PUBLIC_NAME, HINESVILLE_PUBLIC_NAME)
    probes = await asyncio.gather(
        *[
            _get_json(
                GOOGLE_DIRECTIONS_URL,
                params={
                    "origin": origin,
                    "destination": dest,
                    "mode": "driving",
                    "alternatives": "false",
                    "departure_time": "now",
                    "traffic_model": "best_guess",
                    "key": key,
                },
            )
            for dest in destinations
        ],
        return_exceptions=True,
    )
    routes_out: List[Dict[str, Any]] = []
    last_status = None
    last_error = None
    last_url = ""
    for dest, probe in zip(destinations, probes):
        if isinstance(probe, Exception):
            last_error = str(probe)
            continue
        data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
        last_status = data.get("status")
        last_url = _redact_url(str(probe.get("url") or ""))
        if last_status != "OK":
            last_error = data.get("error_message") or last_status or probe.get("error")
            continue
        for route in data.get("routes") or []:
            if isinstance(route, dict):
                routes_out.append(_route_from_google(route, dest))
    return {
        "ok": bool(routes_out),
        "source": "google-directions",
        "citation": "https://maps.googleapis.com/maps/api/directions/json",
        "url": last_url,
        "key_present": True,
        "google_status": last_status if routes_out else last_status,
        "origin": origin,
        "destinations": list(destinations),
        "routes": routes_out,
        "retrieved_at": _utc_now(),
        "error": None if routes_out else last_error,
        "note": "Public driving routes + live traffic duration. Cited Google. Not a military MGRS inject.",
    }


async def fetch_google_traffic(ao: Dict[str, Any]) -> Dict[str, Any]:
    """Distance Matrix duration_in_traffic at the declared public point."""
    key = _google_maps_key()
    if not key:
        return {
            "ok": False,
            "source": "google-traffic",
            "key_present": False,
            "error": "GOOGLE_MAPS_API_KEY unset",
            "reason": "google_maps_key_missing",
        }
    origin = f"{PUBLIC_WEATHER_LAT},{PUBLIC_WEATHER_LON}"
    destinations = (HUNTER_AAF_PUBLIC_NAME, HINESVILLE_PUBLIC_NAME)
    probe = await _get_json(
        GOOGLE_DISTANCE_URL,
        params={
            "origins": origin,
            "destinations": "|".join(destinations),
            "mode": "driving",
            "departure_time": "now",
            "traffic_model": "best_guess",
            "key": key,
        },
    )
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    rows = data.get("rows") if isinstance(data.get("rows"), list) else []
    elements: List[Dict[str, Any]] = []
    if rows and isinstance(rows[0], dict):
        raw = rows[0].get("elements") if isinstance(rows[0].get("elements"), list) else []
        for dest, el in zip(destinations, raw):
            if not isinstance(el, dict):
                continue
            traffic = el.get("duration_in_traffic") if isinstance(el.get("duration_in_traffic"), dict) else {}
            duration = el.get("duration") if isinstance(el.get("duration"), dict) else {}
            distance = el.get("distance") if isinstance(el.get("distance"), dict) else {}
            elements.append(
                {
                    "destination": dest,
                    "status": el.get("status"),
                    "travel_mode": "driving",
                    "distance_text": distance.get("text"),
                    "duration_text": duration.get("text"),
                    "duration_in_traffic_text": traffic.get("text"),
                    "duration_in_traffic_s": traffic.get("value"),
                }
            )
    first = elements[0] if elements else {}
    return {
        "ok": bool(probe.get("ok") and data.get("status") == "OK" and any(e.get("status") == "OK" for e in elements)),
        "source": "google-traffic",
        "citation": "https://maps.googleapis.com/maps/api/distancematrix/json",
        "url": _redact_url(str(probe.get("url") or "")),
        "key_present": True,
        "google_status": data.get("status"),
        "element_status": first.get("status"),
        "origin": origin,
        "destinations": list(destinations),
        "etas": elements,
        "duration_text": first.get("duration_text"),
        "duration_in_traffic_text": first.get("duration_in_traffic_text"),
        "duration_in_traffic_s": first.get("duration_in_traffic_s"),
        "retrieved_at": _utc_now(),
        "error": None
        if any(e.get("status") == "OK" for e in elements)
        else (data.get("error_message") or first.get("status") or probe.get("error")),
        "note": "Live public-road traffic duration only. Cited Google. Not a weapons or officer score.",
    }


async def fetch_google_places_bases() -> Dict[str, Any]:
    """Public Places names for Fort Stewart / Hunter AAF. Not FOUO base data."""
    key = _google_maps_key()
    if not key:
        return {
            "ok": False,
            "source": "google-places",
            "key_present": False,
            "error": "GOOGLE_MAPS_API_KEY unset",
            "places": [],
        }
    places: List[Dict[str, Any]] = []
    errors: List[str] = []
    for query in (FORT_STEWART_PUBLIC_NAME, HUNTER_AAF_PUBLIC_NAME):
        probe = await _get_json(
            GOOGLE_PLACES_URL,
            params={"query": query, "key": key},
        )
        data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
        results = data.get("results") if isinstance(data.get("results"), list) else []
        if probe.get("ok") and data.get("status") in {"OK", "ZERO_RESULTS"} and results:
            row = results[0] if isinstance(results[0], dict) else {}
            loc = row.get("geometry", {}).get("location") if isinstance(row.get("geometry"), dict) else {}
            places.append(
                {
                    "query": query,
                    "name": row.get("name"),
                    "formatted_address": row.get("formatted_address"),
                    "place_id": row.get("place_id"),
                    "types": row.get("types") or [],
                    "lat": loc.get("lat") if isinstance(loc, dict) else None,
                    "lng": loc.get("lng") if isinstance(loc, dict) else None,
                }
            )
        else:
            errors.append(str(data.get("status") or probe.get("error") or "places miss"))
    return {
        "ok": bool(places),
        "source": "google-places",
        "citation": "https://maps.googleapis.com/maps/api/place/textsearch/json",
        "key_present": True,
        "places": places,
        "error": "; ".join(errors) if errors and not places else None,
        "note": "Public Google Places names only. No FOUO, no CUI, no MGRS from Army PDFs.",
    }


async def fetch_osm_road_limits(ao: Dict[str, Any]) -> Dict[str, Any]:
    """Public OSM maxspeed / height / weight / hazmat on civilian roads."""
    west, south, east, north = _bbox(ao)
    query = (
        f"[out:json][timeout:8];"
        f"("
        f'way["highway"~"motorway|trunk|primary|secondary|tertiary"]["maxspeed"]({south},{west},{north},{east});'
        f'way["maxheight"]({south},{west},{north},{east});'
        f'way["maxweight"]({south},{west},{north},{east});'
        f'way["hazmat"]({south},{west},{north},{east});'
        f");"
        f"out tags 20;"
    )
    try:
        async with httpx.AsyncClient(timeout=PROBE_S, follow_redirects=True) as client:
            response = await client.post(
                OVERPASS_URL,
                data={"data": query},
                headers={"User-Agent": USER_AGENT},
            )
            body = response.json() if "json" in (response.headers.get("content-type") or "") else {}
            elements = body.get("elements") if isinstance(body, dict) else []
            if not isinstance(elements, list):
                elements = []
            limits: List[Dict[str, Any]] = []
            for el in elements[:20]:
                tags = el.get("tags") if isinstance(el.get("tags"), dict) else {}
                if not any(tags.get(k) for k in ("maxspeed", "maxheight", "maxweight", "hazmat")):
                    continue
                limits.append(
                    {
                        "id": el.get("id"),
                        "name": tags.get("name") or tags.get("ref"),
                        "highway": tags.get("highway"),
                        "maxspeed": tags.get("maxspeed"),
                        "maxheight": tags.get("maxheight"),
                        "maxweight": tags.get("maxweight"),
                        "hazmat": tags.get("hazmat"),
                    }
                )
            return {
                "ok": bool(response.is_success and limits),
                "source": "osm-road-limits",
                "citation": OVERPASS_URL,
                "count": len(limits),
                "limits": limits,
                "error": None if response.is_success else f"HTTP {response.status_code}",
                "note": "Public OSM civilian road limits. Not a military vehicle class p.",
            }
    except Exception as exc:
        return {
            "ok": False,
            "source": "osm-road-limits",
            "citation": OVERPASS_URL,
            "error": str(exc),
            "limits": [],
        }


async def fetch_nws_forecast(ao: Dict[str, Any]) -> Dict[str, Any]:
    lat, lon = PUBLIC_WEATHER_LAT, PUBLIC_WEATHER_LON
    probe = await _get_json(NWS_POINTS_URL.format(lat=lat, lon=lon))
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    props = data.get("properties") if isinstance(data.get("properties"), dict) else {}
    periods: List[Dict[str, Any]] = []
    # Skip the second NWS hop so the 5s assessment budget stays intact.
    return {
        "ok": bool(probe.get("ok") and props),
        "source": "nws",
        "citation": NWS_POINTS_URL.format(lat=lat, lon=lon),
        "retrieved_at": _utc_now(),
        "cwa": props.get("cwa"),
        "periods": periods,
        "error": None if probe.get("ok") else probe.get("error"),
    }


async def fetch_wikipedia_bases() -> Dict[str, Any]:
    import asyncio

    titles = ("Fort_Stewart", "Hunter_Army_Airfield")
    probes = await asyncio.gather(
        *[_get_json(WIKI_SUMMARY_URL.format(title=title)) for title in titles],
        return_exceptions=True,
    )
    pages = []
    for title, probe in zip(titles, probes):
        if isinstance(probe, Exception) or not isinstance(probe, dict):
            continue
        data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
        extract = data.get("extract")
        if probe.get("ok") and extract:
            coords = data.get("coordinates") if isinstance(data.get("coordinates"), dict) else {}
            pages.append(
                {
                    "title": data.get("title") or title,
                    "extract": str(extract)[:500],
                    "url": ((data.get("content_urls") or {}).get("desktop") or {}).get("page"),
                    "lat": coords.get("lat"),
                    "lon": coords.get("lon"),
                    "citation": WIKI_SUMMARY_URL.format(title=title),
                    "retrieved_at": _utc_now(),
                }
            )
    return {
        "ok": bool(pages),
        "source": "wikipedia",
        "citation": "https://en.wikipedia.org/api/rest_v1/page/summary/",
        "retrieved_at": _utc_now(),
        "pages": pages,
        "error": None if pages else "wikipedia_empty",
    }


async def fetch_opensky(ao: Dict[str, Any]) -> Dict[str, Any]:
    west, south, east, north = _bbox(ao)
    probe = await _get_json(
        OPENSKY_URL,
        params={"lamin": south, "lomin": west, "lamax": north, "lomax": east},
    )
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    states = data.get("states")
    count = len(states) if isinstance(states, list) else 0
    return {
        "ok": bool(probe.get("ok") and count > 0),
        "source": "opensky",
        "citation": OPENSKY_URL,
        "retrieved_at": _utc_now(),
        "count": count,
        "live_cop": False,
        "error": None if probe.get("ok") and count else (probe.get("error") or "empty"),
        "note": "Public ADS-B only. Empty bbox is not invented tracks.",
    }


async def fetch_pubchem_fusaric() -> Dict[str, Any]:
    probe = await _get_json(PUBCHEM_URL)
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    props = ((data.get("PropertyTable") or {}).get("Properties")) if isinstance(data.get("PropertyTable"), dict) else []
    if not isinstance(props, list):
        props = []
    return {
        "ok": bool(probe.get("ok") and props),
        "source": "pubchem",
        "citation": PUBCHEM_URL,
        "retrieved_at": _utc_now(),
        "properties": props[:3],
        "error": None if props else (probe.get("error") or "empty"),
        "note": "Public PubChem fusaric acid. Not an NLM chemistry p.",
    }


async def fetch_gbif_species_match() -> Dict[str, Any]:
    """Public GBIF backbone match for Fusarium oxysporum. Not a biology p."""
    probe = await _get_json(
        GBIF_SPECIES_MATCH_URL,
        params={"name": "Fusarium oxysporum", "kingdom": "Fungi"},
    )
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    usage_key = data.get("usageKey")
    return {
        "ok": bool(probe.get("ok") and usage_key),
        "source": "gbif-species-match",
        "citation": GBIF_SPECIES_MATCH_URL,
        "retrieved_at": _utc_now(),
        "scientificName": data.get("scientificName"),
        "usageKey": usage_key,
        "status": data.get("status"),
        "error": None if usage_key else (probe.get("error") or "no_match"),
        "note": "Public GBIF species match. Not a Fusarium biology p.",
    }


async def fetch_open_meteo_air_quality() -> Dict[str, Any]:
    probe = await _get_json(
        OPEN_METEO_AQ_URL,
        params={
            "latitude": PUBLIC_WEATHER_LAT,
            "longitude": PUBLIC_WEATHER_LON,
            "current": "us_aqi,pm2_5,ozone",
            "timezone": "UTC",
        },
    )
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    current = data.get("current") if isinstance(data.get("current"), dict) else {}
    return {
        "ok": bool(probe.get("ok") and current),
        "source": "open-meteo-air-quality",
        "citation": OPEN_METEO_AQ_URL,
        "retrieved_at": _utc_now(),
        "lat": PUBLIC_WEATHER_LAT,
        "lon": PUBLIC_WEATHER_LON,
        "current": current,
        "error": None if current else (probe.get("error") or "no current air quality"),
        "note": "Public Open-Meteo air quality at the declared Fort Stewart point.",
    }


async def fetch_usgs_quakes(ao: Dict[str, Any]) -> Dict[str, Any]:
    """Public USGS FDSN events in the AO bbox. Empty bbox is honest."""
    west, south, east, north = _bbox(ao)
    probe = await _get_json(
        USGS_QUAKES_URL,
        params={
            "format": "geojson",
            "starttime": "2024-01-01",
            "minlatitude": south,
            "maxlatitude": north,
            "minlongitude": west,
            "maxlongitude": east,
            "limit": 5,
        },
    )
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    features = data.get("features") if isinstance(data.get("features"), list) else []
    excerpt = []
    for feat in features[:5]:
        if not isinstance(feat, dict):
            continue
        props = feat.get("properties") if isinstance(feat.get("properties"), dict) else {}
        excerpt.append(
            {
                "id": feat.get("id") or props.get("code"),
                "mag": props.get("mag"),
                "place": props.get("place"),
                "time": props.get("time"),
            }
        )
    return {
        "ok": bool(probe.get("ok") and excerpt),
        "source": "usgs-earthquake",
        "citation": USGS_QUAKES_URL,
        "retrieved_at": _utc_now(),
        "count": len(excerpt),
        "excerpt": excerpt,
        "error": None if probe.get("ok") else probe.get("error"),
        "note": "Public USGS FDSN. Empty bbox is not invented seismicity.",
    }


async def fetch_mycobrain() -> Dict[str, Any]:
    probe = await _get_json(MYCOBRAIN_HEALTH)
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    count = int(data.get("devices_connected") or 0) if data else 0
    return {
        "ok": bool(probe.get("ok") and count > 0),
        "source": "mycobrain",
        "citation": MYCOBRAIN_HEALTH,
        "retrieved_at": _utc_now(),
        "devices_connected": count,
        "health": data if probe.get("ok") else {},
        "error": None if probe.get("ok") and count else (probe.get("error") or "no_live_devices"),
    }


def _geojson_from_osint(
    nominatim: Dict[str, Any],
    wikipedia: Dict[str, Any],
    directions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    features: List[Dict[str, Any]] = [
        {
            "type": "Feature",
            "properties": {
                "name": "Fort Stewart (public geocode)",
                "source": "operator-declared-public",
                "live": False,
            },
            "geometry": {"type": "Point", "coordinates": [PUBLIC_WEATHER_LON, PUBLIC_WEATHER_LAT]},
        }
    ]
    for row in nominatim.get("places") or []:
        if not isinstance(row, dict) or row.get("lat") is None or row.get("lon") is None:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": row.get("display_name") or row.get("query"),
                    "source": "Nominatim",
                    "live": False,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row["lon"]), float(row["lat"])],
                },
            }
        )
    for page in wikipedia.get("pages") or []:
        if not isinstance(page, dict) or page.get("lat") is None or page.get("lon") is None:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": page.get("title"),
                    "source": "Wikipedia",
                    "url": page.get("url"),
                    "live": False,
                },
                "geometry": {"type": "Point", "coordinates": [float(page["lon"]), float(page["lat"])]},
            }
        )
    for route in (directions or {}).get("routes") or []:
        if not isinstance(route, dict) or not route.get("polyline"):
            continue
        coords = _decode_polyline(str(route.get("polyline")))
        if len(coords) < 2:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": f"Public driving {route.get('destination') or ''}".strip(),
                    "source": "Google Maps Directions",
                    "citation": "https://maps.googleapis.com/maps/api/directions/json",
                    "duration_in_traffic_text": route.get("duration_in_traffic_text"),
                    "travel_mode": "driving",
                    "capability_class": "public_road",
                    "live": False,
                },
                "geometry": {"type": "LineString", "coordinates": coords},
            }
        )
    return {"type": "FeatureCollection", "features": features}


async def gather_public_osint(ao: Dict[str, Any]) -> Dict[str, Any]:
    """Parallel public + MINDEX + Google traffic/pathways for one AO slice."""
    import asyncio

    jobs = {
        "weather": fetch_open_meteo(ao),
        "gbif": fetch_gbif_occurrences(ao),
        "inat": fetch_inaturalist(ao),
        "wikipedia": fetch_wikipedia_bases(),
        "nominatim": fetch_nominatim_places(),
        "google_dir": fetch_google_directions(ao),
        "google_traffic": fetch_google_traffic(ao),
        "mindex": fetch_mindex_slice(ao),
        "pubchem": fetch_pubchem_fusaric(),
        "gbif_species": fetch_gbif_species_match(),
        "air": fetch_open_meteo_air_quality(),
        "usgs": fetch_usgs_quakes(ao),
    }
    done_map: Dict[str, Any] = {}
    tasks = {name: asyncio.create_task(coro) for name, coro in jobs.items()}
    done, pending = await asyncio.wait(tasks.values(), timeout=3.3)
    for name, task in tasks.items():
        if task in pending:
            task.cancel()
            done_map[name] = {"ok": False, "error": "deadline", "source": name}
            continue
        try:
            done_map[name] = task.result()
        except Exception as exc:  # noqa: BLE001
            done_map[name] = {"ok": False, "error": str(exc), "source": name}
    weather = done_map.get("weather")
    gbif = done_map.get("gbif")
    inat = done_map.get("inat")
    osm = {"ok": False, "source": "osm", "error": "deferred_for_latency", "places": []}
    nominatim = done_map.get("nominatim")
    google_dir = done_map.get("google_dir")
    google_traffic = done_map.get("google_traffic")
    road_limits = {"ok": False, "source": "osm-road-limits", "error": "deferred_for_latency", "limits": []}
    nws = {"ok": False, "source": "nws", "error": "deferred_for_latency"}
    wikipedia = done_map.get("wikipedia")
    pubchem = done_map.get("pubchem")
    mycobrain = {"ok": False, "source": "mycobrain", "error": "deferred_for_latency"}
    mindex = done_map.get("mindex")
    gbif_species = done_map.get("gbif_species")
    air_quality = done_map.get("air")
    usgs = done_map.get("usgs")
    hifld = {"ok": False, "source": "hifld", "error": "skipped_for_latency", "sites": []}
    opensky = {"ok": False, "source": "opensky", "error": "skipped_for_latency"}
    google_places = {"ok": False, "source": "google-places", "error": "skipped_for_latency", "places": []}

    def _as_dict(value: Any, name: str) -> Dict[str, Any]:
        if isinstance(value, Exception):
            return {"ok": False, "error": str(value), "source": name}
        return value if isinstance(value, dict) else {"ok": False, "error": f"bad {name}"}

    nominatim_d = _as_dict(nominatim, "nominatim")
    hifld_d = _as_dict(hifld, "hifld")
    places_d = _as_dict(google_places, "google-places")
    wiki_d = _as_dict(wikipedia, "wikipedia")
    nws_d = _as_dict(nws, "nws")
    opensky_d = _as_dict(opensky, "opensky")
    pubchem_d = _as_dict(pubchem, "pubchem")
    mycobrain_d = _as_dict(mycobrain, "mycobrain")
    public_base = {
        "ok": bool(
            (nominatim_d.get("places") or [])
            or (hifld_d.get("sites") or [])
            or (places_d.get("places") or [])
            or (wiki_d.get("pages") or [])
        ),
        "nominatim": nominatim_d,
        "hifld": hifld_d,
        "google_places": places_d,
        "wikipedia": wiki_d,
        "note": "Public names / HIFLD Open / Places / Wikipedia only. Official injects stay NOT_SUPPLIED.",
    }
    retrieved = _utc_now()
    key_name = _google_key_name()

    return {
        "mindex": _as_dict(mindex, "mindex"),
        "open_meteo": _as_dict(weather, "open-meteo"),
        "nws": nws_d,
        "gbif": _as_dict(gbif, "gbif"),
        "gbif_species": _as_dict(gbif_species, "gbif-species"),
        "air_quality": _as_dict(air_quality, "air-quality"),
        "usgs": _as_dict(usgs, "usgs"),
        "inaturalist": _as_dict(inat, "inaturalist"),
        "osm_military": _as_dict(osm, "osm"),
        "hifld": hifld_d,
        "nominatim": nominatim_d,
        "wikipedia": wiki_d,
        "google_directions": _as_dict(google_dir, "google-directions"),
        "google_traffic": _as_dict(google_traffic, "google-traffic"),
        "google_places": places_d,
        "road_limits": _as_dict(road_limits, "osm-road-limits"),
        "opensky": opensky_d,
        "pubchem": pubchem_d,
        "mycobrain": mycobrain_d,
        "public_base": public_base,
        "geojson": _geojson_from_osint(nominatim_d, wiki_d, _as_dict(google_dir, "google-directions")),
        "google_key_present": _google_key_present(),
        "google_key_env_name": key_name,
        "retrieved_at": retrieved,
        "official_injects": "NOT_SUPPLIED",
        "cui": False,
        "fouo": False,
        "refused": [
            {
                "source": "Army FOUO PDFs / HQ 3ID OPORD 14-06 BULLDOG",
                "reason": "UNCLASSIFIED//FOUO — STOP_INGEST outside CUI boundary",
            },
            {"source": "Official Army injects / 1–5 rubric", "reason": "NOT_SUPPLIED by contract"},
            {"source": "ADS-B Exchange / MarineTraffic", "reason": "auth/paid wall — restricted_source"},
            {
                "source": "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY as Directions",
                "reason": "REQUEST_DENIED — Map Tiles key is not Directions-capable",
            },
        ],
    }
