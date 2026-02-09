"""
MyceliumSeg API routes for catalog, assets, and validation jobs.
Mount under FastAPI app at /mindex/myceliumseg or similar.
Uses MINDEX_DATABASE_URL for DB.
"""
from __future__ import annotations

import os
import uuid
from typing import Any

# Optional FastAPI
try:
    from fastapi import APIRouter, HTTPException, Query
    from pydantic import BaseModel
except ImportError:
    APIRouter = None  # type: ignore
    BaseModel = object  # type: ignore

DATABASE_URL = os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL")


def get_db():
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    except Exception as e:
        raise RuntimeError(f"DB connection failed: {e}") from e


# --- Pydantic models (if FastAPI available) ---
if BaseModel is not object:

    class DatasetSlice(BaseModel):
        species: list[str] | None = None
        medium: list[str] | None = None
        temperature_c: list[int] | None = None
        growth_stage: list[str] | None = None
        limit: int = 50
        offset: int = 0

    class ValidationJobCreate(BaseModel):
        dataset_slice: dict[str, Any]
        simulator_run_id: str | None = None
        model_ref: str | None = None


def catalog_images(
    species: list[str] | None = None,
    medium: list[str] | None = None,
    temperature_c: list[int] | None = None,
    growth_stage: list[str] | None = None,
    split: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Query catalog; return { items: [...], total: N }."""
    conn = get_db()
    try:
        conditions = ["1=1"]
        params: list[Any] = []
        if species:
            conditions.append("species = ANY(%s)")
            params.append(species)
        if medium:
            conditions.append("medium = ANY(%s)")
            params.append(medium)
        if temperature_c:
            conditions.append("temperature_c = ANY(%s)")
            params.append(temperature_c)
        if growth_stage:
            conditions.append("growth_stage = ANY(%s)")
            params.append(growth_stage)
        if split:
            conditions.append("split = %s")
            params.append(split)
        where = " AND ".join(conditions)
        params_count = params.copy()
        params.extend([limit, offset])
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, external_id, species, growth_stage, medium, temperature_c, split,
                           asset_path, width, height, dataset_version,
                           EXISTS(SELECT 1 FROM core.myceliumseg_masks m WHERE m.image_id = core.myceliumseg_images.id) AS has_mask
                    FROM core.myceliumseg_images WHERE {where} ORDER BY external_id LIMIT %s OFFSET %s""",
                params,
            )
            rows = cur.fetchall()
            cur.execute(f"SELECT COUNT(*) AS total FROM core.myceliumseg_images WHERE {where}", params_count)
            total = int(cur.fetchone()["total"])
        items = []
        for r in rows:
            r = dict(r)
            r["asset_url"] = r.get("asset_path")  # or signed URL in production
            r["id"] = str(r["id"])
            items.append(r)
        return {"items": items, "total": total}
    finally:
        conn.close()


def get_job(job_id: str) -> dict | None:
    """Get validation job by id with results and aggregate."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, status, dataset_slice, simulator_run_id, model_ref, created_at, completed_at, error_message
                   FROM core.validation_jobs WHERE id = %s""",
                (uuid.UUID(job_id),),
            )
            row = cur.fetchone()
            if not row:
                return None
            job = dict(row)
            job["id"] = str(job["id"])
            if job.get("simulator_run_id"):
                job["simulator_run_id"] = str(job["simulator_run_id"])
            if job["status"] != "completed":
                job["results"] = []
                job["aggregate"] = None
                return job
            cur.execute(
                """SELECT vr.image_id, vr.sample_metrics, vr.overlay_path
                   FROM core.validation_results vr WHERE vr.validation_job_id = %s""",
                (uuid.UUID(job_id),),
            )
            results = [dict(r) for r in cur.fetchall()]
            for r in results:
                r["image_id"] = str(r["image_id"])
            job["results"] = results
            if results:
                sm = results[0].get("sample_metrics")
                if isinstance(sm, str):
                    import json
                    sm = json.loads(sm)
                metrics = list(sm.keys()) if sm else []
                agg = {}
                for k in metrics:
                    vals = []
                    for r in results:
                        sm = r.get("sample_metrics")
                        if isinstance(sm, str):
                            import json
                            sm = json.loads(sm)
                        if sm and k in sm:
                            vals.append(sm[k])
                    agg[f"mean_{k}"] = round(sum(vals) / len(vals), 6) if vals else None
                job["aggregate"] = agg
            else:
                job["aggregate"] = None
            return job
    finally:
        conn.close()


def create_validation_job(dataset_slice: dict, simulator_run_id: str | None = None, model_ref: str | None = None) -> dict:
    """Insert job and return { job_id, status }."""
    conn = get_db()
    try:
        job_id = uuid.uuid4()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO core.validation_jobs (id, status, dataset_slice, simulator_run_id, model_ref)
                   VALUES (%s, 'queued', %s, %s, %s)""",
                (job_id, __import__("json").dumps(dataset_slice), uuid.UUID(simulator_run_id) if simulator_run_id else None, model_ref),
            )
        conn.commit()
        return {"job_id": str(job_id), "status": "queued"}
    finally:
        conn.close()


def run_validation_sync(job_id: str) -> dict | None:
    """
    Run the validation job to completion (sync). Returns full job with results, or None if job not found.
    Used for one-click / MYCA automation: submit then run in one request.
    """
    try:
        from scripts.myceliumseg.run_validation_job import run_job
        run_job(job_id)
        return get_job(job_id)
    except Exception:
        return get_job(job_id)  # still return current state (e.g. failed)


def build_router() -> "APIRouter":
    """Build FastAPI router for MyceliumSeg APIs."""
    if APIRouter is None:
        raise ImportError("FastAPI not installed")
    router = APIRouter(prefix="/myceliumseg", tags=["myceliumseg"])

    @router.get("/images")
    def list_images(
        species: list[str] | None = Query(None),
        medium: list[str] | None = Query(None),
        temperature_c: list[int] | None = Query(None),
        growth_stage: list[str] | None = Query(None),
        split: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ):
        try:
            return catalog_images(species=species, medium=medium, temperature_c=temperature_c, growth_stage=growth_stage, split=split, limit=limit, offset=offset)
        except Exception as e:
            raise HTTPException(status_code=503, detail=str(e))

    @router.get("/images/{image_id}/asset")
    def get_asset(image_id: str):
        """Return redirect or asset path; in production return signed URL."""
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT asset_path FROM core.myceliumseg_images WHERE id = %s", (uuid.UUID(image_id),))
                row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Image not found")
            return {"asset_url": row["asset_path"], "id": image_id}
        finally:
            conn.close()

    @router.post("/validation/jobs")
    def submit_validation_job(body: ValidationJobCreate):
        try:
            return create_validation_job(
                body.dataset_slice,
                simulator_run_id=body.simulator_run_id,
                model_ref=body.model_ref,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/validation/run")
    def run_validation_now(body: ValidationJobCreate):
        """
        One-click / full automation: create job, run to completion, return full results.
        Use this for minimal user input (one button) or MYCA-triggered experiments.
        """
        try:
            res = create_validation_job(
                body.dataset_slice,
                simulator_run_id=body.simulator_run_id,
                model_ref=body.model_ref,
            )
            job_id = res["job_id"]
            job = run_validation_sync(job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="Job not found after run")
            return job
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/validation/jobs/{job_id}")
    def job_status(job_id: str):
        job = get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    return router
