"""
LLM Client Module

Provides a simple, high-level interface for LLM interactions.
This is the recommended entry point for most use cases.
"""

import logging
from typing import Any, AsyncGenerator, Optional

from mycosoft_mas.llm.config import LLMConfig, get_llm_config
from mycosoft_mas.llm.providers.base import Message, LLMResponse, EmbeddingResponse
from mycosoft_mas.llm.router import LLMRouter

logger = logging.getLogger(__name__)


class LLMClient:
    """
    High-level LLM client for easy integration.
    
    Provides a simple interface for common LLM operations with
    automatic provider selection and error handling.
    
    Usage:
        client = LLMClient()
        
        # Simple chat
        response = await client.chat("What is 2+2?")
        
        # With system prompt
        response = await client.chat(
            "Summarize this text",
            system_prompt="You are a helpful assistant.",
        )
        
        # With message history
        response = await client.chat_with_history([
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ])
        
        # Generate embeddings
        embeddings = await client.embed(["text1", "text2"])
    """
    
    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        router: Optional[LLMRouter] = None,
    ):
        self.config = config or get_llm_config()
        self.router = router or LLMRouter(config=self.config)
        self.logger = logging.getLogger("llm.client")
    
    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        task_type: str = "execution",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> str:
        """
        Simple chat completion.
        
        Args:
            prompt: User message
            system_prompt: Optional system prompt
            task_type: Task type for model selection
            model: Override model
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            tools: Tool definitions
            **kwargs: Additional parameters
            
        Returns:
            Generated text response
        """
        messages = []
        
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        
        messages.append(Message(role="user", content=prompt))
        
        response = await self.router.chat(
            messages=messages,
            task_type=task_type,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            **kwargs,
        )
        
        return response.content
    
    async def chat_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        task_type: str = "execution",
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Chat completion with full response object.
        
        Same as chat() but returns the full LLMResponse
        including usage stats, timing, etc.
        """
        messages = []
        
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        
        messages.append(Message(role="user", content=prompt))
        
        return await self.router.chat(
            messages=messages,
            task_type=task_type,
            **kwargs,
        )
    
    async def chat_with_history(
        self,
        messages: list[dict[str, str]],
        task_type: str = "execution",
        **kwargs: Any,
    ) -> str:
        """
        Chat with message history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            task_type: Task type for model selection
            **kwargs: Additional parameters
            
        Returns:
            Generated text response
        """
        msg_objects = [
            Message(role=m["role"], content=m["content"])
            for m in messages
        ]
        
        response = await self.router.chat(
            messages=msg_objects,
            task_type=task_type,
            **kwargs,
        )
        
        return response.content
    
    async def chat_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        task_type: str = "execution",
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion.
        
        Yields text chunks as they are generated.
        """
        messages = []
        
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        
        messages.append(Message(role="user", content=prompt))
        
        async for chunk in self.router.chat_stream(
            messages=messages,
            task_type=task_type,
            **kwargs,
        ):
            yield chunk
    
    async def plan(
        self,
        task: str,
        context: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate a plan for a complex task.
        
        Uses the planning model configured for complex reasoning.
        
        Args:
            task: Task description
            context: Optional additional context
            **kwargs: Additional parameters
            
        Returns:
            Generated plan
        """
        system_prompt = """You are an expert planner. Break down the given task into clear, 
actionable steps. Be thorough but concise. Consider dependencies between steps."""
        
        prompt = f"Task: {task}"
        if context:
            prompt += f"\n\nContext: {context}"
        
        return await self.chat(
            prompt=prompt,
            system_prompt=system_prompt,
            task_type="planning",
            **kwargs,
        )
    
    async def summarize(
        self,
        text: str,
        max_length: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        Summarize text.
        
        Args:
            text: Text to summarize
            max_length: Optional maximum length hint
            **kwargs: Additional parameters
            
        Returns:
            Summarized text
        """
        system_prompt = "You are a concise summarizer. Provide clear, accurate summaries."
        
        prompt = f"Summarize the following text"
        if max_length:
            prompt += f" in approximately {max_length} words"
        prompt += f":\n\n{text}"
        
        return await self.chat(
            prompt=prompt,
            system_prompt=system_prompt,
            task_type="fast",
            **kwargs,
        )
    
    async def embed(
        self,
        texts: list[str],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> list[list[float]]:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            model: Optional embedding model override
            **kwargs: Additional parameters
            
        Returns:
            List of embedding vectors
        """
        response = await self.router.embed(
            texts=texts,
            model=model,
            **kwargs,
        )
        
        return response.embeddings
    
    async def embed_response(
        self,
        texts: list[str],
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """
        Generate embeddings with full response.
        
        Same as embed() but returns the full EmbeddingResponse.
        """
        return await self.router.embed(texts=texts, **kwargs)
    
    async def classify(
        self,
        text: str,
        categories: list[str],
        **kwargs: Any,
    ) -> str:
        """
        Classify text into one of the given categories.
        
        Args:
            text: Text to classify
            categories: List of category names
            **kwargs: Additional parameters
            
        Returns:
            Selected category name
        """
        categories_str = ", ".join(f'"{c}"' for c in categories)
        
        system_prompt = f"""You are a text classifier. Classify the given text into exactly one of these categories: {categories_str}.
Respond with only the category name, nothing else."""
        
        result = await self.chat(
            prompt=text,
            system_prompt=system_prompt,
            task_type="fast",
            temperature=0,
            **kwargs,
        )
        
        # Try to match to a valid category
        result = result.strip().strip('"')
        for cat in categories:
            if cat.lower() == result.lower():
                return cat
        
        # Return raw result if no exact match
        return result
    
    async def extract_json(
        self,
        text: str,
        schema_hint: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Extract structured JSON from text.
        
        Args:
            text: Text containing or describing data
            schema_hint: Optional hint about expected schema
            **kwargs: Additional parameters
            
        Returns:
            Extracted JSON as dict
        """
        import json
        
        system_prompt = "Extract the information as JSON. Return only valid JSON, no explanation."
        if schema_hint:
            system_prompt += f"\n\nExpected schema: {schema_hint}"
        
        result = await self.chat(
            prompt=text,
            system_prompt=system_prompt,
            task_type="fast",
            temperature=0,
            **kwargs,
        )
        
        # Try to parse JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]
            
            return json.loads(result.strip())
        except json.JSONDecodeError:
            return {"raw": result}
    
    def get_usage_stats(self) -> dict[str, Any]:
        """Get current usage statistics."""
        return self.router.get_usage_stats()
    
    def get_provider_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all providers."""
        return self.router.get_provider_status()
    
    async def health_check(self) -> dict[str, bool]:
        """Check health of all providers."""
        return await self.router.health_check()


# Global client instance
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the global LLM client instance."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def reset_llm_client() -> None:
    """Reset the global client (useful for testing)."""
    global _client
    _client = None
