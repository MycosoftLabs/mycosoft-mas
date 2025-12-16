"""
OpenAI Provider

Supports:
- OpenAI API (https://api.openai.com/v1)
- Azure OpenAI API
"""

import os
import time
import asyncio
from typing import Dict, Any, List, Optional
import httpx
import logging

from .provider import LLMProvider, LLMResponse, LLMError, Message, MessageRole

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI and Azure OpenAI provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.base_url = config.get("base_url") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.api_type = config.get("api_type", "openai")  # "openai" or "azure"
        self.api_version = config.get("api_version", "2024-02-01")
        self.timeout = config.get("timeout", 60)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 2)
        
        # Azure-specific
        if self.api_type == "azure":
            self.deployment_name = config.get("deployment_name")
            self.base_url = config.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
        
        if not self.api_key:
            raise LLMError(
                "OpenAI API key not found in config or environment",
                provider="openai",
                model="N/A"
            )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_type == "azure":
            headers["api-key"] = self.api_key
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    def _build_url(self, endpoint: str, model: Optional[str] = None) -> str:
        """Build request URL."""
        if self.api_type == "azure":
            # Azure URL format: {endpoint}/openai/deployments/{deployment}/chat/completions?api-version={version}
            deployment = model or self.deployment_name
            return f"{self.base_url.rstrip('/')}/openai/deployments/{deployment}/{endpoint}?api-version={self.api_version}"
        else:
            # OpenAI URL format: {base_url}/chat/completions
            return f"{self.base_url.rstrip('/')}/{endpoint}"
    
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
            "messages": formatted_messages,
            "temperature": temperature,
            **({"max_tokens": max_tokens} if max_tokens else {}),
            **({"functions": functions} if functions else {}),
            **({"function_call": function_call} if function_call else {}),
            **kwargs
        }
        
        # Add model only for non-Azure (Azure uses deployment name in URL)
        if self.api_type != "azure":
            payload["model"] = model
        
        url = self._build_url("chat/completions", model)
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
                    provider="openai",
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
                        f"OpenAI request failed (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying..."
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise self._handle_error(e, model, "chat")
            
            except Exception as e:
                raise self._handle_error(e, model, "chat")
        
        raise LLMError(
            f"OpenAI chat failed after {self.max_retries} attempts",
            provider="openai",
            model=model
        )
    
    async def embed(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small",
        **kwargs
    ) -> List[List[float]]:
        """Generate embeddings."""
        payload = {
            "input": texts,
            **kwargs
        }
        
        # Add model only for non-Azure
        if self.api_type != "azure":
            payload["model"] = model
        
        url = self._build_url("embeddings", model)
        headers = self._get_headers()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            
            # Extract embeddings
            embeddings = [item["embedding"] for item in data["data"]]
            return embeddings
            
        except Exception as e:
            raise self._handle_error(e, model, "embed")
    
    async def list_models(self) -> List[str]:
        """List available models."""
        if self.api_type == "azure":
            # Azure doesn't support listing models via API
            return [self.deployment_name] if self.deployment_name else []
        
        url = f"{self.base_url.rstrip('/')}/models"
        headers = self._get_headers()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
            
            models = [model["id"] for model in data.get("data", [])]
            return models
            
        except Exception as e:
            logger.warning(f"Failed to list OpenAI models: {e}")
            return []
    
    def get_required_config_keys(self) -> List[str]:
        """Get required configuration keys."""
        if self.api_type == "azure":
            return ["api_key", "azure_endpoint", "deployment_name"]
        return ["api_key"]
