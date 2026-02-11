"""
LLM Providers Module

Contains provider implementations for different LLM backends.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mycosoft_mas.llm.providers.base import BaseLLMProvider, LLMResponse, LLMError
from mycosoft_mas.llm.providers.openai_provider import OpenAIProvider
from mycosoft_mas.llm.providers.openai_compatible import OpenAICompatibleProvider

# ---------------------------------------------------------------------------
# Compatibility exports
# ---------------------------------------------------------------------------
# Some parts of the codebase (and tests) historically imported `LLMRouter` and
# `LLMResult` from `mycosoft_mas.llm.providers`. Since `providers` is now a
# package, we provide a small compatibility router that works with the
# `RuntimeSettings.model_registry` format.


@dataclass(frozen=True)
class LLMResult:
    content: str
    provider: str
    model: str
    raw: Optional[Dict[str, Any]] = None


class LLMRouter:
    """
    Minimal router used by tests + legacy call sites.

    - Accepts `RuntimeSettings` from `mycosoft_mas.config.runtime_settings`.
    - Uses `settings.model_registry.roles` mappings like `primary:model-name`.
    - Allows callers/tests to inject `router.providers = {...}`.
    """

    def __init__(self, settings: Any):
        self.settings = settings
        self.providers: Dict[str, BaseLLMProvider] = {}

    async def chat(self, role: str, messages: List[Dict[str, str]], **kwargs: Any) -> LLMResult:
        target = self.settings.model_registry.get_model_target(role)
        if not target:
            raise LLMError(f"Unknown model role: {role}")

        provider_key, model_name = target
        provider = self.providers.get(provider_key)
        if not provider:
            raise LLMError(f"Provider not configured: {provider_key}")

        try:
            result = await provider.chat(messages, model=model_name, **kwargs)
            if isinstance(result, LLMResult):
                return result
            if isinstance(result, LLMResponse):
                return LLMResult(content=result.content, provider=provider_key, model=model_name, raw=result.raw)
            # Last resort: stringify
            return LLMResult(content=str(result), provider=provider_key, model=model_name, raw={"result": result})
        except Exception as exc:
            # Try an explicit fallback role if present
            fallback_target = self.settings.model_registry.get_model_target("fallback_model")
            if not fallback_target:
                raise
            fb_provider_key, fb_model = fallback_target
            fb_provider = self.providers.get(fb_provider_key)
            if not fb_provider:
                raise
            fb_result = await fb_provider.chat(messages, model=fb_model, **kwargs)
            if isinstance(fb_result, LLMResult):
                return fb_result
            if isinstance(fb_result, LLMResponse):
                return LLMResult(content=fb_result.content, provider=fb_provider_key, model=fb_model, raw=fb_result.raw)
            return LLMResult(
                content=str(fb_result),
                provider=fb_provider_key,
                model=fb_model,
                raw={"result": fb_result, "fallback_from": provider_key, "error": str(exc)},
            )

__all__ = [
    "BaseLLMProvider",
    "LLMResponse",
    "LLMError",
    "LLMResult",
    "LLMRouter",
    "OpenAIProvider",
    "OpenAICompatibleProvider",
]
