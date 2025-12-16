"""
Google Gemini Provider

Supports Google's Gemini models via the Generative Language API.
"""

import os
import time
import asyncio
from typing import Dict, Any, List, Optional
import httpx
import logging

from .provider import LLMProvider, LLMResponse, LLMError, Message, MessageRole

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY")
        self.base_url = config.get("base_url", "https://generativelanguage.googleapis.com/v1beta")
        self.timeout = config.get("timeout", 60)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 2)
        
        if not self.api_key:
            raise LLMError(
                "Gemini API key not found in config or environment",
                provider="gemini",
                model="N/A"
            )
    
    def _convert_messages_to_gemini(self, messages: List[Message]) -> Dict[str, Any]:
        """Convert messages to Gemini format."""
        contents = []
        system_instruction = None
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # Gemini uses a separate system_instruction field
                system_instruction = msg.content
            else:
                # Map roles: user -> user, assistant -> model
                role = "user" if msg.role == MessageRole.USER else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.content}]
                })
        
        result = {"contents": contents}
        if system_instruction:
            result["system_instruction"] = {"parts": [{"text": system_instruction}]}
        
        return result
    
    async def chat(
        self,
        messages: List[Message],
        model: str = "gemini-pro",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a chat completion."""
        start_time = time.time()
        
        # Convert messages
        message_data = self._convert_messages_to_gemini(messages)
        
        # Build payload
        payload = {
            **message_data,
            "generationConfig": {
                "temperature": temperature,
                **({"maxOutputTokens": max_tokens} if max_tokens else {}),
                **({"topP": kwargs.get("top_p")} if "top_p" in kwargs else {}),
                **({"topK": kwargs.get("top_k")} if "top_k" in kwargs else {}),
            }
        }
        
        # Function calling (Gemini uses "tools")
        if functions:
            payload["tools"] = [{
                "functionDeclarations": functions
            }]
        
        # Build URL
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                
                # Extract response
                candidate = data["candidates"][0]
                content_part = candidate["content"]["parts"][0]
                
                # Extract text or function call
                content_text = content_part.get("text", "")
                function_call_data = content_part.get("functionCall")
                
                # Token usage (Gemini provides this in metadata)
                usage_metadata = data.get("usageMetadata", {})
                prompt_tokens = usage_metadata.get("promptTokenCount", 0)
                completion_tokens = usage_metadata.get("candidatesTokenCount", 0)
                
                response_time_ms = (time.time() - start_time) * 1000
                
                return LLMResponse(
                    content=content_text,
                    model=model,
                    provider="gemini",
                    finish_reason=candidate.get("finishReason", "STOP").lower(),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    response_time_ms=response_time_ms,
                    function_call=function_call_data,
                    raw_response=data
                )
                
            except httpx.HTTPStatusError as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Gemini request failed (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying..."
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise self._handle_error(e, model, "chat")
            
            except Exception as e:
                raise self._handle_error(e, model, "chat")
        
        raise LLMError(
            f"Gemini chat failed after {self.max_retries} attempts",
            provider="gemini",
            model=model
        )
    
    async def embed(
        self,
        texts: List[str],
        model: str = "embedding-001",
        **kwargs
    ) -> List[List[float]]:
        """Generate embeddings."""
        url = f"{self.base_url}/models/{model}:embedContent?key={self.api_key}"
        
        # Gemini embedding API processes one text at a time
        embeddings = []
        
        for text in texts:
            payload = {
                "content": {
                    "parts": [{"text": text}]
                }
            }
            
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                
                embedding = data["embedding"]["values"]
                embeddings.append(embedding)
                
            except Exception as e:
                raise self._handle_error(e, model, "embed")
        
        return embeddings
    
    async def list_models(self) -> List[str]:
        """List available models."""
        url = f"{self.base_url}/models?key={self.api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            models = [
                model["name"].replace("models/", "")
                for model in data.get("models", [])
                if "generateContent" in model.get("supportedGenerationMethods", [])
            ]
            return models
            
        except Exception as e:
            logger.warning(f"Failed to list Gemini models: {e}")
            return ["gemini-pro", "gemini-pro-vision"]  # Fallback to known models
