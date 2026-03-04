"""
Distributed GPU Compute Client

Provides access to cloud GPU rental services:
- Lambda Labs -- GPU cloud instances
- RunPod -- serverless GPU, pods
- Vast.ai -- GPU marketplace
- Together.ai -- inference API

Env vars:
    LAMBDA_API_KEY     -- Lambda Labs API key
    RUNPOD_API_KEY     -- RunPod API key
    VASTAI_API_KEY     -- Vast.ai API key
    TOGETHER_API_KEY   -- Together.ai API key
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

LAMBDA_BASE = "https://cloud.lambdalabs.com/api/v1"
RUNPOD_BASE = "https://api.runpod.io/v2"
RUNPOD_GQL = "https://api.runpod.io/graphql"
VASTAI_BASE = "https://console.vast.ai/api/v0"
TOGETHER_BASE = "https://api.together.xyz/v1"


class GpuComputeClient:
    """Multi-provider GPU compute client."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.lambda_key = self.config.get("lambda_api_key") or os.getenv("LAMBDA_API_KEY", "")
        self.runpod_key = self.config.get("runpod_api_key") or os.getenv("RUNPOD_API_KEY", "")
        self.vastai_key = self.config.get("vastai_api_key") or os.getenv("VASTAI_API_KEY", "")
        self.together_key = self.config.get("together_api_key") or os.getenv("TOGETHER_API_KEY", "")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "lambda_key_set": bool(self.lambda_key),
            "runpod_key_set": bool(self.runpod_key),
            "vastai_key_set": bool(self.vastai_key),
            "together_key_set": bool(self.together_key),
            "ts": datetime.utcnow().isoformat(),
        }

    # -- Lambda Labs ----------------------------------------------------------

    async def lambda_instance_types(self) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(
            f"{LAMBDA_BASE}/instance-types",
            headers={"Authorization": f"Bearer {self.lambda_key}"},
        )
        r.raise_for_status()
        return r.json()

    async def lambda_instances(self) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(
            f"{LAMBDA_BASE}/instances",
            headers={"Authorization": f"Bearer {self.lambda_key}"},
        )
        r.raise_for_status()
        return r.json()

    async def lambda_launch(
        self, instance_type: str, region: str, ssh_key_names: List[str], quantity: int = 1
    ) -> Dict[str, Any]:
        c = await self._http()
        r = await c.post(
            f"{LAMBDA_BASE}/instance-operations/launch",
            headers={"Authorization": f"Bearer {self.lambda_key}"},
            json={
                "instance_type_name": instance_type,
                "region_name": region,
                "ssh_key_names": ssh_key_names,
                "quantity": quantity,
            },
        )
        r.raise_for_status()
        return r.json()

    async def lambda_terminate(self, instance_ids: List[str]) -> Dict[str, Any]:
        c = await self._http()
        r = await c.post(
            f"{LAMBDA_BASE}/instance-operations/terminate",
            headers={"Authorization": f"Bearer {self.lambda_key}"},
            json={"instance_ids": instance_ids},
        )
        r.raise_for_status()
        return r.json()

    # -- RunPod ---------------------------------------------------------------

    async def runpod_gpus(self) -> Dict[str, Any]:
        c = await self._http()
        r = await c.post(
            RUNPOD_GQL,
            headers={"Authorization": f"Bearer {self.runpod_key}"},
            json={"query": "{ gpuTypes { id displayName memoryInGb } }"},
        )
        r.raise_for_status()
        return r.json()

    async def runpod_pods(self) -> Dict[str, Any]:
        c = await self._http()
        r = await c.post(
            RUNPOD_GQL,
            headers={"Authorization": f"Bearer {self.runpod_key}"},
            json={"query": "{ myself { pods { id name runtime { gpus { id } } } } }"},
        )
        r.raise_for_status()
        return r.json()

    async def runpod_serverless_run(self, endpoint_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        c = await self._http()
        r = await c.post(
            f"{RUNPOD_BASE}/{endpoint_id}/run",
            headers={"Authorization": f"Bearer {self.runpod_key}"},
            json={"input": payload},
        )
        r.raise_for_status()
        return r.json()

    async def runpod_serverless_status(self, endpoint_id: str, job_id: str) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(
            f"{RUNPOD_BASE}/{endpoint_id}/status/{job_id}",
            headers={"Authorization": f"Bearer {self.runpod_key}"},
        )
        r.raise_for_status()
        return r.json()

    # -- Vast.ai --------------------------------------------------------------

    async def vastai_offers(self, num_gpus: int = 1, gpu_name: str = "RTX_4090") -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(
            f"{VASTAI_BASE}/bundles",
            headers={"Authorization": f"Bearer {self.vastai_key}"},
            params={"q": f"num_gpus>={num_gpus} gpu_name={gpu_name} rentable=true"},
        )
        r.raise_for_status()
        return r.json()

    async def vastai_instances(self) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(
            f"{VASTAI_BASE}/instances",
            headers={"Authorization": f"Bearer {self.vastai_key}"},
        )
        r.raise_for_status()
        return r.json()

    # -- Together.ai ----------------------------------------------------------

    async def together_models(self) -> List[Dict[str, Any]]:
        c = await self._http()
        r = await c.get(
            f"{TOGETHER_BASE}/models",
            headers={"Authorization": f"Bearer {self.together_key}"},
        )
        r.raise_for_status()
        return r.json()

    async def together_inference(
        self, model: str, prompt: str, max_tokens: int = 512, temperature: float = 0.7
    ) -> Dict[str, Any]:
        c = await self._http()
        r = await c.post(
            f"{TOGETHER_BASE}/completions",
            headers={"Authorization": f"Bearer {self.together_key}"},
            json={"model": model, "prompt": prompt, "max_tokens": max_tokens, "temperature": temperature},
        )
        r.raise_for_status()
        return r.json()

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
