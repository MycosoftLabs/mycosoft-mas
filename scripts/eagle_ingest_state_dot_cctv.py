#!/usr/bin/env python3
"""
Daily warm-cache: State DOT public CCTV APIs → MINDEX eagle.video_sources bulk-upsert.

Mirrors WEBSITE/website/app/api/eagle/connectors/state-dot-cctv/route.ts feeds.
Run from MAS VM (188) or any host with MINDEX_INTERNAL_TOKEN + network egress.

Env:
  MINDEX_API_URL          default http://192.168.0.189:8000
  MINDEX_INTERNAL_TOKEN   required (or legacy MINDEX_API_KEY in X-API-Key)
  WSDOT_ACCESS_CODE       optional; WSDOT skipped if unset
  WSDOT_API_KEY           alias for WSDOT_ACCESS_CODE
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any
from urllib.parse import quote

import httpx

LOG = logging.getLogger("eagle_ingest_state_dot_cctv")

BULK_CHUNK = 200
USER_AGENT = "MycosoftCREP/1.0 (eagle-state-dot-cctv-cron)"
DEFAULT_MINDEX = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")


def _auth_headers() -> dict[str, str]:
    token = (
        os.environ.get("MINDEX_INTERNAL_TOKEN")
        or (os.environ.get("MINDEX_INTERNAL_TOKENS") or "").split(",")[0].strip()
    )
    if token:
        return {"X-Internal-Token": token}
    key = os.environ.get("MINDEX_API_KEY", "")
    if key:
        return {"X-API-Key": key}
    return {}


def cam_to_upsert(cam: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": cam["id"],
        "kind": "permanent",
        "provider": cam["provider"],
        "stable_location": True,
        "lat": cam["lat"],
        "lng": cam["lng"],
        "location_confidence": 0.95,
        "stream_url": cam.get("stream_url"),
        "embed_url": cam.get("embed_url"),
        "media_url": cam.get("media_url"),
        "source_status": "active",
        "permissions": {"access": "public", "source": "state_dot_cctv_cron"},
        "retention_policy": {},
        "provenance_method": "state_dot_public_api_daily",
        "privacy_class": "public",
    }


async def pull_caltrans(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    districts = list(range(1, 13))
    out: list[dict[str, Any]] = []

    async def one(d: int) -> list[dict[str, Any]]:
        local: list[dict[str, Any]] = []
        url = (
            f"https://cwwp2.dot.ca.gov/data/d{d}/cctv/"
            f"cctvStatusD{str(d).zfill(2)}.json"
        )
        try:
            r = await client.get(url, timeout=12.0)
            if r.status_code != 200:
                return []
            j = r.json()
            items = j.get("data") or []
            for entry in items:
                cctv = entry.get("cctv") or {}
                loc = (cctv.get("location") or {})
                try:
                    lat_f = float(loc.get("latitude"))
                    lng_f = float(loc.get("longitude"))
                except (TypeError, ValueError):
                    continue
                if not (lat_f == lat_f and lng_f == lng_f):
                    continue
                image_data = cctv.get("imageData") or {}
                still = image_data.get("static", {}).get("currentImageURL") or image_data.get(
                    "streamingVideoURL"
                )
                stream = image_data.get("streamingVideoURL")
                idx = cctv.get("indexCctv") or ""
                rid = cctv.get("recordId") or cctv.get("indexCctv") or f"{lat_f},{lng_f}"
                embed = (
                    f"https://cwwp2.dot.ca.gov/vm/iframemap.htm?code={quote(str(idx))}"
                    if idx
                    else None
                )
                local.append(
                    {
                        "id": f"caltrans-d{d}-{rid}",
                        "provider": "caltrans",
                        "lat": lat_f,
                        "lng": lng_f,
                        "stream_url": stream,
                        "embed_url": embed,
                        "media_url": still,
                    }
                )
        except Exception as e:
            LOG.debug("Caltrans d%s: %s", d, e)
        return local

    results = await asyncio.gather(*[one(d) for d in districts])
    for block in results:
        out.extend(block)
    return out


async def pull_wsdot(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    key = os.environ.get("WSDOT_ACCESS_CODE") or os.environ.get("WSDOT_API_KEY") or ""
    if not key:
        return []
    url = (
        "https://wsdot.wa.gov/traffic/api/Cameras/CamerasREST.svc/GetCamerasAsJson"
        f"?AccessCode={quote(key, safe='')}"
    )
    out: list[dict[str, Any]] = []
    try:
        r = await client.get(url, timeout=15.0)
        if r.status_code != 200:
            return []
        items = r.json()
        if not isinstance(items, list):
            return []
        for c in items:
            cl = c.get("CameraLocation") or {}
            try:
                lat = float(cl.get("Latitude"))
                lng = float(cl.get("Longitude"))
            except (TypeError, ValueError):
                continue
            if not (lat == lat and lng == lng):
                continue
            cid = c.get("CameraID")
            img = c.get("ImageURL")
            out.append(
                {
                    "id": f"wsdot-{cid}",
                    "provider": "wsdot",
                    "lat": lat,
                    "lng": lng,
                    "stream_url": None,
                    "embed_url": img,
                    "media_url": img,
                }
            )
    except Exception as e:
        LOG.warning("WSDOT: %s", e)
    return out


async def pull_fdot(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    urls = (
        "https://fl511.com/map/data/cctvs.json",
        "https://www.fl511.com/map/data/cctvs.json",
    )
    j = None
    try:
        for fdot_url in urls:
            r = await client.get(fdot_url, timeout=20.0)
            if r.status_code == 200:
                j = r.json()
                break
        if j is None:
            return []
        items = j.get("data") or j.get("features") or (j if isinstance(j, list) else [])
        if not isinstance(items, list):
            return []
        for c in items:
            try:
                lat = float(c.get("latitude", c.get("lat")))
                lng = float(c.get("longitude", c.get("lng")))
            except (TypeError, ValueError):
                geom = c.get("geometry") or {}
                coords = geom.get("coordinates") or []
                if len(coords) >= 2:
                    lng = float(coords[0])
                    lat = float(coords[1])
                else:
                    continue
            if not (lat == lat and lng == lng):
                continue
            cid = c.get("id") or c.get("camId") or f"{lat},{lng}"
            out.append(
                {
                    "id": f"fdot-{cid}",
                    "provider": "fdot",
                    "lat": lat,
                    "lng": lng,
                    "stream_url": c.get("hlsUrl"),
                    "embed_url": c.get("url") or c.get("videoUrl"),
                    "media_url": c.get("imageUrl") or c.get("snapshotUrl"),
                }
            )
    except Exception as e:
        LOG.warning("FDOT: %r", e)
    return out


async def pull_nysdot(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        r = await client.get(
            "https://511ny.org/api/getcameras?format=json",
            timeout=15.0,
        )
        if r.status_code != 200:
            return []
        items = r.json()
        if not isinstance(items, list):
            return []
        for c in items:
            try:
                lat = float(c.get("Latitude"))
                lng = float(c.get("Longitude"))
            except (TypeError, ValueError):
                continue
            if not (lat == lat and lng == lng):
                continue
            cid = c.get("ID")
            out.append(
                {
                    "id": f"nysdot-{cid}",
                    "provider": "nysdot",
                    "lat": lat,
                    "lng": lng,
                    "stream_url": None,
                    "embed_url": c.get("Url"),
                    "media_url": c.get("ImageUrl"),
                }
            )
    except Exception as e:
        LOG.warning("511NY: %s", e)
    return out


async def pull_txdot(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        r = await client.get(
            "https://www.drivetexas.org/api/cctv-cameras",
            timeout=httpx.Timeout(45.0, connect=20.0),
        )
        if r.status_code != 200:
            return []
        j = r.json()
        items = j.get("features") or j.get("data") or (j if isinstance(j, list) else [])
        if not isinstance(items, list):
            return []
        for c in items:
            p = c.get("properties") or c
            try:
                lat = float(p.get("latitude", p.get("lat")))
                lng = float(p.get("longitude", p.get("lng")))
            except (TypeError, ValueError):
                geom = c.get("geometry") or {}
                coords = (geom.get("coordinates") or [])[:2]
                if len(coords) >= 2:
                    lng = float(coords[0])
                    lat = float(coords[1])
                else:
                    continue
            if not (lat == lat and lng == lng):
                continue
            cid = p.get("id") or p.get("cctv_id") or f"{lat},{lng}"
            snap = p.get("snapshotURL") or p.get("imageURL")
            out.append(
                {
                    "id": f"txdot-{cid}",
                    "provider": "txdot",
                    "lat": lat,
                    "lng": lng,
                    "stream_url": p.get("streamURL"),
                    "embed_url": snap,
                    "media_url": snap,
                }
            )
    except Exception as e:
        LOG.warning("TxDOT: %r", e)
    return out


async def collect_all(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    cal, ws, fd, ny, tx = await asyncio.gather(
        pull_caltrans(client),
        pull_wsdot(client),
        pull_fdot(client),
        pull_nysdot(client),
        pull_txdot(client),
    )
    merged = [*cal, *ws, *fd, *ny, *tx]
    by_id: dict[str, dict[str, Any]] = {}
    for c in merged:
        by_id[c["id"]] = c
    deduped = list(by_id.values())
    LOG.info(
        "Fetched cameras: caltrans=%s wsdot=%s fdot=%s nysdot=%s txdot=%s merged=%s deduped=%s",
        len(cal),
        len(ws),
        len(fd),
        len(ny),
        len(tx),
        len(merged),
        len(deduped),
    )
    return deduped


def post_bulk_upsert(
    base_url: str,
    headers: dict[str, str],
    sources: list[dict[str, Any]],
    dry_run: bool,
) -> None:
    url = f"{base_url}/api/mindex/eagle/video-sources/bulk-upsert"
    if dry_run:
        LOG.info("Dry-run: would POST %s rows to %s", len(sources), url)
        print(json.dumps({"dry_run": True, "total": len(sources)}, indent=2))
        return
    auth = {**headers, "Content-Type": "application/json", "Accept": "application/json"}
    with httpx.Client(timeout=120.0) as sync_client:
        for i in range(0, len(sources), BULK_CHUNK):
            chunk = sources[i : i + BULK_CHUNK]
            r = sync_client.post(url, headers=auth, json={"sources": chunk})
            if r.status_code >= 400:
                LOG.error("bulk-upsert failed %s: %s", r.status_code, r.text[:500])
                sys.exit(1)
            try:
                body = r.json()
            except Exception:
                body = {"raw": r.text[:200]}
            LOG.info("Chunk %s-%s: %s", i, i + len(chunk), body)


async def async_main(dry_run: bool) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    hdrs = _auth_headers()
    if not hdrs and not dry_run:
        LOG.error("Set MINDEX_INTERNAL_TOKEN or MINDEX_API_KEY")
        return 1

    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        limits=limits,
        follow_redirects=True,
    ) as client:
        cams = await collect_all(client)

    sources = [cam_to_upsert(c) for c in cams]
    post_bulk_upsert(DEFAULT_MINDEX, hdrs, sources, dry_run=dry_run)
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and log counts only; do not POST to MINDEX",
    )
    args = p.parse_args()
    raise SystemExit(asyncio.run(async_main(args.dry_run)))


if __name__ == "__main__":
    main()
