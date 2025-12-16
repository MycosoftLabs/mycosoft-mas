"""
Base LLM Provider Interface

All LLM providers must implement this interface for consistency.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class LLMError(Exception):
    """Base exception for LLM errors."""
    
    def __init__(self, message: str, provider: str, model: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.original_error = original_error
        self.timestamp = datetime.utcnow()


class MessageRole(str, Enum):
    """Message roles for chat completions."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


@dataclass
class Message:
    """Chat message."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class LLMResponse:
    """Unified response from LLM providers."""
    
    content: str
    model: str
    provider: str
    finish_reason: str
    
    # Token usage
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    # Metadata
    response_time_ms: float = 0.0
    timestamp: datetime = None
    raw_response: Optional[Dict[str, Any]] = None
    
    # Function calling
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class LLMProvider(ABC):
    """
    Base abstract class for LLM providers.
    
    All providers must implement:
    - chat(): For chat completions
    - embed(): For embeddings (optional but recommended)
    - list_models(): List available models
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider.
        
        Args:
            config: Provider configuration including api_key, base_url, etc.
        """
        self.config = config
        self.provider_name = self.__class__.__name__.replace("Provider", "").lower()
        
    @abstractmethod
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
        """
        Generate a chat completion.
        
        Args:
            messages: List of chat messages
            model: Model identifier
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            functions: Function definitions for function calling
            function_call: Force a specific function call
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse object
            
        Raises:
            LLMError: If the request fails
        """
        pass
    
    async def embed(
        self,
        texts: List[str],
        model: str,
        **kwargs
    ) -> List[List[float]]:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            model: Embedding model identifier
            **kwargs: Additional provider-specific parameters
            
        Returns:
            List of embedding vectors
            
        Raises:
            LLMError: If the request fails
            NotImplementedError: If provider doesn't support embeddings
        """
        raise NotImplementedError(f"{self.provider_name} does not support embeddings")
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """
        List available models for this provider.
        
        Returns:
            List of model identifiers
        """
        pass
    
    async def validate_config(self) -> bool:
        """
        Validate provider configuration.
        
        Returns:
            True if configuration is valid
            
        Raises:
            LLMError: If configuration is invalid
        """
        required_keys = self.get_required_config_keys()
        missing_keys = [key for key in required_keys if key not in self.config]
        
        if missing_keys:
            raise LLMError(
                f"Missing required configuration keys: {', '.join(missing_keys)}",
                provider=self.provider_name,
                model="N/A"
            )
        
        return True
    
    def get_required_config_keys(self) -> List[str]:
        """
        Get required configuration keys for this provider.
        
        Returns:
            List of required config keys
        """
        return ["api_key"]
    
    def _handle_error(self, error: Exception, model: str, operation: str) -> LLMError:
        """
        Convert provider-specific errors to LLMError.
        
        Args:
            error: Original exception
            model: Model being used
            operation: Operation that failed (e.g., "chat", "embed")
            
        Returns:
            LLMError with context
        """
        message = f"{self.provider_name} {operation} failed: {str(error)}"
        return LLMError(
            message=message,
            provider=self.provider_name,
            model=model,
            original_error=error
        )
