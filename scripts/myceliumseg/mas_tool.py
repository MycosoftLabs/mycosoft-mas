"""
MYCA/MAS-callable MyceliumSeg validation. Run experiments with minimal input.
Used by voice_tools_api (run_myceliumseg_validation) and by API POST /validation/run.
"""
from __future__ import annotations

import os
import sys
from typing import Any

# Ensure repo root on path
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(os.path.dirname(_here))
if _root not in sys.path:
    sys.path.insert(0, _root)


def run_myceliumseg_validation(
    dataset_slice: dict[str, Any] | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Create a validation job, run it to completion, return full results.
    Callable by MYCA or UI with minimal input.
    """
    from scripts.myceliumseg.api_routes import (
        create_validation_job,
        run_validation_sync,
        get_job,
    )
    slice_cfg = dataset_slice or {"limit": limit}
    if "limit" not in slice_cfg:
        slice_cfg["limit"] = limit
    res = create_validation_job(slice_cfg)
    job_id = res["job_id"]
    run_validation_sync(job_id)
    job = get_job(job_id)
    return job or {"job_id": job_id, "status": "unknown", "results": [], "aggregate": None}


async def run_myceliumseg_validation_async(
    dataset_slice: dict[str, Any] | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Async wrapper for use in FastAPI; runs sync in executor to avoid blocking."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: run_myceliumseg_validation(dataset_slice=dataset_slice, limit=limit),
    )
