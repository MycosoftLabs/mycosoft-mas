"""
Culture Vision AI Integration Client.

Petri dish image analysis: colony counting, contamination detection, growth rate
estimation, organism classification (bacteria, fungi, virus indicators).

Supports:
- OpenAI Vision API (cloud) for image understanding
- Optional local GPU endpoint (YOLO/SegFormer) via CULTURE_VISION_GPU_URL

Environment Variables:
    OPENAI_API_KEY: For cloud vision analysis
    CULTURE_VISION_GPU_URL: Optional local GPU service URL for YOLO/SegFormer
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

OPENAI_API_BASE = "https://api.openai.com/v1"

PETRI_ANALYSIS_PROMPT = """Analyze this petri dish or culture plate image. Provide a structured JSON response with:

1. colony_count: estimated number of visible colonies (integer)
2. contamination_detected: boolean - true if mold, foreign growth, or abnormal morphology detected
3. growth_stage: "sparse" | "moderate" | "confluent" | "overgrown"
4. organism_hint: "bacteria" | "fungi" | "mixed" | "unknown" based on colony morphology
5. notes: brief free-text observations (color, shape, distribution)
6. quality_score: 1-10 (10 = clear, well-lit, in-focus image)

Return ONLY valid JSON, no markdown or extra text."""


class CultureVisionClient:
    """Client for petri dish / culture plate image analysis."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", os.environ.get("OPENAI_API_KEY", ""))
        self.gpu_url = self.config.get("gpu_url", os.environ.get("CULTURE_VISION_GPU_URL", ""))
        self.timeout = self.config.get("timeout", 60)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def analyze_image_openai(
        self,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze petri dish image using OpenAI Vision API.

        Args:
            image_url: Public URL of the image
            image_base64: Base64-encoded image data (alternative to URL)
            prompt: Override default petri analysis prompt

        Returns:
            Parsed JSON analysis or None on failure
        """
        if not self.api_key:
            logger.warning("Culture Vision: OPENAI_API_KEY not set")
            return None
        if not image_url and not image_base64:
            return None

        content: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": prompt or PETRI_ANALYSIS_PROMPT,
            }
        ]
        if image_url:
            content.append({"type": "image_url", "image_url": {"url": image_url}})
        else:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                    },
                }
            )

        client = await self._get_client()
        try:
            r = await client.post(
                f"{OPENAI_API_BASE}/chat/completions",
                headers=self._headers(),
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": content}],
                    "max_tokens": 1024,
                },
            )
            if not r.is_success:
                logger.warning("OpenAI Vision request failed: %s", r.text[:200])
                return None
            data = r.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not text:
                return None
            # Try to extract JSON from response (model might wrap in markdown)
            text = text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(l for l in lines if not l.startswith("```") and l != "json")
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("Culture Vision: failed to parse OpenAI response: %s", e)
            return {"raw_response": text} if "text" in dir() else None
        except Exception as e:
            logger.warning("Culture Vision OpenAI analysis failed: %s", e)
            return None

    async def analyze_image_gpu(
        self,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze image via local GPU endpoint (YOLO/SegFormer).

        Expects POST to CULTURE_VISION_GPU_URL with JSON body:
        {"image_url": "..."} or {"image_base64": "..."}
        Returns: {"colony_count": int, "contamination": bool, "segmentation_mask_url": str?, ...}
        """
        if not self.gpu_url:
            return None
        if not image_url and not image_base64:
            return None

        client = await self._get_client()
        body: Dict[str, Any] = {}
        if image_url:
            body["image_url"] = image_url
        else:
            body["image_base64"] = image_base64

        try:
            r = await client.post(self.gpu_url, json=body)
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("Culture Vision GPU analysis failed: %s", e)
            return None

    async def analyze_image(
        self,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        prefer_gpu: bool = False,
    ) -> Dict[str, Any]:
        """
        Analyze petri dish image. Uses GPU endpoint if configured and prefer_gpu,
        otherwise falls back to OpenAI Vision.

        Returns:
            Analysis dict with colony_count, contamination_detected, growth_stage, etc.
        """
        if not image_url and not image_base64:
            return {"error": "No image provided"}

        result: Optional[Dict[str, Any]] = None
        if prefer_gpu and self.gpu_url:
            result = await self.analyze_image_gpu(image_url=image_url, image_base64=image_base64)
        if result is None and self.api_key:
            result = await self.analyze_image_openai(image_url=image_url, image_base64=image_base64)
        if result is None and not prefer_gpu and self.gpu_url:
            result = await self.analyze_image_gpu(image_url=image_url, image_base64=image_base64)

        if result is None:
            return {
                "error": "No analysis backend available (OPENAI_API_KEY or CULTURE_VISION_GPU_URL)"
            }
        return result

    async def health_check(self) -> Dict[str, Any]:
        """Check availability of vision backends."""
        ok = bool(self.api_key or self.gpu_url)
        return {
            "status": "healthy" if ok else "unconfigured",
            "openai_available": bool(self.api_key),
            "gpu_available": bool(self.gpu_url),
        }
