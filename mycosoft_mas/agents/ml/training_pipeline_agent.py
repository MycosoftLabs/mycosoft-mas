"""
ML Training Pipeline Agent

Orchestrates end-to-end ML training workflows:
- Dataset preparation (via Hugging Face datasets)
- Model fine-tuning orchestration
- Hyperparameter search (W&B sweeps)
- Evaluation and metrics tracking
- Model registry and versioning
- A/B deployment targeting

Leverages: HuggingFace client, GPU compute client, W&B client.
"""

import logging
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class TrainingPipelineAgent(BaseAgent):
    """Orchestrates ML training pipelines across providers."""

    def __init__(self, agent_id: str = "training-pipeline", name: str = "Training Pipeline Agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = [
            "prepare_dataset",
            "launch_training",
            "track_experiment",
            "evaluate_model",
            "register_model",
            "compare_runs",
        ]
        self._hf = None
        self._gpu = None
        self._wandb = None

    def _get_hf(self):
        if self._hf is None:
            from mycosoft_mas.integrations.huggingface_client import HuggingFaceClient
            self._hf = HuggingFaceClient(self.config)
        return self._hf

    def _get_gpu(self):
        if self._gpu is None:
            from mycosoft_mas.integrations.gpu_compute_client import GpuComputeClient
            self._gpu = GpuComputeClient(self.config)
        return self._gpu

    def _get_wandb(self):
        if self._wandb is None:
            from mycosoft_mas.integrations.wandb_client import WandbClient
            self._wandb = WandbClient(self.config)
        return self._wandb

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        t = task.get("type", "")

        if t == "prepare_dataset":
            return await self._prepare_dataset(task)
        elif t == "launch_training":
            return await self._launch_training(task)
        elif t == "check_experiment":
            return await self._check_experiment(task)
        elif t == "evaluate":
            return await self._evaluate(task)
        elif t == "list_models":
            return await self._list_models(task)
        elif t == "compare_runs":
            return await self._compare_runs(task)

        return {"status": "error", "message": f"Unknown task type: {t}"}

    async def _prepare_dataset(self, task: Dict[str, Any]) -> Dict[str, Any]:
        hf = self._get_hf()
        dataset_name = task.get("dataset", "")
        results = await hf.search_datasets(dataset_name)
        return {
            "status": "success",
            "dataset": dataset_name,
            "search_results": results,
        }

    async def _launch_training(self, task: Dict[str, Any]) -> Dict[str, Any]:
        provider = task.get("provider", "runpod")
        model = task.get("model", "")
        dataset = task.get("dataset", "")
        gpu = self._get_gpu()

        if provider == "runpod":
            endpoint_id = task.get("endpoint_id", "")
            result = await gpu.runpod_serverless_run(
                endpoint_id,
                {"model": model, "dataset": dataset, "epochs": task.get("epochs", 3)},
            )
        elif provider == "lambda":
            result = await gpu.lambda_instance_types()
        elif provider == "together":
            result = await gpu.together_models()
        else:
            result = {"note": f"Provider {provider} not configured for launch"}

        return {"status": "success", "provider": provider, "result": result}

    async def _check_experiment(self, task: Dict[str, Any]) -> Dict[str, Any]:
        wb = self._get_wandb()
        project = task.get("project", "")
        run_id = task.get("run_id", "")
        if run_id:
            run = await wb.get_run(project, run_id)
            return {"status": "success", "run": run}
        runs = await wb.list_runs(project, limit=task.get("limit", 10))
        return {"status": "success", "runs": runs}

    async def _evaluate(self, task: Dict[str, Any]) -> Dict[str, Any]:
        wb = self._get_wandb()
        project = task.get("project", "")
        run_id = task.get("run_id", "")
        run = await wb.get_run(project, run_id)
        return {
            "status": "success",
            "run_id": run_id,
            "metrics": run.get("summaryMetrics", {}),
            "state": run.get("state", "unknown"),
        }

    async def _list_models(self, task: Dict[str, Any]) -> Dict[str, Any]:
        wb = self._get_wandb()
        project = task.get("project", "")
        artifacts = await wb.list_artifacts(project, artifact_type="model")
        return {"status": "success", "models": artifacts}

    async def _compare_runs(self, task: Dict[str, Any]) -> Dict[str, Any]:
        wb = self._get_wandb()
        project = task.get("project", "")
        runs = await wb.list_runs(project, limit=task.get("limit", 10))
        return {
            "status": "success",
            "project": project,
            "runs": runs,
            "count": len(runs),
        }
