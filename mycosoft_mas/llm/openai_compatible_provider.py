"""
OpenAI-Compatible Provider

Works with any OpenAI-compatible API including:
- LiteLLM proxy
- vLLM
- Ollama (with OpenAI compatibility)
- LocalAI
- Text Generation WebUI
"""

import os
import time
import asyncio
from typing import Dict, Any, List, Optional
import httpx
import logging

from .provider import LLMProvider, LLMResponse, LLMError, Message, MessageRole

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """Provider for OpenAI-compatible APIs."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url") or os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:4000")
        self.api_key = config.get("api_key") or os.getenv("LOCAL_LLM_API_KEY", "dummy")
        self.timeout = config.get("timeout", 120)  # Local models may be slower
        self.max_retries = config.get("max_retries", 2)
        self.retry_delay = config.get("retry_delay", 3)
        self.provider_name = "openai_compatible"
        
        # Strip trailing slashes and ensure we have the base API URL
        self.base_url = self.base_url.rstrip("/")
        if not self.base_url.endswith(("/v1", "/api")):
            self.base_url = f"{self.base_url}/v1"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    async def chat(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a chat completion."""
        start_time = time.time()
        
        # Convert messages to OpenAI format
        formatted_messages = [
            {
                "role": msg.role.value,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {})
            }
            for msg in messages
        ]
        
        payload = {
            "model": model,
            "messages": formatted_messages,
            "temperature": temperature,
            **({"max_tokens": max_tokens} if max_tokens else {}),
            **({"functions": functions} if functions else {}),
            **({"function_call": function_call} if function_call else {}),
            **kwargs
        }
        
        url = f"{self.base_url}/chat/completions"
        headers = self._get_headers()
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                
                # Extract response
                choice = data["choices"][0]
                message = choice["message"]
                usage = data.get("usage", {})
                
                response_time_ms = (time.time() - start_time) * 1000
                
                return LLMResponse(
                    content=message.get("content", ""),
                    model=data.get("model", model),
                    provider=self.provider_name,
                    finish_reason=choice.get("finish_reason", "stop"),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    response_time_ms=response_time_ms,
                    function_call=message.get("function_call"),
                    tool_calls=message.get("tool_calls"),
                    raw_response=data
                )
                
            except httpx.HTTPStatusError as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"OpenAI-compatible request failed (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying..."
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise self._handle_error(e, model, "chat")
            
            except Exception as e:
                raise self._handle_error(e, model, "chat")
        
        raise LLMError(
            f"OpenAI-compatible chat failed after {self.max_retries} attempts",
            provider=self.provider_name,
            model=model
        )
    
    async def embed(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small",
        **kwargs
    ) -> List[List[float]]:
        """Generate embeddings (if supported by the endpoint)."""
        payload = {
            "model": model,
            "input": texts,
            **kwargs
        }
        
        url = f"{self.base_url}/embeddings"
        headers = self._get_headers()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            
            # Extract embeddings
            embeddings = [item["embedding"] for item in data["data"]]
            return embeddings
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise NotImplementedError(
                    f"{self.provider_name} endpoint does not support embeddings"
                )
            raise self._handle_error(e, model, "embed")
        
        except Exception as e:
            raise self._handle_error(e, model, "embed")
    
    async def list_models(self) -> List[str]:
        """List available models."""
        url = f"{self.base_url}/models"
        headers = self._get_headers()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
            
            models = [model["id"] for model in data.get("data", [])]
            return models
            
        except Exception as e:
            logger.warning(f"Failed to list models from {self.base_url}: {e}")
            return []
    
    def get_required_config_keys(self) -> List[str]:
        """Get required configuration keys."""
        return ["base_url"]  # API key can be dummy for local models
