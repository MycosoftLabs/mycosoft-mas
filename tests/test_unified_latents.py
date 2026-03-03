"""
Tests for the Unified Latents agent and API router.

Covers the UnifiedLatentsAgent (v2 simulation agent) and the
/api/unified-latents/* HTTP endpoints.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from mycosoft_mas.agents.v2.simulation_agents import (
    UnifiedLatentsAgent,
    SIMULATION_AGENTS,
    get_simulation_agent,
)
from mycosoft_mas.agents.v2.scientific_agents import ScientificTask, TaskPriority


# ---------------------------------------------------------------------------
# Agent tests
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    return UnifiedLatentsAgent()


def _make_task(task_type: str, input_data: dict) -> ScientificTask:
    return ScientificTask(
        task_id=uuid4(),
        task_type=task_type,
        description=f"Test {task_type}",
        priority=TaskPriority.MEDIUM,
        input_data=input_data,
        created_at=datetime.now(timezone.utc),
    )


class TestUnifiedLatentsAgentInit:
    def test_agent_id(self, agent):
        assert agent.agent_id == "unified_latents_agent"

    def test_agent_name(self, agent):
        assert agent.name == "Unified Latents Agent"

    def test_description_mentions_arxiv(self, agent):
        assert "2602.17270" in agent.description

    def test_gpu_node_default(self, agent):
        # Default value when UNIFIED_LATENTS_GPU_NODE env var is unset
        assert agent.GPU_NODE is not None
        assert isinstance(agent.GPU_NODE, str)


class TestUnifiedLatentsRegistry:
    def test_registered_in_simulation_agents(self):
        assert "unified_latents" in SIMULATION_AGENTS

    def test_get_simulation_agent(self):
        a = get_simulation_agent("unified_latents")
        assert isinstance(a, UnifiedLatentsAgent)


class TestEncodeToLatent:
    @pytest.mark.asyncio
    async def test_encode(self, agent):
        task = _make_task("encode_to_latent", {
            "input_path": "/data/test.png",
            "checkpoint": "v1",
            "noise_level": 0.1,
        })
        result = await agent.execute_task(task)
        assert "latent_id" in result
        assert result["input_path"] == "/data/test.png"
        assert result["checkpoint"] == "v1"
        assert result["noise_level"] == 0.1


class TestDecodeFromLatent:
    @pytest.mark.asyncio
    async def test_decode(self, agent):
        task = _make_task("decode_from_latent", {
            "latent_id": "abc-123",
            "num_diffusion_steps": 100,
        })
        result = await agent.execute_task(task)
        assert "decode_id" in result
        assert result["latent_id"] == "abc-123"
        assert result["num_diffusion_steps"] == 100


class TestGenerateImage:
    @pytest.mark.asyncio
    async def test_generate(self, agent):
        task = _make_task("generate_image", {
            "prompt": "a photo of a mushroom",
            "resolution": 512,
            "num_samples": 2,
            "guidance_scale": 7.5,
            "num_diffusion_steps": 50,
            "checkpoint": "default",
        })
        result = await agent.execute_task(task)
        assert "generation_id" in result
        assert result["prompt"] == "a photo of a mushroom"
        assert result["num_samples"] == 2
        assert result["resolution"] == 512

    @pytest.mark.asyncio
    async def test_defaults(self, agent):
        task = _make_task("generate_image", {"prompt": "test"})
        result = await agent.execute_task(task)
        assert result["resolution"] == 512
        assert result["num_samples"] == 1


class TestGenerateVideo:
    @pytest.mark.asyncio
    async def test_generate(self, agent):
        task = _make_task("generate_video", {
            "prompt": "timelapse of mycelium growth",
            "resolution": 512,
            "num_frames": 32,
            "fps": 16,
        })
        result = await agent.execute_task(task)
        assert "generation_id" in result
        assert result["num_frames"] == 32
        assert result["fps"] == 16


class TestTrainModel:
    @pytest.mark.asyncio
    async def test_train(self, agent):
        task = _make_task("train_model", {
            "dataset": "imagenet-512",
            "batch_size": 32,
            "learning_rate": 1e-4,
            "max_steps": 1000,
            "noise_schedule": "cosine",
        })
        result = await agent.execute_task(task)
        assert "run_id" in result
        assert result["dataset"] == "imagenet-512"
        assert result["status"] == "queued"
        assert result["gpu_node"] == agent.GPU_NODE

    @pytest.mark.asyncio
    async def test_get_status_after_train(self, agent):
        # Launch a training run
        train_task = _make_task("train_model", {"dataset": "kinetics-600"})
        train_result = await agent.execute_task(train_task)
        run_id = train_result["run_id"]

        # Query its status
        status_task = _make_task("get_model_status", {"run_id": run_id})
        status_result = await agent.execute_task(status_task)
        assert status_result["run_id"] == run_id
        assert status_result["dataset"] == "kinetics-600"

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, agent):
        task = _make_task("get_model_status", {"run_id": "nonexistent"})
        result = await agent.execute_task(task)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_concurrent_training_runs(self, agent):
        """Multiple training runs can coexist on the same agent."""
        task_a = _make_task("train_model", {"dataset": "imagenet-512"})
        task_b = _make_task("train_model", {"dataset": "kinetics-600"})

        result_a = await agent.execute_task(task_a)
        result_b = await agent.execute_task(task_b)

        assert result_a["run_id"] != result_b["run_id"]

        status_a = await agent.execute_task(
            _make_task("get_model_status", {"run_id": result_a["run_id"]})
        )
        status_b = await agent.execute_task(
            _make_task("get_model_status", {"run_id": result_b["run_id"]})
        )
        assert status_a["dataset"] == "imagenet-512"
        assert status_b["dataset"] == "kinetics-600"


class TestEvaluateModel:
    @pytest.mark.asyncio
    async def test_evaluate(self, agent):
        task = _make_task("evaluate_model", {
            "checkpoint": "v1-500k",
            "dataset": "imagenet-512",
            "num_samples": 50_000,
            "metrics": ["fid", "psnr", "fvd"],
        })
        result = await agent.execute_task(task)
        assert "evaluation_id" in result
        assert "fid" in result["metrics"]
        assert "psnr" in result["metrics"]
        assert "fvd" in result["metrics"]


class TestUnknownTaskType:
    @pytest.mark.asyncio
    async def test_unknown(self, agent):
        task = _make_task("unknown_task", {})
        result = await agent.execute_task(task)
        assert "error" in result


# ---------------------------------------------------------------------------
# API router tests
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Create a FastAPI test client with the unified-latents router.

    Resets the module-level agent singleton so each test client gets
    a fresh agent instance (important for training-status tests).
    """
    import importlib
    import sys

    # Import the router module directly to avoid cascading deps from __init__
    spec = importlib.util.spec_from_file_location(
        "unified_latents_api",
        str(
            __import__("pathlib").Path(__file__).resolve().parent.parent
            / "mycosoft_mas"
            / "core"
            / "routers"
            / "unified_latents_api.py"
        ),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["unified_latents_api"] = mod
    spec.loader.exec_module(mod)

    # Reset the singleton so state doesn't leak between test classes
    mod._agent_instance = None

    router = mod.router

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestAPIHealth:
    def test_health(self, client):
        resp = client.get("/api/unified-latents/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_info(self, client):
        resp = client.get("/api/unified-latents/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["arxiv"] == "2602.17270"
        assert data["benchmarks"]["imagenet_512_fid"] == 1.4
        assert data["benchmarks"]["kinetics_600_fvd"] == 1.3

    def test_info_gpu_node_present(self, client):
        resp = client.get("/api/unified-latents/info")
        data = resp.json()
        assert "gpu_node" in data
        assert isinstance(data["gpu_node"], str)


class TestAPIGenerateImage:
    def test_generate_image(self, client):
        resp = client.post("/api/unified-latents/generate/image", json={
            "prompt": "a mushroom in a forest",
            "resolution": 256,
            "num_samples": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "generation_id" in data
        assert data["prompt"] == "a mushroom in a forest"

    def test_empty_prompt_rejected(self, client):
        resp = client.post("/api/unified-latents/generate/image", json={
            "prompt": "",
        })
        assert resp.status_code == 422


class TestAPIGenerateVideo:
    def test_generate_video(self, client):
        resp = client.post("/api/unified-latents/generate/video", json={
            "prompt": "mycelium growth timelapse",
            "num_frames": 16,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "generation_id" in data
        assert data["num_frames"] == 16

    def test_empty_prompt_rejected(self, client):
        resp = client.post("/api/unified-latents/generate/video", json={
            "prompt": "",
        })
        assert resp.status_code == 422


class TestAPIEncode:
    def test_encode(self, client):
        resp = client.post("/api/unified-latents/encode", json={
            "input_path": "/data/sample.png",
        })
        assert resp.status_code == 200
        assert "latent_id" in resp.json()

    def test_empty_path_rejected(self, client):
        resp = client.post("/api/unified-latents/encode", json={
            "input_path": "",
        })
        assert resp.status_code == 422


class TestAPIDecode:
    def test_decode(self, client):
        resp = client.post("/api/unified-latents/decode", json={
            "latent_id": "test-latent-id",
        })
        assert resp.status_code == 200
        assert "decode_id" in resp.json()

    def test_empty_latent_id_rejected(self, client):
        resp = client.post("/api/unified-latents/decode", json={
            "latent_id": "",
        })
        assert resp.status_code == 422


class TestAPITrain:
    def test_train(self, client):
        resp = client.post("/api/unified-latents/train", json={
            "dataset": "imagenet-512",
            "batch_size": 16,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert "run_id" in data

    def test_train_then_get_status(self, client):
        """POST /train then GET /train/{run_id} returns the same run."""
        train_resp = client.post("/api/unified-latents/train", json={
            "dataset": "kinetics-600",
        })
        assert train_resp.status_code == 200
        run_id = train_resp.json()["run_id"]

        status_resp = client.get(f"/api/unified-latents/train/{run_id}")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["run_id"] == run_id
        assert data["dataset"] == "kinetics-600"

    def test_get_status_not_found(self, client):
        resp = client.get("/api/unified-latents/train/nonexistent-run-id")
        assert resp.status_code == 404


class TestAPIEvaluate:
    def test_evaluate(self, client):
        resp = client.post("/api/unified-latents/evaluate", json={
            "checkpoint": "latest",
            "metrics": ["fid", "psnr"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "evaluation_id" in data
        assert "fid" in data["metrics"]
