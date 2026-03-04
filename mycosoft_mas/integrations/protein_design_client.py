"""
Protein Design Integration Client.

ESMFold via Hugging Face Inference API, RFdiffusion via NVIDIA NIM (optional).
Used by ProteinDesignAgent and scientific simulation agents.

Environment Variables:
    HUGGINGFACE_TOKEN: For ESMFold inference
    NVIDIA_NIM_URL: Optional NVIDIA NIM RFdiffusion endpoint
    NGC_API_KEY or NVIDIA_API_KEY: For NVIDIA NIM (when using RFdiffusion)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

ESMFOLD_MODEL = "facebook/esmfold_v1"
HF_INFERENCE_BASE = "https://api-inference.huggingface.co"


class ProteinDesignClient:
    """Client for ESMFold (Hugging Face) and RFdiffusion (NVIDIA NIM)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.hf_token = self.config.get("hf_token", os.environ.get("HUGGINGFACE_TOKEN", ""))
        self.nim_url = self.config.get("nim_url", os.environ.get("NVIDIA_NIM_URL", ""))
        self.ngc_key = self.config.get("ngc_key", os.environ.get("NGC_API_KEY", os.environ.get("NVIDIA_API_KEY", "")))
        self.timeout = self.config.get("timeout", 300)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def esmfold_predict(self, sequence: str) -> Optional[Dict[str, Any]]:
        """
        Predict protein structure using ESMFold via Hugging Face Inference API.
        Input: amino acid sequence (single-letter codes).
        Returns inference result (may include pdb_content, coordinates, or error).
        """
        if not self.hf_token:
            logger.warning("ProteinDesignClient: HUGGINGFACE_TOKEN required for ESMFold")
            return None
        if not sequence or len(sequence) > 400:
            return {"error": "Sequence required, max ~400 residues for Inference API"}
        client = await self._get_client()
        try:
            r = await client.post(
                f"{HF_INFERENCE_BASE}/models/{ESMFOLD_MODEL}",
                headers={"Authorization": f"Bearer {self.hf_token}"},
                json={"inputs": sequence},
            )
            if r.is_success:
                data = r.json()
                if isinstance(data, dict):
                    return data
                return {"result": data}
            return {"error": r.text[:500], "status_code": r.status_code}
        except Exception as e:
            logger.warning("ProteinDesignClient esmfold_predict failed: %s", e)
            return {"error": str(e)}

    async def rfdiffusion_scaffold(
        self,
        pdb_content: Optional[str] = None,
        pdb_url: Optional[str] = None,
        task: str = "scaffold",
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Run RFdiffusion via NVIDIA NIM for scaffolding or binder design.
        Requires NVIDIA_NIM_URL and NGC_API_KEY.
        """
        if not self.nim_url or not self.ngc_key:
            return {
                "error": "NVIDIA_NIM_URL and NGC_API_KEY required for RFdiffusion. "
                "See https://docs.api.nvidia.com/nim/reference/ipd-rfdiffusion",
            }
        payload: Dict[str, Any] = {"task": task, **kwargs}
        if pdb_content:
            payload["pdb_content"] = pdb_content
        if pdb_url:
            payload["pdb_url"] = pdb_url
        client = await self._get_client()
        try:
            r = await client.post(
                self.nim_url,
                headers={"Authorization": f"Bearer {self.ngc_key}"},
                json=payload,
            )
            if r.is_success:
                return r.json()
            return {"error": r.text[:500], "status_code": r.status_code}
        except Exception as e:
            logger.warning("ProteinDesignClient rfdiffusion_scaffold failed: %s", e)
            return {"error": str(e)}

    async def predict_structure(self, sequence: str) -> Dict[str, Any]:
        """Unified entry: predict structure from sequence (uses ESMFold)."""
        result = await self.esmfold_predict(sequence)
        if result is None:
            return {"error": "ESMFold client not configured", "sequence_length": len(sequence)}
        result["sequence_length"] = len(sequence)
        return result

    async def design_binder(
        self,
        target_pdb: Optional[str] = None,
        target_pdb_url: Optional[str] = None,
        hotspot_residues: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Design a binder for a target structure (uses RFdiffusion when NIM configured)."""
        if self.nim_url and self.ngc_key:
            return await self.rfdiffusion_scaffold(
                pdb_content=target_pdb,
                pdb_url=target_pdb_url,
                task="binder",
                hotspot_residues=hotspot_residues or [],
            ) or {"error": "RFdiffusion request failed"}
        return {
            "error": "RFdiffusion requires NVIDIA_NIM_URL and NGC_API_KEY. "
            "For ESMFold structure prediction, use predict_structure with sequence.",
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check ESMFold (HF) and optionally RFdiffusion (NIM) availability."""
        out: Dict[str, Any] = {"esmfold": "unconfigured", "rfdiffusion": "unconfigured"}
        if self.hf_token:
            try:
                r = await (await self._get_client()).post(
                    f"{HF_INFERENCE_BASE}/models/{ESMFOLD_MODEL}",
                    headers={"Authorization": f"Bearer {self.hf_token}"},
                    json={"inputs": "MKFL"},  # short test sequence
                )
                out["esmfold"] = "healthy" if r.status_code in (200, 503) else "unhealthy"
            except Exception as e:
                out["esmfold"] = f"error: {e}"
        if self.nim_url and self.ngc_key:
            out["rfdiffusion"] = "configured"
        return out
