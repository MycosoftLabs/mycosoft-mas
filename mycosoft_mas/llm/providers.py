from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from prometheus_client import Counter, Histogram

from mycosoft_mas.config.runtime_settings import RuntimeSettings


class LLMError(RuntimeError):
    """LLM provider level error."""


@dataclass
class LLMResult:
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    raw: Optional[Dict[str, Any]] = None


class BaseLLMProvider:
    name: str

    async def chat(self, messages: List[Dict[str, str]], *, model: Optional[str] = None, **kwargs) -> LLMResult:
        raise NotImplementedError

    async def embed(self, inputs: List[str], *, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str, default_model: str, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout
        self.name = "openai"

    async def chat(self, messages: List[Dict[str, str]], *, model: Optional[str] = None, **kwargs) -> LLMResult:
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
            "tools": kwargs.get("tools"),
            "tool_choice": kwargs.get("tool_choice"),
        }
        return await self._post("/chat/completions", payload)

    async def embed(self, inputs: List[str], *, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        payload = {
            "model": model or self.default_model,
            "input": inputs,
        }
        result = await self._post("/embeddings", payload)
        return result.raw or {}

    async def _post(self, path: str, payload: Dict[str, Any]) -> LLMResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}{path}"
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    data = await resp.json()
                    if resp.status >= 400:
                        raise LLMError(data.get("error", {}).get("message", f"OpenAI error {resp.status}"))
                    choice = (data.get("choices") or [{}])[0]
                    message = choice.get("message", {})
                    content = message.get("content") or ""
                    return LLMResult(
                        content=content,
                        provider=self.name,
                        model=data.get("model", payload.get("model")),
                        usage=data.get("usage"),
                        raw=data,
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise LLMError(str(exc)) from exc


class OpenAICompatibleProvider(OpenAIProvider):
    """OpenAI-compatible endpoints such as LiteLLM, vLLM, or Ollama-proxy."""

    def __init__(self, api_key: str, base_url: str, default_model: str, timeout: int = 30):
        super().__init__(api_key=api_key, base_url=base_url, default_model=default_model, timeout=timeout)
        self.name = "openai_compatible"


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, default_model: str, timeout: int = 30):
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout
        self.name = "gemini"

    async def chat(self, messages: List[Dict[str, str]], *, model: Optional[str] = None, **kwargs) -> LLMResult:
        # Gemini expects a single prompt list; we flatten the message content.
        prompt = "\n".join([msg.get("content", "") for msg in messages if msg.get("content")])
        target_model = model or self.default_model
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent"
            f"?key={self.api_key}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(url, json=payload) as resp:
                    data = await resp.json()
                    if resp.status >= 400:
                        message = data.get("error", {}).get("message", f"Gemini error {resp.status}")
                        raise LLMError(message)
                    candidates = data.get("candidates") or [{}]
                    parts = (candidates[0].get("content", {}).get("parts") or [{}])
                    content = parts[0].get("text", "")
                    return LLMResult(
                        content=content,
                        provider=self.name,
                        model=target_model,
                        usage=data.get("usageMetadata"),
                        raw=data,
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise LLMError(str(exc)) from exc


class LLMRouter:
    """
    Routes requests to providers based on the model registry and runtime settings.
    Supports basic fallback to the configured fallback_model role.
    """

    REQUEST_COUNT = Counter("llm_requests_total", "LLM chat requests", ["provider", "model", "status"])
    REQUEST_LATENCY = Histogram("llm_request_duration_seconds", "LLM chat latency seconds", ["provider", "model"])

    def __init__(self, settings: RuntimeSettings):
        self.settings = settings
        self.registry = settings.model_registry
        self.providers: Dict[str, BaseLLMProvider] = self._build_providers()

    def _build_providers(self) -> Dict[str, BaseLLMProvider]:
        providers: Dict[str, BaseLLMProvider] = {}
        for key, cfg in self.registry.providers.items():
            base_url = cfg.base_url or self.settings.llm_base_url or "https://api.openai.com/v1"
            api_key = cfg.api_key or self.settings.llm_api_key or ""
            provider_type = cfg.provider
            if provider_type == "gemini":
                providers[key] = GeminiProvider(api_key=api_key, default_model=cfg.model)
            elif provider_type == "openai_compatible":
                providers[key] = OpenAICompatibleProvider(api_key=api_key, base_url=base_url, default_model=cfg.model)
            else:
                providers[key] = OpenAIProvider(api_key=api_key, base_url=base_url, default_model=cfg.model)
        # Default provider if missing
        if self.settings.llm_default_provider and self.settings.llm_default_provider not in providers:
            providers[self.settings.llm_default_provider] = OpenAICompatibleProvider(
                api_key=self.settings.llm_api_key or "",
                base_url=self.settings.llm_base_url or "https://api.openai.com/v1",
                default_model=self.registry.roles.get("fast_model", "gpt-4o-mini"),
            )
        return providers

    def _target_for_role(self, role: str) -> Tuple[BaseLLMProvider, str]:
        target = self.registry.get_model_target(role)
        if target:
            provider_key, model_name = target
            provider = self.providers.get(provider_key)
            if provider:
                return provider, model_name
        # Fallback to default provider
        fallback_key = self.settings.llm_default_provider or "openai"
        provider = self.providers.get(fallback_key)
        if not provider:
            raise LLMError(f"No provider configured for role={role} and fallback={fallback_key}")
        model_name = self.registry.roles.get(role, "")
        model_name = model_name.split(":", 1)[1] if ":" in model_name else model_name or getattr(provider, "default_model", "")
        return provider, model_name

    async def chat(self, role: str, messages: List[Dict[str, str]], **kwargs) -> LLMResult:
        provider, model_name = self._target_for_role(role)
        start = time.time()
        try:
            result = await provider.chat(messages, model=model_name, **kwargs)
            self.REQUEST_COUNT.labels(provider=provider.name, model=model_name, status="success").inc()
            return result
        except LLMError:
            self.REQUEST_COUNT.labels(provider=provider.name, model=model_name, status="error").inc()
            # Try fallback if configured
            fallback_target = self.registry.get_model_target("fallback_model")
            if fallback_target:
                fb_provider_key, fb_model = fallback_target
                fb_provider = self.providers.get(fb_provider_key)
                if fb_provider and fb_provider is not provider:
                    return await fb_provider.chat(messages, model=fb_model, **kwargs)
            raise
        finally:
            self.REQUEST_LATENCY.labels(provider=provider.name, model=model_name).observe(time.time() - start)
