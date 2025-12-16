"""
OpenAI Provider Implementation

Supports OpenAI API and Azure OpenAI with full feature parity.
"""

import time
from typing import Any, AsyncGenerator, Optional
import logging
import asyncio

try:
    import openai
    from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

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


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API provider implementation.
    
    Supports both OpenAI and Azure OpenAI endpoints.
    """
    
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        organization: str = "",
        timeout: int = 120,
        max_retries: int = 3,
        azure_api_version: str = "",
        **kwargs: Any,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )
        
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package is required. Install with: pip install openai")
        
        self.organization = organization
        self.azure_api_version = azure_api_version
        self._is_azure = bool(azure_api_version) or "azure" in base_url.lower()
        
        # Initialize client
        client_kwargs = {
            "api_key": api_key,
            "timeout": timeout,
            "max_retries": max_retries,
        }
        
        if base_url:
            client_kwargs["base_url"] = base_url
        if organization:
            client_kwargs["organization"] = organization
        
        self._client = AsyncOpenAI(**client_kwargs)
    
    @property
    def provider_name(self) -> str:
        return "azure" if self._is_azure else "openai"
    
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
        """Send a chat completion request to OpenAI."""
        start_time = time.time()
        
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
        
        # Build request parameters
        request_params = {
            "model": model,
            "messages": message_dicts,
            "temperature": temperature,
        }
        
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        
        if tools:
            request_params["tools"] = tools
            if tool_choice:
                request_params["tool_choice"] = tool_choice
        
        # Add any extra kwargs
        request_params.update(kwargs)
        
        try:
            response = await self._client.chat.completions.create(**request_params)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Extract content and tool calls
            choice = response.choices[0]
            content = choice.message.content or ""
            tool_calls = None
            
            if choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in choice.message.tool_calls
                ]
            
            # Build usage
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            )
            
            # Calculate cost
            cost = self._calculate_cost(
                model=model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )
            
            return LLMResponse(
                content=content,
                model=response.model,
                provider=self.provider_name,
                usage=usage,
                duration_ms=duration_ms,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason or "stop",
                estimated_cost=cost,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )
            
        except RateLimitError as e:
            raise LLMError(
                error_type=LLMErrorType.RATE_LIMIT,
                message=str(e),
                provider=self.provider_name,
                model=model,
                retryable=True,
                retry_after=float(e.response.headers.get("retry-after", 60)) if hasattr(e, "response") else 60,
            )
        except APITimeoutError as e:
            raise LLMError(
                error_type=LLMErrorType.TIMEOUT,
                message=str(e),
                provider=self.provider_name,
                model=model,
                retryable=True,
            )
        except APIError as e:
            error_type = LLMErrorType.UNKNOWN
            retryable = False
            
            if "authentication" in str(e).lower() or e.status_code == 401:
                error_type = LLMErrorType.AUTHENTICATION
            elif e.status_code == 404:
                error_type = LLMErrorType.MODEL_NOT_FOUND
            elif "context_length" in str(e).lower() or e.status_code == 400:
                error_type = LLMErrorType.CONTEXT_LENGTH
            elif e.status_code in (500, 502, 503):
                error_type = LLMErrorType.SERVICE_UNAVAILABLE
                retryable = True
            
            raise LLMError(
                error_type=error_type,
                message=str(e),
                provider=self.provider_name,
                model=model,
                retryable=retryable,
                details={"status_code": e.status_code if hasattr(e, "status_code") else None},
            )
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
        # OpenAI deprecated completions, use chat
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
        """Generate embeddings using OpenAI."""
        start_time = time.time()
        
        try:
            response = await self._client.embeddings.create(
                model=model,
                input=texts,
                **kwargs,
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            embeddings = [item.embedding for item in response.data]
            
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            )
            
            return EmbeddingResponse(
                embeddings=embeddings,
                model=response.model,
                provider=self.provider_name,
                usage=usage,
                duration_ms=duration_ms,
            )
            
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
        # Convert Message objects to dicts
        message_dicts = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        request_params = {
            "model": model,
            "messages": message_dicts,
            "temperature": temperature,
            "stream": True,
        }
        
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        
        request_params.update(kwargs)
        
        try:
            stream = await self._client.chat.completions.create(**request_params)
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise LLMError(
                error_type=LLMErrorType.UNKNOWN,
                message=str(e),
                provider=self.provider_name,
                model=model,
            )
    
    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            # Use models list as a lightweight health check
            await self._client.models.list()
            return True
        except Exception as e:
            self.logger.warning(f"OpenAI health check failed: {e}")
            return False
