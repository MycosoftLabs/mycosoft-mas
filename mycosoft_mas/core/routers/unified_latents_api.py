"""
Unified Latents (UL) API Router

HTTP endpoints for image and video generation using the Unified Latents
framework (Heek et al. 2026, arXiv 2602.17270).

UL jointly regularises latent representations with a diffusion prior and
decodes them with a diffusion model, yielding SOTA quality on both images
(FID 1.4 on ImageNet-512) and video (FVD 1.3 on Kinetics-600).

All heavy inference is dispatched to the GPU node (192.168.0.190).
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/unified-latents", tags=["unified-latents"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class GenerateImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Text prompt for image generation")
    resolution: int = Field(default=512, ge=64, le=2048)
    num_samples: int = Field(default=1, ge=1, le=16)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=30.0)
    num_diffusion_steps: int = Field(default=50, ge=1, le=1000)
    checkpoint: str = Field(default="default")


class GenerateVideoRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Text prompt for video generation")
    resolution: int = Field(default=512, ge=64, le=2048)
    num_frames: int = Field(default=16, ge=4, le=128)
    fps: int = Field(default=8, ge=1, le=60)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=30.0)
    num_diffusion_steps: int = Field(default=50, ge=1, le=1000)
    checkpoint: str = Field(default="default")


class EncodeRequest(BaseModel):
    input_path: str = Field(..., min_length=1, description="Path to image or video to encode")
    checkpoint: str = Field(default="default")
    noise_level: float = Field(default=0.0, ge=0.0, le=1.0)


class DecodeRequest(BaseModel):
    latent_id: str = Field(..., min_length=1, description="Latent representation ID to decode")
    num_diffusion_steps: int = Field(default=50, ge=1, le=1000)


class TrainModelRequest(BaseModel):
    dataset: str = Field(default="imagenet-512")
    batch_size: int = Field(default=64, ge=1, le=512)
    learning_rate: float = Field(default=1e-4, gt=0)
    max_steps: int = Field(default=500_000, ge=1)
    noise_schedule: str = Field(default="cosine")
    latent_channels: int = Field(default=4, ge=1, le=32)
    resume_from: Optional[str] = None


class EvaluateModelRequest(BaseModel):
    checkpoint: str = Field(..., min_length=1)
    dataset: str = Field(default="imagenet-512")
    num_samples: int = Field(default=50_000, ge=100)
    metrics: List[str] = Field(default=["fid", "psnr"])


# ---------------------------------------------------------------------------
# Agent accessor
# ---------------------------------------------------------------------------


def _get_agent():
    """Lazily instantiate the UnifiedLatentsAgent."""
    from mycosoft_mas.agents.v2.simulation_agents import UnifiedLatentsAgent

    return UnifiedLatentsAgent()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
async def health():
    """Check if the Unified Latents API is available."""
    return {"status": "healthy", "service": "unified-latents"}


@router.get("/info")
async def info():
    """Return metadata about the Unified Latents framework."""
    return {
        "framework": "Unified Latents (UL)",
        "paper": "Heek et al. 2026 - 'Unified Latents: How to train your latents'",
        "arxiv": "2602.17270",
        "capabilities": [
            "encode_to_latent",
            "decode_from_latent",
            "generate_image",
            "generate_video",
            "train_model",
            "evaluate_model",
        ],
        "benchmarks": {
            "imagenet_512_fid": 1.4,
            "kinetics_600_fvd": 1.3,
        },
        "gpu_node": "192.168.0.190",
    }


@router.post("/generate/image")
async def generate_image(request: GenerateImageRequest):
    """Generate images using the Unified Latents diffusion pipeline."""
    from datetime import datetime, timezone
    from uuid import uuid4 as _uuid4

    from mycosoft_mas.agents.v2.scientific_agents import ScientificTask, TaskPriority

    agent = _get_agent()
    task = ScientificTask(
        task_id=_uuid4(),
        task_type="generate_image",
        description=f"Generate image: {request.prompt[:80]}",
        priority=TaskPriority.HIGH,
        input_data=request.model_dump(),
        created_at=datetime.now(timezone.utc),
    )
    result = await agent.execute_task(task)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/generate/video")
async def generate_video(request: GenerateVideoRequest):
    """Generate video using the Unified Latents diffusion pipeline."""
    from datetime import datetime, timezone
    from uuid import uuid4 as _uuid4

    from mycosoft_mas.agents.v2.scientific_agents import ScientificTask, TaskPriority

    agent = _get_agent()
    task = ScientificTask(
        task_id=_uuid4(),
        task_type="generate_video",
        description=f"Generate video: {request.prompt[:80]}",
        priority=TaskPriority.HIGH,
        input_data=request.model_dump(),
        created_at=datetime.now(timezone.utc),
    )
    result = await agent.execute_task(task)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/encode")
async def encode_to_latent(request: EncodeRequest):
    """Encode an image or video into the unified latent space."""
    from datetime import datetime, timezone
    from uuid import uuid4 as _uuid4

    from mycosoft_mas.agents.v2.scientific_agents import ScientificTask, TaskPriority

    agent = _get_agent()
    task = ScientificTask(
        task_id=_uuid4(),
        task_type="encode_to_latent",
        description=f"Encode to latent: {request.input_path}",
        priority=TaskPriority.MEDIUM,
        input_data=request.model_dump(),
        created_at=datetime.now(timezone.utc),
    )
    result = await agent.execute_task(task)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/decode")
async def decode_from_latent(request: DecodeRequest):
    """Decode a latent representation back to pixel space."""
    from datetime import datetime, timezone
    from uuid import uuid4 as _uuid4

    from mycosoft_mas.agents.v2.scientific_agents import ScientificTask, TaskPriority

    agent = _get_agent()
    task = ScientificTask(
        task_id=_uuid4(),
        task_type="decode_from_latent",
        description=f"Decode latent: {request.latent_id}",
        priority=TaskPriority.MEDIUM,
        input_data=request.model_dump(),
        created_at=datetime.now(timezone.utc),
    )
    result = await agent.execute_task(task)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/train")
async def train_model(request: TrainModelRequest):
    """Launch a Unified Latents training run on the GPU node."""
    from datetime import datetime, timezone
    from uuid import uuid4 as _uuid4

    from mycosoft_mas.agents.v2.scientific_agents import ScientificTask, TaskPriority

    agent = _get_agent()
    task = ScientificTask(
        task_id=_uuid4(),
        task_type="train_model",
        description=f"Train UL model on {request.dataset}",
        priority=TaskPriority.HIGH,
        input_data=request.model_dump(),
        created_at=datetime.now(timezone.utc),
    )
    result = await agent.execute_task(task)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/train/{run_id}")
async def get_training_status(run_id: str):
    """Get status of a training run."""
    from datetime import datetime, timezone
    from uuid import uuid4 as _uuid4

    from mycosoft_mas.agents.v2.scientific_agents import ScientificTask, TaskPriority

    agent = _get_agent()
    task = ScientificTask(
        task_id=_uuid4(),
        task_type="get_model_status",
        description=f"Get training status: {run_id}",
        priority=TaskPriority.LOW,
        input_data={"run_id": run_id},
        created_at=datetime.now(timezone.utc),
    )
    result = await agent.execute_task(task)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/evaluate")
async def evaluate_model(request: EvaluateModelRequest):
    """Evaluate a UL checkpoint computing FID, FVD, PSNR metrics."""
    from datetime import datetime, timezone
    from uuid import uuid4 as _uuid4

    from mycosoft_mas.agents.v2.scientific_agents import ScientificTask, TaskPriority

    agent = _get_agent()
    task = ScientificTask(
        task_id=_uuid4(),
        task_type="evaluate_model",
        description=f"Evaluate checkpoint: {request.checkpoint}",
        priority=TaskPriority.MEDIUM,
        input_data=request.model_dump(),
        created_at=datetime.now(timezone.utc),
    )
    result = await agent.execute_task(task)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
