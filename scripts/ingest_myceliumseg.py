#!/usr/bin/env python3
"""
Ingest MyceliumSeg dataset metadata (and optionally blobs) into MINDEX.
Phase 0: --fixture inserts 5-10 metadata-only rows for development.
Usage:
  python scripts/ingest_myceliumseg.py --fixture
  python scripts/ingest_myceliumseg.py --dir /path/to/labeled-GL/trainset
  MINDEX_DATABASE_URL=postgresql://... python scripts/ingest_myceliumseg.py --fixture
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

# Prefer psycopg2; fallback for envs without it
try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None

DATABASE_URL = os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL")
if not DATABASE_URL and "postgres" not in str(os.getenv("DATABASE_URL", "")):
    DATABASE_URL = os.getenv("MINDEX_DATABASE_URL", "postgresql://mindex:mindex@localhost:5432/mindex")

# Fixture: 10 labeled samples from MyceliumSeg (trainset GL 00000001-00000010)
# Paper: labeled-GL trainset 00000001-00000457, testset 00000458-00000507
FIXTURE_IMAGES = [
    {"external_id": "00000001", "species": "GL", "growth_stage": "network_building", "medium": "MYG", "temperature_c": 25, "split": "trainset"},
    {"external_id": "00000002", "species": "GL", "growth_stage": "network_building", "medium": "MYG", "temperature_c": 25, "split": "trainset"},
    {"external_id": "00000003", "species": "GL", "growth_stage": "maturation", "medium": "MYG", "temperature_c": 25, "split": "trainset"},
    {"external_id": "00000004", "species": "GL", "growth_stage": "primary_expansion", "medium": "MYG", "temperature_c": 25, "split": "trainset"},
    {"external_id": "00000005", "species": "GL", "growth_stage": "network_building", "medium": "MYG", "temperature_c": 25, "split": "trainset"},
    {"external_id": "00000006", "species": "GL", "growth_stage": "activation_germination", "medium": "MYG", "temperature_c": 25, "split": "trainset"},
    {"external_id": "00000007", "species": "GL", "growth_stage": "network_building", "medium": "MYG", "temperature_c": 25, "split": "trainset"},
    {"external_id": "00000008", "species": "GL", "growth_stage": "maturation", "medium": "MYG", "temperature_c": 25, "split": "trainset"},
    {"external_id": "00000009", "species": "GL", "growth_stage": "network_building", "medium": "MYG", "temperature_c": 25, "split": "trainset"},
    {"external_id": "00000010", "species": "GL", "growth_stage": "network_building", "medium": "MYG", "temperature_c": 25, "split": "trainset"},
]
# Paper: 4608 x 3456
FIXTURE_WIDTH = 4608
FIXTURE_HEIGHT = 3456


def get_conn():
    if not psycopg2:
        raise RuntimeError("psycopg2 is required. pip install psycopg2-binary")
    return psycopg2.connect(DATABASE_URL)


def ensure_schema(conn):
    """Ensure core schema exists (migration 021 must be applied separately)."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'core' AND table_name = 'myceliumseg_images'")
        if cur.fetchone() is None:
            raise RuntimeError("core.myceliumseg_images not found. Apply migration 021_myceliumseg.sql first.")


