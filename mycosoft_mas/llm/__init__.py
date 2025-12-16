"""
Mycosoft MAS - LLM Provider Abstraction Module

This module provides a unified interface for interacting with various LLM providers.
It supports multiple backends including OpenAI, Azure OpenAI, Google Gemini,
Anthropic Claude, and local models via Ollama/LiteLLM.

Usage:
    from mycosoft_mas.llm import get_llm_client, LLMRouter
    
    # Get a configured client
    client = get_llm_client()
    
    # Use the router for automatic model selection
    router = LLMRouter()
    response = await router.chat(messages=[...], task_type="planning")
"""

from mycosoft_mas.llm.config import LLMConfig, get_llm_config
from mycosoft_mas.llm.providers.base import BaseLLMProvider, LLMResponse, LLMError
from mycosoft_mas.llm.providers.openai_provider import OpenAIProvider
from mycosoft_mas.llm.providers.openai_compatible import OpenAICompatibleProvider
from mycosoft_mas.llm.router import LLMRouter
from mycosoft_mas.llm.client import get_llm_client, LLMClient

__all__ = [
    # Config
    "LLMConfig",
    "get_llm_config",
    # Providers
    "BaseLLMProvider",
    "OpenAIProvider",
    "OpenAICompatibleProvider",
    "LLMResponse",
    "LLMError",
    # Router
    "LLMRouter",
    # Client
    "get_llm_client",
    "LLMClient",
]
