"""
Base LLM Provider Interface

Defines the abstract interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Optional
import logging

logger = logging.getLogger(__name__)


class LLMErrorType(Enum):
    """Types of LLM errors for structured error handling."""
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    MODEL_NOT_FOUND = "model_not_found"
    CONTEXT_LENGTH = "context_length"
    CONTENT_FILTER = "content_filter"
    SERVICE_UNAVAILABLE = "service_unavailable"
    UNKNOWN = "unknown"


@dataclass
class LLMError(Exception):
    """
    Structured LLM error with type and details.

    Compatibility: legacy tests raise `LLMError("message")`, so `message` is the
    first positional arg and `error_type` is optional.
    """

    message: str
    error_type: LLMErrorType = LLMErrorType.UNKNOWN
    provider: str = ""
    model: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False
    retry_after: Optional[float] = None
    
    def __str__(self) -> str:
        return f"[{self.error_type.value}] {self.provider}/{self.model}: {self.message}"


@dataclass
class Message:
    """A chat message."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


@dataclass
class TokenUsage:
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    provider: str
    
    # Token usage
    usage: TokenUsage = field(default_factory=TokenUsage)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0
    
    # Function/tool calling
    tool_calls: Optional[list[dict[str, Any]]] = None
    finish_reason: str = "stop"
    
    # Cost tracking
    estimated_cost: float = 0.0
    
    # Raw response for debugging
    raw_response: Optional[dict[str, Any]] = None
    
    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return bool(self.tool_calls)


@dataclass
class EmbeddingResponse:
    """Response from an embedding request."""
    embeddings: list[list[float]]
    model: str
    provider: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    duration_ms: int = 0


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All provider implementations must inherit from this class and implement
    the required methods: chat(), complete(), and embed().
    """
    
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        timeout: int = 120,
        max_retries: int = 3,
        **kwargs: Any,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(f"llm.{self.provider_name}")
        self._extra_config = kwargs
    
    @property
    def provider_name(self) -> str:
        """
        Return the provider name (e.g., 'openai', 'azure', 'gemini').

        Compatibility: legacy provider test doubles often only define `name`.
        """
        name = getattr(self, "name", None)
        if isinstance(name, str) and name:
            return name
        return self.__class__.__name__.lower()
    
    @abstractmethod
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
        """
        Send a chat completion request.
        
        Args:
            messages: List of chat messages
            model: Model identifier
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            tools: List of tool definitions for function calling
            tool_choice: Tool selection strategy
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse with generated content
            
        Raises:
            LLMError: On any provider error
        """
        pass
    
    async def complete(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send a text completion request (non-chat).
        
        Args:
            prompt: Text prompt
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse with generated content
        """
        # Default implementation: map a prompt into a single-turn chat.
        return await self.chat(
            messages=[Message(role="user", content=prompt)],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
    
    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            model: Embedding model identifier
            **kwargs: Additional parameters
            
        Returns:
            EmbeddingResponse with embedding vectors
        """
        pass
    
    async def chat_stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion response.
        
        Default implementation calls chat() and yields the full response.
        Providers can override for true streaming support.
        """
        response = await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        yield response.content
    
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and accessible.
        
        Default implementation tries a simple completion.
        Providers can override for more efficient checks.
        """
        try:
            await self.chat(
                messages=[Message(role="user", content="Hi")],
                model="gpt-4o-mini",  # Use a cheap model
                max_tokens=5,
            )
            return True
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False
    
    def _calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Calculate estimated cost for a request.
        
        Override in subclasses with accurate pricing.
        """
        # Default pricing (rough estimates)
        pricing = {
            "gpt-4o": (0.005, 0.015),  # (input per 1k, output per 1k)
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-4-turbo": (0.01, 0.03),
            "gpt-3.5-turbo": (0.0005, 0.0015),
            "claude-3-5-sonnet": (0.003, 0.015),
            "claude-3-opus": (0.015, 0.075),
            "gemini-1.5-pro": (0.00125, 0.005),
            "gemini-1.5-flash": (0.000075, 0.0003),
        }
        
        if model in pricing:
            input_price, output_price = pricing[model]
            return (prompt_tokens / 1000 * input_price) + (completion_tokens / 1000 * output_price)
        
        # Default fallback
        return (prompt_tokens + completion_tokens) / 1000 * 0.002
