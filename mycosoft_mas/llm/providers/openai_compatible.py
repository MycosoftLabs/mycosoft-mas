"""
OpenAI-Compatible Provider Implementation

Supports any LLM endpoint that implements the OpenAI API spec:
- LiteLLM proxy
- vLLM
- Ollama (with OpenAI compatibility)
- LocalAI
- etc.

This is the recommended provider for local development as it allows
switching between providers without code changes.
"""

import time
from typing import Any, AsyncGenerator, Optional
import logging
import aiohttp

from mycosoft_mas.llm.providers.base import (
    BaseLLMProvider,
    LLMResponse,
    LLMError,
    LLMErrorType,
    EmbeddingResponse,
    Message,
    TokenUsage,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Provider for OpenAI-compatible API endpoints.
    
    Works with LiteLLM, vLLM, Ollama, and other compatible servers.
    This is the recommended provider for local development as it
    provides a unified interface to all LLM backends.
    """
    
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "http://localhost:4000",
        timeout: int = 120,
        max_retries: int = 3,
        **kwargs: Any,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def provider_name(self) -> str:
        return "openai_compatible"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
            )
        return self._session
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def chat(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str | dict[str, Any]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request."""
        start_time = time.time()
        session = await self._get_session()
        
        # Convert Message objects to dicts
        message_dicts = []
        for msg in messages:
            msg_dict = {"role": msg.role, "content": msg.content}
            if msg.name:
                msg_dict["name"] = msg.name
            if msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            message_dicts.append(msg_dict)
        
        # Build request payload
        payload = {
            "model": model,
            "messages": message_dicts,
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
        
        # Add any extra kwargs
        payload.update(kwargs)
        
        url = f"{self.base_url}/v1/chat/completions"
        
        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_body = await response.text()
                    raise self._handle_error_response(response.status, error_body, model)
                
                data = await response.json()
                
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Extract response
            choice = data["choices"][0]
            content = choice["message"].get("content", "") or ""
            tool_calls = choice["message"].get("tool_calls")
            
            # Build usage
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )
            
            # Calculate cost
            cost = self._calculate_cost(
                model=model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )
            
            return LLMResponse(
                content=content,
                model=data.get("model", model),
                provider=self.provider_name,
                usage=usage,
                duration_ms=duration_ms,
                tool_calls=tool_calls,
                finish_reason=choice.get("finish_reason", "stop"),
                estimated_cost=cost,
                raw_response=data,
            )
            
        except aiohttp.ClientError as e:
            raise LLMError(
                error_type=LLMErrorType.SERVICE_UNAVAILABLE,
                message=f"Connection error: {str(e)}",
                provider=self.provider_name,
                model=model,
                retryable=True,
            )
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(
                error_type=LLMErrorType.UNKNOWN,
                message=str(e),
                provider=self.provider_name,
                model=model,
            )
    
    async def complete(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a completion request (converts to chat format)."""
        messages = [Message(role="user", content=prompt)]
        return await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
    
    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Generate embeddings."""
        start_time = time.time()
        session = await self._get_session()
        
        payload = {
            "model": model,
            "input": texts,
        }
        payload.update(kwargs)
        
        url = f"{self.base_url}/v1/embeddings"
        
        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_body = await response.text()
                    raise self._handle_error_response(response.status, error_body, model)
                
                data = await response.json()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            embeddings = [item["embedding"] for item in data["data"]]
            
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )
            
            return EmbeddingResponse(
                embeddings=embeddings,
                model=data.get("model", model),
                provider=self.provider_name,
                usage=usage,
                duration_ms=duration_ms,
            )
            
        except aiohttp.ClientError as e:
            raise LLMError(
                error_type=LLMErrorType.SERVICE_UNAVAILABLE,
                message=f"Connection error: {str(e)}",
                provider=self.provider_name,
                model=model,
                retryable=True,
            )
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(
                error_type=LLMErrorType.UNKNOWN,
                message=str(e),
                provider=self.provider_name,
                model=model,
            )
    
    async def chat_stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion response."""
        session = await self._get_session()
        
        message_dicts = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        payload = {
            "model": model,
            "messages": message_dicts,
            "temperature": temperature,
            "stream": True,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        payload.update(kwargs)
        
        url = f"{self.base_url}/v1/chat/completions"
        
        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_body = await response.text()
                    raise self._handle_error_response(response.status, error_body, model)
                
                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        
                        import json
                        try:
                            data = json.loads(data_str)
                            if data["choices"] and data["choices"][0]["delta"].get("content"):
                                yield data["choices"][0]["delta"]["content"]
                        except json.JSONDecodeError:
                            continue
                            
        except aiohttp.ClientError as e:
            raise LLMError(
                error_type=LLMErrorType.SERVICE_UNAVAILABLE,
                message=f"Connection error: {str(e)}",
                provider=self.provider_name,
                model=model,
                retryable=True,
            )
    
    async def health_check(self) -> bool:
        """Check if the endpoint is accessible."""
        session = await self._get_session()
        
        try:
            # Try /health endpoint first (LiteLLM)
            async with session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    return True
        except Exception:
            pass
        
        try:
            # Fall back to /v1/models
            async with session.get(f"{self.base_url}/v1/models") as response:
                return response.status == 200
        except Exception:
            return False
    
    def _handle_error_response(
        self,
        status_code: int,
        error_body: str,
        model: str,
    ) -> LLMError:
        """Parse error response and return appropriate LLMError."""
        import json
        
        error_type = LLMErrorType.UNKNOWN
        message = error_body
        retryable = False
        retry_after = None
        
        try:
            error_data = json.loads(error_body)
            message = error_data.get("error", {}).get("message", error_body)
        except json.JSONDecodeError:
            pass
        
        if status_code == 401:
            error_type = LLMErrorType.AUTHENTICATION
        elif status_code == 429:
            error_type = LLMErrorType.RATE_LIMIT
            retryable = True
            retry_after = 60.0
        elif status_code == 404:
            error_type = LLMErrorType.MODEL_NOT_FOUND
        elif status_code == 400:
            if "context" in message.lower() or "token" in message.lower():
                error_type = LLMErrorType.CONTEXT_LENGTH
            else:
                error_type = LLMErrorType.INVALID_REQUEST
        elif status_code in (500, 502, 503, 504):
            error_type = LLMErrorType.SERVICE_UNAVAILABLE
            retryable = True
        
        return LLMError(
            error_type=error_type,
            message=message,
            provider=self.provider_name,
            model=model,
            retryable=retryable,
            retry_after=retry_after,
            details={"status_code": status_code},
        )