def ingest_fixture(conn, asset_base_url: str | None = None):
    """Insert fixture image and mask metadata. No real blobs; asset_path is placeholder."""
    asset_base = asset_base_url or os.getenv("MYCELIUMSEG_ASSET_BASE", "fixture/")
    inserted = 0
    with conn.cursor() as cur:
        for row in FIXTURE_IMAGES:
            image_id = uuid.uuid4()
            # Insert image (no blob_id; use asset_path for fixture)
            cur.execute(
                """INSERT INTO core.myceliumseg_images
                   (id, external_id, species, growth_stage, medium, temperature_c, split, asset_path, width, height, dataset_version)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (external_id) DO NOTHING""",
                (
                    image_id,
                    row["external_id"],
                    row["species"],
                    row["growth_stage"],
                    row["medium"],
                    row["temperature_c"],
                    row["split"],
                    f"{asset_base}image/{row['external_id']}.jpg",
                    FIXTURE_WIDTH,
                    FIXTURE_HEIGHT,
                    "myceliumseg-v1.0",
                ),
            )
            if cur.rowcount:
                inserted += 1
                # Insert mask for this image (fixture: same convention as paper - mask in mask/)
                cur.execute(
                    """INSERT INTO core.myceliumseg_masks (image_id, asset_path, mask_version)
                       SELECT id, %s, 'v1' FROM core.myceliumseg_images WHERE external_id = %s
                       ON CONFLICT (image_id, mask_version) DO NOTHING""",
                    (f"{asset_base}mask/{row['external_id']}.png", row["external_id"]),
                )
    conn.commit()
    return inserted


def ingest_from_dir(conn, image_dir: Path, mask_dir: Path | None = None):
    """Ingest from a directory structure: image_dir/image/*.jpg, (optional) image_dir/mask/*.png."""
    image_path = image_dir / "image" if (image_dir / "image").exists() else image_dir
    mask_path = (mask_dir or image_dir) / "mask" if (image_dir / "mask").exists() else (mask_dir or image_dir)
    if not image_path.exists():
        raise FileNotFoundError(f"Image path not found: {image_path}")
    inserted = 0
    # Infer species/split from path (e.g. .../trainset or .../GL)
    split = "trainset"
    if "testset" in str(image_dir):
        split = "testset"
    species = "GL"
    for p in sorted(image_path.glob("*.jpg"))[:500]:  # limit for safety
        external_id = p.stem
        with conn.cursor() as cur:
            image_id = uuid.uuid4()
            cur.execute(
                """INSERT INTO core.myceliumseg_images
                   (id, external_id, species, growth_stage, medium, temperature_c, split, asset_path, width, height, dataset_version)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (external_id) DO NOTHING""",
                (
                    image_id,
                    external_id,
                    species,
                    "network_building",
                    "MYG",
                    25,
                    split,
                    str(p),
                    FIXTURE_WIDTH,
                    FIXTURE_HEIGHT,
                    "myceliumseg-v1.0",
                ),
            )
            if cur.rowcount:
                inserted += 1
                mask_file = mask_path / f"{external_id}.png"
                if mask_file.exists():
                    cur.execute(
                        """INSERT INTO core.myceliumseg_masks (image_id, asset_path, mask_version)
                           SELECT id, %s, 'v1' FROM core.myceliumseg_images WHERE external_id = %s
                           ON CONFLICT (image_id, mask_version) DO NOTHING""",
                        (str(mask_file), external_id),
                    )
    conn.commit()
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Ingest MyceliumSeg into MINDEX")
    parser.add_argument("--fixture", action="store_true", help="Insert fixture metadata (10 samples)")
    parser.add_argument("--dir", type=Path, help="Path to labeled set (e.g. labeled-GL/trainset)")
    parser.add_argument("--asset-base", type=str, help="Base URL/path for asset_path in fixture")
    args = parser.parse_args()

    if not args.fixture and not args.dir:
        parser.error("Use --fixture or --dir PATH")

    if not DATABASE_URL or "postgres" not in DATABASE_URL:
        print("Set MINDEX_DATABASE_URL or DATABASE_URL (PostgreSQL).", file=sys.stderr)
        sys.exit(1)

    try:
        conn = get_conn()
    except Exception as e:
        print(f"Database connection failed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        ensure_schema(conn)
        if args.fixture:
            n = ingest_fixture(conn, args.asset_base)
            print(f"Fixture: inserted {n} image rows (with masks).")
        else:
            n = ingest_from_dir(conn, args.dir)
            print(f"Dir: inserted {n} image rows.")
    except Exception as e:
        print(f"Ingest failed: {e}", file=sys.stderr)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
