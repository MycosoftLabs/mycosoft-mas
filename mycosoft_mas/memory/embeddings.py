"""
Embeddings Module - February 6, 2026

Embedding providers for vector memory.
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger(__name__)


class BaseEmbedder(ABC):
    """Abstract base class for embedding providers."""
    
    dimension: int = 1536
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [await self.embed_text(text) for text in texts]


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embeddings using text-embedding-ada-002 or newer."""
    
    dimension = 1536
    
    def __init__(self, model: str = "text-embedding-ada-002"):
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")
        self._client = None
    
    async def embed_text(self, text: str) -> List[float]:
        try:
            from openai import AsyncOpenAI
            
            if self._client is None:
                self._client = AsyncOpenAI(api_key=self.api_key)
            
            response = await self._client.embeddings.create(
                model=self.model,
                input=text[:8000]  # Truncate to max tokens
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            # Return zero vector as fallback
            return [0.0] * self.dimension


class GeminiEmbedder(BaseEmbedder):
    """Google Gemini embeddings."""
    
    dimension = 768
    
    def __init__(self, model: str = "embedding-001"):
        self.model = model
        self.api_key = os.getenv("GOOGLE_API_KEY")
    
    async def embed_text(self, text: str) -> List[float]:
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            
            result = await asyncio.to_thread(
                genai.embed_content,
                model=f"models/{self.model}",
                content=text[:10000],
                task_type="retrieval_document"
            )
            return result["embedding"]
            
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}")
            return [0.0] * self.dimension


class LocalEmbedder(BaseEmbedder):
    """Local embeddings using sentence-transformers."""
    
    dimension = 384  # MiniLM default
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
    
    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self.dimension = self._model.get_sentence_embedding_dimension()
            except ImportError:
                logger.error("sentence-transformers not installed")
                raise
    
    async def embed_text(self, text: str) -> List[float]:
        self._load_model()
        
        embedding = await asyncio.to_thread(
            self._model.encode,
            text,
            convert_to_numpy=True
        )
        return embedding.tolist()
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        
        embeddings = await asyncio.to_thread(
            self._model.encode,
            texts,
            convert_to_numpy=True
        )
        return embeddings.tolist()


def get_embedder(provider: str = "openai") -> BaseEmbedder:
    """Factory function to get an embedder."""
    provider = provider.lower()
    
    if provider == "openai":
        return OpenAIEmbedder()
    elif provider == "gemini":
        return GeminiEmbedder()
    elif provider == "local":
        return LocalEmbedder()
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")


# Aliases for backward compatibility
EmbeddingProvider = BaseEmbedder
OpenAIEmbeddings = OpenAIEmbedder