"""
Run a single validation job: load GT masks, compute metrics (e.g. vs dummy prediction), write results.
Phase 0: dummy prediction = GT with slight erosion so metrics are non-trivial.
"""
from __future__ import annotations

import json
import os
import sys
import uuid

import numpy as np

# Add parent so we can import from scripts
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.myceliumseg.metrics import compute_all_metrics

DATABASE_URL = os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL")


def get_db():
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    except ImportError:
        raise RuntimeError("psycopg2 required") from None
    except Exception as e:
        raise RuntimeError(f"DB connection failed: {e}") from e


def load_mask_from_path(path: str) -> np.ndarray | None:
    """Load binary mask from path (PNG). Returns (H,W) uint8."""
    if not path or not os.path.isfile(path):
        return None
    try:
        from PIL import Image
        img = np.array(Image.open(path))
        if img.ndim == 3:
            img = img[:, :, 0]
        return (img > 0).astype(np.uint8)
    except Exception:
        return None


def dummy_prediction_from_gt(gt: np.ndarray) -> np.ndarray:
    """Phase 0: erode GT slightly to simulate a prediction."""
    try:
        from scipy import ndimage
        pred = ndimage.binary_erosion(gt, iterations=2).astype(np.uint8)
    except ImportError:
        pred = gt.copy()
    return pred


def run_job(job_id: str) -> bool:
    """
    Process job_id: for each image in dataset_slice, compute metrics (GT vs dummy pred), insert validation_results, set job completed.
    Phase 0: if no real mask files, use synthetic GT (circle) and dummy pred.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, dataset_slice, status FROM core.validation_jobs WHERE id = %s",
                (uuid.UUID(job_id),),
            )
            row = cur.fetchone()
            if not row:
                return False
            if row["status"] != "queued":
                return True  # already processed
            slice_cfg = row["dataset_slice"] if isinstance(row["dataset_slice"], dict) else json.loads(row["dataset_slice"])
            limit = int(slice_cfg.get("limit", 5))
            species = slice_cfg.get("species")
            # Fetch image IDs for this slice (prefer images that have masks)
            cond = "1=1"
            params: list = []
            if species and isinstance(species, list) and len(species) > 0:
                cond += " AND i.species = ANY(%s)"
                params.append(species)
            params.append(limit)
            cur.execute(
                f"""SELECT i.id, i.external_id, i.asset_path FROM core.myceliumseg_images i
                    WHERE {cond} ORDER BY i.external_id LIMIT %s""",
                params,
            )
            images = cur.fetchall()
        if not images:
            # No labeled images: create one synthetic result for Phase 0
            h, w = 256, 256
            y, x = np.ogrid[:h, :w]
            gt = ((x - w // 2) ** 2 + (y - h // 2) ** 2 <= (min(h, w) // 3) ** 2).astype(np.uint8)
            pred = dummy_prediction_from_gt(gt)
            metrics = compute_all_metrics(gt, pred)
            with conn.cursor() as cur:
                cur.execute("UPDATE core.validation_jobs SET status = 'completed', completed_at = NOW(), updated_at = NOW() WHERE id = %s", (uuid.UUID(job_id),))
                # Insert one synthetic result (no image_id FK if we have no row - use first image or skip)
                cur.execute("SELECT id FROM core.myceliumseg_images ORDER BY external_id LIMIT 1")
                first = cur.fetchone()
                if first:
                    cur.execute(
                        "INSERT INTO core.validation_results (validation_job_id, image_id, sample_metrics) VALUES (%s, %s, %s)",
                        (uuid.UUID(job_id), first["id"], json.dumps(metrics)),
                    )
            conn.commit()
            return True
        results = []
        for img in images:
            # Try to load GT mask from asset_path (mask path)
            cur2 = conn.cursor()
            cur2.execute("SELECT asset_path FROM core.myceliumseg_masks WHERE image_id = %s LIMIT 1", (img["id"],))
            mask_row = cur2.fetchone()
            cur2.close()
            mask_path = mask_row["asset_path"] if mask_row else None
            gt = load_mask_from_path(mask_path) if mask_path else None
            if gt is None:
                # Synthetic
                h, w = 256, 256
                y, x = np.ogrid[:h, :w]
                gt = ((x - w // 2) ** 2 + (y - h // 2) ** 2 <= (min(h, w) // 3) ** 2).astype(np.uint8)
            pred = dummy_prediction_from_gt(gt)
            metrics = compute_all_metrics(gt, pred)
            results.append((img["id"], metrics))
        with conn.cursor() as cur:
            cur.execute("UPDATE core.validation_jobs SET status = 'running', updated_at = NOW() WHERE id = %s", (uuid.UUID(job_id),))
            conn.commit()
            for image_id, metrics in results:
                cur.execute(
                    "INSERT INTO core.validation_results (validation_job_id, image_id, sample_metrics) VALUES (%s, %s, %s)",
                    (uuid.UUID(job_id), image_id, json.dumps(metrics)),
                )
            cur.execute("UPDATE core.validation_jobs SET status = 'completed', completed_at = NOW(), updated_at = NOW() WHERE id = %s", (uuid.UUID(job_id),))
        conn.commit()
        return True
    except Exception as e:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE core.validation_jobs SET status = 'failed', error_message = %s, updated_at = NOW() WHERE id = %s",
                (str(e), uuid.UUID(job_id)),
            )
        conn.commit()
        raise
    finally:
        conn.close()


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("job_id", help="Validation job UUID")
    args = p.parse_args()
    run_job(args.job_id)
    print("Job completed.")


if __name__ == "__main__":
    main()
