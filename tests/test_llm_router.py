import pytest

from mycosoft_mas.config.runtime_settings import ModelRegistry, ProviderConfig, RuntimeSettings
from mycosoft_mas.llm.providers import BaseLLMProvider, LLMError, LLMResult, LLMRouter


class FailingProvider(BaseLLMProvider):
    name = "primary"

    async def chat(self, messages, *, model=None, **kwargs):
        raise LLMError("fail")

    async def embed(self, inputs, *, model=None, **kwargs):
        raise NotImplementedError


class DummyProvider(BaseLLMProvider):
    name = "fallback"

    async def chat(self, messages, *, model=None, **kwargs):
        return LLMResult(content="ok", provider=self.name, model=model or "dummy")

    async def embed(self, inputs, *, model=None, **kwargs):
        return {"embeddings": []}


@pytest.mark.asyncio
async def test_router_falls_back_on_error(monkeypatch):
    registry = ModelRegistry(
        providers={
            "primary": ProviderConfig(provider="openai", model="primary-model"),
            "fallback": ProviderConfig(provider="openai", model="fallback-model"),
        },
        roles={
            "planning_model": "primary:primary-model",
            "fallback_model": "fallback:fallback-model",
        },
    )
    settings = RuntimeSettings(
        database_url="postgresql://user:pass@localhost/db",
        redis_url="redis://localhost:6379/0",
        qdrant_url="http://localhost:6333",
        model_registry=registry,
    )
    router = LLMRouter(settings)
    router.providers = {"primary": FailingProvider(), "fallback": DummyProvider()}

    result = await router.chat("planning_model", [{"role": "user", "content": "hi"}])
    assert result.content == "ok"
    assert result.provider == "fallback"
