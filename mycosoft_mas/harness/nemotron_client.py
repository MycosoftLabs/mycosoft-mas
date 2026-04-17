"""Nemotron (VoiceChat / in-house LLM) client — OpenAI-compatible streaming."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from mycosoft_mas.harness.config import HarnessConfig
from mycosoft_mas.harness.turbo_quant import TurboQuantCompressor

logger = logging.getLogger(__name__)


class NemotronClient:
    """Async LLM client with optional turbo-quant wrapping."""

    def __init__(self, config: HarnessConfig) -> None:
        self._base = config.nemotron_base_url
        self._model = config.nemotron_model
        self._api_key = config.nemotron_api_key
        self._compressor = (
            TurboQuantCompressor(nda_mode=config.turbo_quant_nda_mode)
            if config.enable_turbo_quant
            else None
        )
        self._quant_enabled = config.enable_turbo_quant

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        stream: bool = False,
    ) -> AsyncIterator[str]:
        """Yield token chunks (async generator). Non-stream returns one chunk."""
        body = self._prepare_body(prompt, system, stream)
        url = f"{self._base}/v1/chat/completions"
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            if stream:
                async with client.stream("POST", url, headers=self._headers(), json=body) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or line.startswith(":"):
                            continue
                        if line.startswith("data: "):
                            payload = line[6:].strip()
                            if payload == "[DONE]":
                                break
                            try:
                                obj = json.loads(payload)
                                delta = (
                                    obj.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content")
                                )
                                if delta:
                                    yield delta
                            except json.JSONDecodeError:
                                continue
            else:
                resp = await client.post(url, headers=self._headers(), json=body)
                resp.raise_for_status()
                data = resp.json()
                text = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                if text:
                    yield text

    def _prepare_body(self, prompt: str, system: str | None, stream: bool) -> dict[str, Any]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        content = prompt
        if self._quant_enabled and self._compressor:
            # Measure placeholder compression cost only; wire bytes to a quant-aware gateway under NDA.
            _ = self._compressor.compress(prompt)
        messages.append({"role": "user", "content": content})
        return {
            "model": self._model,
            "messages": messages,
            "stream": stream,
        }


def nemotron_client_from_env() -> NemotronClient:
    return NemotronClient(HarnessConfig.from_env())
