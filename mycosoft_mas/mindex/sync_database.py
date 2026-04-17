"""
Async PostgreSQL helpers for MINDEX full_sync and scrapers (Apr 17, 2026).

Prefers `species.organisms` (20260315 migration) for taxon upserts; falls back to
`core.taxon` + metadata when needed. Sightings → `species.sightings`; images → `media.image`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from typing import Any, Dict, Optional, Union

import asyncpg

logger = logging.getLogger(__name__)

_DEFAULT_POOL_MAX = 8
_MAX_RETRIES = 3
_BASE_BACKOFF_SEC = 0.8


def resolve_mindex_database_url(override: Optional[str] = None) -> str:
    """Resolve DSN for MINDEX PostgreSQL."""
    for key in (override, os.environ.get("MINDEX_DATABASE_URL"), os.environ.get("DATABASE_URL")):
        if key and str(key).strip():
            return str(key).strip()
    return ""


async def create_mindex_pool(database_url: str) -> asyncpg.Pool:
    """Create asyncpg pool with bounded retries."""
    last_exc: Optional[BaseException] = None
    for attempt in range(_MAX_RETRIES):
        try:
            return await asyncpg.create_pool(
                database_url,
                min_size=1,
                max_size=int(os.environ.get("MINDEX_POOL_MAX", _DEFAULT_POOL_MAX)),
                command_timeout=float(os.environ.get("MINDEX_PG_COMMAND_TIMEOUT", "120")),
            )
        except Exception as e:
            last_exc = e
            wait = _BASE_BACKOFF_SEC * (2**attempt)
            logger.warning(
                "MINDEX pool attempt %s/%s failed: %s; retry in %.1fs",
                attempt + 1,
                _MAX_RETRIES,
                e,
                wait,
            )
            await asyncio.sleep(wait)
    assert last_exc is not None
    raise last_exc


class MindexFullSyncDB:
    """Wraps asyncpg pool for scrapers (`execute`, `call_insert_*`)."""

    __slots__ = ("_pool",)

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def execute(self, query: str, *args: Any) -> str:
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def close(self) -> None:
        await self._pool.close()


def _species_source_and_id(row: Dict[str, Any]) -> tuple[str, str]:
    src = (
        row.get("source")
        or row.get("data_source")
        or ("GBIF" if row.get("gbif_key") is not None else None)
        or ("iNaturalist" if row.get("inat_id") is not None else None)
        or ("IndexFungorum" if row.get("record_id") is not None else None)
        or "MINDEX_SYNC"
    )
    sid = (
        row.get("gbif_key")
        or row.get("inat_id")
        or row.get("record_id")
        or row.get("id")
        or row.get("species_id")
    )
    return str(src)[:50], str(sid if sid is not None else "")[:100]


def _split_genus_species(scientific_name: str) -> tuple[Optional[str], Optional[str]]:
    parts = scientific_name.strip().split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    if len(parts) == 1:
        return parts[0], None
    return None, None


async def call_insert_species(db: Union[MindexFullSyncDB, Any], row: Dict[str, Any]) -> None:
    """Upsert taxon: prefer species.organisms, then extended core.taxon, then minimal core.taxon."""
    scientific_name = (row.get("scientific_name") or row.get("canonical_name") or "").strip()
    if not scientific_name:
        logger.debug("call_insert_species: skip row without scientific_name")
        return

    source, source_id = _species_source_and_id(row)
    if not source_id:
        source_id = hashlib.sha256(scientific_name.encode()).hexdigest()[:32]

    genus, species_ep = _split_genus_species(scientific_name)
    meta_extra: Dict[str, Any] = {
        k: v
        for k, v in row.items()
        if k
        not in {
            "scientific_name",
            "canonical_name",
            "kingdom",
            "phylum",
            "class_name",
            "class",
            "order_name",
            "order",
            "family",
            "genus",
            "rank",
            "author",
            "year",
            "source",
            "gbif_key",
            "inat_id",
            "record_id",
        }
        and v is not None
    }

    properties_obj: Dict[str, Any] = dict(meta_extra) if meta_extra else {}
    tax_key = row.get("gbif_key") or row.get("taxonomy_id") or row.get("taxon_key")

    q_org = """
        INSERT INTO species.organisms (
            source, source_id, kingdom, phylum, class_name, order_name, family, genus,
            species_name, scientific_name, rank, taxonomy_id, properties
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb)
        ON CONFLICT (source, source_id) DO UPDATE SET
            scientific_name = EXCLUDED.scientific_name,
            kingdom = EXCLUDED.kingdom,
            phylum = EXCLUDED.phylum,
            class_name = EXCLUDED.class_name,
            order_name = EXCLUDED.order_name,
            family = EXCLUDED.family,
            genus = EXCLUDED.genus,
            species_name = EXCLUDED.species_name,
            rank = EXCLUDED.rank,
            taxonomy_id = COALESCE(EXCLUDED.taxonomy_id, species.organisms.taxonomy_id),
            properties = species.organisms.properties || EXCLUDED.properties
    """

    try:
        await db.execute(
            q_org,
            source,
            source_id,
            row.get("kingdom", "Fungi"),
            row.get("phylum"),
            row.get("class_name") or row.get("class"),
            row.get("order_name") or row.get("order"),
            row.get("family"),
            row.get("genus") or genus,
            species_ep,
            scientific_name,
            row.get("rank", "species"),
            int(tax_key) if tax_key is not None and str(tax_key).isdigit() else None,
            properties_obj,
        )
        return
    except asyncpg.exceptions.PostgresError as e:
        if "species.organisms" not in str(e) and "does not exist" not in str(e).lower():
            logger.error("species.organisms insert failed: %s", e)
            raise
        logger.debug("species.organisms unavailable (%s); trying core.taxon", e)

    # Legacy / extended core.taxon (matches Index Fungorum scraper SQL)
    meta_if = {**meta_extra, "scientific_name": scientific_name}
    q_taxon_ext = """
        INSERT INTO core.taxon (
            scientific_name, kingdom, phylum, class, "order", family,
            rank, author, year, source, source_id, metadata, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, NOW())
        ON CONFLICT (source, source_id) DO UPDATE SET
            metadata = core.taxon.metadata || EXCLUDED.metadata,
            updated_at = NOW()
    """
    year_val = row.get("year")
    if year_val is not None and not isinstance(year_val, int):
        try:
            year_val = int(year_val)
        except (TypeError, ValueError):
            year_val = None

    try:
        await db.execute(
            q_taxon_ext,
            scientific_name,
            row.get("kingdom", "Fungi"),
            row.get("phylum"),
            row.get("class_name") or row.get("class"),
            row.get("order_name") or row.get("order"),
            row.get("family"),
            row.get("rank", "species"),
            row.get("author"),
            year_val,
            source,
            source_id,
            meta_if,
        )
        return
    except asyncpg.exceptions.PostgresError as e:
        if "column" not in str(e).lower() and "conflict" not in str(e).lower():
            logger.debug("extended core.taxon path skipped: %s", e)

    # Minimal core.taxon (0001_init) — dedupe by canonical_name + source
    meta_min = {**meta_if, "source_id": source_id}
    await db.execute(
        """
        INSERT INTO core.taxon (
            canonical_name, rank, authority, source, metadata, created_at, updated_at
        )
        SELECT $1, $2, $3, $4, $5::jsonb, NOW(), NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM core.taxon t
            WHERE t.canonical_name = $1 AND COALESCE(t.source, '') = COALESCE($4::text, '')
        )
        """,
        scientific_name,
        row.get("rank", "species"),
        row.get("author"),
        source,
        meta_min,
    )


async def call_insert_observation(db: Union[MindexFullSyncDB, Any], row: Dict[str, Any]) -> None:
    """Insert into species.sightings (PostGIS). Skips rows without coordinates."""
    lat = row.get("latitude")
    lon = row.get("longitude")
    if lat is None or lon is None:
        return

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return

    src = str(row.get("source") or "MINDEX_SYNC")[:50]
    ext = row.get("external_id") or row.get("gbif_key") or row.get("inat_id") or row.get("id")
    sid = str(ext)[:100] if ext is not None else ""

    props = json.dumps({k: v for k, v in row.items() if k not in ("latitude", "longitude")})

    observed_at = row.get("observed_on") or row.get("created_at")
    if hasattr(observed_at, "isoformat"):
        observed_at = observed_at.isoformat()

    img = None
    photos = row.get("photos") or []
    if photos and isinstance(photos, list) and photos and isinstance(photos[0], dict):
        img = photos[0].get("url")

    await db.execute(
        """
        INSERT INTO species.sightings (
            organism_id, source, source_id, location, observed_at, observer,
            image_url, quality_grade, properties
        ) VALUES (
            NULL, $1, $2,
            ST_SetSRID(ST_MakePoint($3, $4), 4326)::geography,
            COALESCE($5::timestamptz, NOW()),
            $6, $7, $8, $9::jsonb
        )
        """,
        src,
        sid or hashlib.sha256(props.encode()).hexdigest()[:24],
        lon_f,
        lat_f,
        observed_at,
        row.get("observer"),
        img,
        row.get("quality_grade"),
        props,
    )


async def call_insert_image(db: Union[MindexFullSyncDB, Any], row: Dict[str, Any]) -> None:
    """Insert media stub into media.image."""
    url = row.get("url") or row.get("source_url")
    if not url:
        return

    src = str(row.get("source") or "MINDEX_SYNC")[:100]
    sid = str(row.get("source_id") or row.get("occurrence_key") or "")[:255]
    base = hashlib.sha256(f"{src}|{sid}|{url}".encode()).hexdigest()[:16]
    mindex_id = f"MYCO-IMG-{base.upper()}"

    fname = re.sub(r"[^a-zA-Z0-9._-]+", "_", url.split("/")[-1][:200] or "image")[:200]

    await db.execute(
        """
        INSERT INTO media.image (
            mindex_id, filename, file_path, source, source_url, source_id,
            license, attribution, species_confidence, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, NOW()
        )
        ON CONFLICT (mindex_id) DO UPDATE SET
            source_url = EXCLUDED.source_url,
            updated_at = NOW()
        """,
        mindex_id,
        fname,
        url,
        src,
        url,
        sid or None,
        (row.get("license") or "unknown")[:100],
        (row.get("attribution") or "")[:500],
        float(row.get("quality_score") or 0.5),
    )
