"""
Petri high-volume batch engine - February 20, 2026

Queue-based orchestration for thousands/millions of simulation iterations.
Chunked execution, resource caps, cancellation, and summary-only modes.
"""

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np

logger = logging.getLogger(__name__)

# Resource caps
MAX_ITERATIONS_PER_REQUEST = 1_000_000
CHUNK_SIZE = 1000
MAX_CONCURRENT_CHUNKS = 4
DEFAULT_TIMEOUT_PER_CHUNK = 60.0


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class BatchJob:
    job_id: str
    total_iterations: int
    dt: float
    summary_only: bool
    status: JobStatus = JobStatus.PENDING
    completed_iterations: int = 0
    chunks_done: int = 0
    result_summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    _cancelled: bool = False

    def cancel(self) -> None:
        self._cancelled = True
        self.status = JobStatus.CANCELLED


# In-memory job store (use Redis/DB for multi-instance)
_jobs: Dict[str, BatchJob] = {}
_job_lock = asyncio.Lock()


async def _run_chunk(
    petridishsim_url: str,
    fields: Dict[str, List[List[float]]],
    chunk_size: int,
    dt: float,
    diffusion_rates: Dict[str, float],
    reaction_params: Dict[str, Dict[str, float]],
) -> Tuple[Dict[str, List[List[float]]], Dict[str, Any]]:
    """Run one chunk of iterations and return updated fields + metrics summary."""
    for _ in range(chunk_size):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_PER_CHUNK) as client:
                r = await client.post(
                    f"{petridishsim_url.rstrip('/')}/chemical/step",
                    json={
                        "fields": fields,
                        "diffusion_rates": diffusion_rates,
                        "dt": dt,
                        "reaction_params": reaction_params,
                    },
                )
                r.raise_for_status()
                data = r.json()
                fields = data.get("fields", fields)
        except Exception as e:
            raise RuntimeError(f"Chunk step failed: {e}") from e

    metrics: Dict[str, float] = {}
    for name, grid in (fields or {}).items():
        arr = np.array(grid, dtype=np.float32)
        metrics[f"{name}_mean"] = float(np.mean(arr))
        metrics[f"{name}_max"] = float(np.max(arr))
    return fields, metrics


async def run_scale_batch(
    iterations: int,
    dt: float,
    initial_fields: Dict[str, List[List[float]]],
    summary_only: bool = True,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run high-volume batch in chunks. Returns job_id immediately if iterations > CHUNK_SIZE,
    otherwise runs synchronously.
    """
    iterations = min(MAX_ITERATIONS_PER_REQUEST, max(1, iterations))
    petridishsim_url = os.environ.get("PETRIDISHSIM_URL", "")
    if not petridishsim_url:
        return {"status": "error", "message": "PETRIDISHSIM_URL not configured"}

    jid = job_id or str(uuid.uuid4())
    job = BatchJob(
        job_id=jid,
        total_iterations=iterations,
        dt=dt,
        summary_only=summary_only,
        status=JobStatus.RUNNING,
    )
    async with _job_lock:
        _jobs[jid] = job

    # Run in background for large jobs
    if iterations > CHUNK_SIZE:
        asyncio.create_task(_execute_batch_job(job, petridishsim_url, initial_fields))
        return {
            "status": "queued",
            "job_id": jid,
            "total_iterations": iterations,
            "message": "Job running in background. Poll /batch/scale/{job_id} for status.",
        }

    # Small job: run synchronously
    try:
        diffusion_rates = {k: 0.1 for k in initial_fields}
        reaction_params = {k: {} for k in initial_fields}
        fields = initial_fields
        all_metrics: List[Dict[str, Any]] = [] if not summary_only else []
        agg_sum: Dict[str, float] = {}
        chunk_count = 0

        for chunk_start in range(0, iterations, CHUNK_SIZE):
            if job._cancelled:
                job.status = JobStatus.CANCELLED
                break
            chunk_len = min(CHUNK_SIZE, iterations - chunk_start)
            fields, metrics = await _run_chunk(
                petridishsim_url, fields, chunk_len, dt, diffusion_rates, reaction_params
            )
            job.completed_iterations += chunk_len
            job.chunks_done += 1
            chunk_count += 1
            for k, v in metrics.items():
                agg_sum[k] = agg_sum.get(k, 0) + v
            if not summary_only:
                all_metrics.append({"iteration": job.completed_iterations, "metrics": metrics})

        agg = {k: v / max(1, chunk_count) for k, v in agg_sum.items()} if agg_sum else {}
        job.result_summary = {"aggregate_metrics": agg, "sample_metrics": all_metrics[-5:] if all_metrics else []}
        job.status = JobStatus.COMPLETED
        return {"status": "ok", "job_id": jid, "result": job.result_summary}
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        return {"status": "error", "job_id": jid, "error": str(e)}


async def _execute_batch_job(
    job: BatchJob,
    petridishsim_url: str,
    initial_fields: Dict[str, List[List[float]]],
) -> None:
    """Background task to execute a large batch job."""
    diffusion_rates = {k: 0.1 for k in initial_fields}
    reaction_params = {k: {} for k in initial_fields}
    fields = initial_fields
    agg_sum: Dict[str, float] = {}
    chunk_count = 0
    sem = asyncio.Semaphore(MAX_CONCURRENT_CHUNKS)

    try:
        for chunk_start in range(0, job.total_iterations, CHUNK_SIZE):
            if job._cancelled:
                job.status = JobStatus.CANCELLED
                return
            chunk_len = min(CHUNK_SIZE, job.total_iterations - chunk_start)
            async with sem:
                fields, metrics = await _run_chunk(
                    petridishsim_url, fields, chunk_len, job.dt, diffusion_rates, reaction_params
                )
            job.completed_iterations += chunk_len
            job.chunks_done += 1
            chunk_count += 1
            for k, v in metrics.items():
                agg_sum[k] = agg_sum.get(k, 0) + v

        agg = {k: v / max(1, chunk_count) for k, v in agg_sum.items()} if agg_sum else {}
        job.result_summary = {"aggregate_metrics": agg, "completed_iterations": job.completed_iterations}
        job.status = JobStatus.COMPLETED
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        logger.exception("Scale batch job %s failed", job.job_id)


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get status of a batch job."""
    job = _jobs.get(job_id)
    if not job:
        return None
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "completed_iterations": job.completed_iterations,
        "total_iterations": job.total_iterations,
        "chunks_done": job.chunks_done,
        "result_summary": job.result_summary,
        "error": job.error,
        "progress_pct": 100.0 * job.completed_iterations / max(1, job.total_iterations),
    }


def cancel_job(job_id: str) -> bool:
    """Request cancellation of a batch job."""
    job = _jobs.get(job_id)
    if not job or job.status not in (JobStatus.PENDING, JobStatus.RUNNING):
        return False
    job.cancel()
    return True
