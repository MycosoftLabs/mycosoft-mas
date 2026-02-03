"""
LLM Model Wrappers
Unified interface for various LLM providers.
Created: February 3, 2026
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator
from pydantic import BaseModel
import asyncio

logger = logging.getLogger(__name__)

class Message(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

class LLMResponse(BaseModel):
    content: str
    model: str
    usage: Dict[str, int] = {}
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = {}

class LLMWrapper(ABC):
    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
    
    @abstractmethod
    async def generate(self, messages: List[Message], **kwargs) -> LLMResponse:
        pass
    
    @abstractmethod
    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        pass


class OpenAIWrapper(LLMWrapper):
    """Wrapper for OpenAI GPT models."""
    def __init__(self, model_name: str = "gpt-4-turbo", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        self.base_url = "https://api.openai.com/v1"
    
    async def generate(self, messages: List[Message], temperature: float = 0.7, max_tokens: int = 4096, **kwargs) -> LLMResponse:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key)
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[m.dict() for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return LLMResponse(
                content=response.choices[0].message.content,
                model=self.model_name,
                usage={"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens},
                finish_reason=response.choices[0].finish_reason
            )
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise
    
    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key)
            stream = await client.chat.completions.create(
                model=self.model_name,
                messages=[m.dict() for m in messages],
                stream=True,
                **kwargs
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
    
    async def embed(self, text: str) -> List[float]:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key)
            response = await client.embeddings.create(model="text-embedding-3-small", input=text)
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise


class AnthropicWrapper(LLMWrapper):
    """Wrapper for Anthropic Claude models."""
    def __init__(self, model_name: str = "claude-3-opus-20240229", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
    
    async def generate(self, messages: List[Message], temperature: float = 0.7, max_tokens: int = 4096, **kwargs) -> LLMResponse:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            system_msg = next((m.content for m in messages if m.role == "system"), None)
            chat_msgs = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
            response = await client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                system=system_msg or "",
                messages=chat_msgs,
                temperature=temperature
            )
            return LLMResponse(
                content=response.content[0].text,
                model=self.model_name,
                usage={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
                finish_reason=response.stop_reason
            )
        except Exception as e:
            logger.error(f"Anthropic generation error: {e}")
            raise
    
    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            system_msg = next((m.content for m in messages if m.role == "system"), None)
            chat_msgs = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
            async with client.messages.stream(model=self.model_name, max_tokens=4096, system=system_msg or "", messages=chat_msgs) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise
    
    async def embed(self, text: str) -> List[float]:
        logger.warning("Anthropic does not provide embedding API, using fallback")
        return [0.0] * 1536


class LocalLLMWrapper(LLMWrapper):
    """Wrapper for local LLM models (Ollama, vLLM, etc.)."""
    def __init__(self, model_name: str = "llama3:70b", base_url: str = "http://localhost:11434"):
        super().__init__(model_name)
        self.base_url = base_url
    
    async def generate(self, messages: List[Message], temperature: float = 0.7, **kwargs) -> LLMResponse:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/chat", json={
                "model": self.model_name,
                "messages": [m.dict() for m in messages],
                "stream": False,
                "options": {"temperature": temperature}
            }) as resp:
                data = await resp.json()
                return LLMResponse(
                    content=data.get("message", {}).get("content", ""),
                    model=self.model_name,
                    usage={"total_duration": data.get("total_duration", 0)}
                )
    
    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/chat", json={
                "model": self.model_name,
                "messages": [m.dict() for m in messages],
                "stream": True
            }) as resp:
                async for line in resp.content:
                    if line:
                        import json
                        data = json.loads(line)
                        if "message" in data:
                            yield data["message"].get("content", "")
    
    async def embed(self, text: str) -> List[float]:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/embeddings", json={"model": self.model_name, "prompt": text}) as resp:
                data = await resp.json()
                return data.get("embedding", [0.0] * 1536)


def get_llm_wrapper(provider: str, model_name: str, api_key: Optional[str] = None) -> LLMWrapper:
    providers = {
        "openai": OpenAIWrapper,
        "anthropic": AnthropicWrapper,
        "local": LocalLLMWrapper,
    }
    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}")
    return providers[provider](model_name, api_key)
