from __future__ import annotations

import os
from typing import Any, Dict

import httpx


class NLMBridge:
    def __init__(self, base_url: str | None = None, timeout_s: float = 20.0) -> None:
        self.base_url = (base_url or "http://192.168.0.189:8000/api/mindex").rstrip("/")
        self.timeout_s = timeout_s
        self.internal_token = os.getenv("MINDEX_INTERNAL_TOKEN", "").strip()
        self.api_key = os.getenv("MINDEX_API_KEY", "").strip()

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.internal_token:
            headers["X-Internal-Token"] = self.internal_token
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(f"{self.base_url}{path}", json=payload, headers=self._headers())
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {"result": data}

    async def classify_acoustic(self, observation: Any) -> Dict[str, Any]:
        payload = observation.model_dump() if hasattr(observation, "model_dump") else dict(observation)
        return await self._post("/nlm/classify/acoustic", payload)

    async def predict_sonar(self, environment: Dict[str, Any]) -> Dict[str, Any]:
        return await self._post("/nlm/predict/sonar-performance", environment)

    async def assess_atmospheric(self, observation: Any) -> Dict[str, Any]:
        payload = observation.model_dump() if hasattr(observation, "model_dump") else dict(observation)
        return await self._post("/nlm/assess/tactical", {"domain": "atmosphere", "observation": payload})

    async def predict_dispersion(self, release: Dict[str, Any]) -> Dict[str, Any]:
        return await self._post("/nlm/assess/tactical", {"domain": "atmosphere-dispersion", "release": release})

    async def assess_biological(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        return await self._post("/nlm/assess/tactical", {"domain": "biosphere", "observation": observation})

    async def generate_intel_product(self, assessment: Any, context: str = "") -> Dict[str, Any]:
        data = assessment.model_dump() if hasattr(assessment, "model_dump") else dict(assessment)
        title = data.get("classification", "Assessment")
        body = data.get("recommendation") or data.get("summary") or "No summary provided"
        return {
            "title": f"FUSARIUM {title}".strip(),
            "body": f"{body}\n\nContext: {context}".strip(),
            "domain": data.get("domain", "multi-domain"),
            "classification": data.get("classification", "CUI"),
            "confidence": float(data.get("confidence", 0.5)),
            "sources": [str(x) for x in data.get("entities", [])],
            "tags": [data.get("domain", "multi-domain")],
        }
