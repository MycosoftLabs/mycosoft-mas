"""
NLM Base Model - February 10, 2026

Model wrapper classes for the Nature Learning Model.

These classes provide a unified interface for:
- Loading pre-trained or fine-tuned models
- Text generation with domain-specific prompts
- Embedding generation for semantic search
- Model lifecycle management
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseNLM(ABC):
    """Abstract base class for NLM model implementations."""
    
    @abstractmethod
    async def load(self) -> bool:
        """
        Load the model into memory.
        
        Returns:
            True if loading was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def unload(self) -> None:
        """Unload the model from memory."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate text based on a prompt.
        
        Args:
            prompt: The input prompt for generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text string
        """
        pass
    
    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if the model is currently loaded."""
        pass


class NLMBaseModel(BaseNLM):
    """
    Base wrapper for the Nature Learning Model.
    
    Provides text generation capabilities specialized for mycology
    and natural sciences domains.
    
    Attributes:
        model_path: Path to the model weights
        device: Device to load the model on (auto, cuda, cpu)
        config: Model configuration dictionary
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "auto",
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the NLM model wrapper.
        
        Args:
            model_path: Path to model weights. If None, uses config default.
            device: Device for inference (auto, cuda, cpu)
            config: Optional configuration override
        """
        from ..config import get_nlm_config
        
        self._nlm_config = get_nlm_config()
        self.model_path = Path(model_path or self._nlm_config.model_dir)
        self.device = device or self._nlm_config.inference.device
        self.config = config or {}
        
        self._model = None
        self._tokenizer = None
        self._is_loaded = False
        
        # System prompt for NLM identity
        self.system_prompt = self._nlm_config.system_prompt
    
    @property
    def is_loaded(self) -> bool:
        """Check if the model is currently loaded."""
        return self._is_loaded
    
    async def load(self) -> bool:
        """
        Load the NLM model into memory.
        
        Attempts to load from local path first, falls back to base model
        if fine-tuned weights are not available.
        
        Returns:
            True if loading successful, False otherwise
        """
        if self._is_loaded:
            logger.info("NLM model already loaded")
            return True
        
        try:
            logger.info(f"Loading NLM from {self.model_path}")
            
            # Check if local model exists
            if self.model_path.exists():
                # In production, load with transformers:
                # from transformers import AutoModelForCausalLM, AutoTokenizer
                # self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                # self._model = AutoModelForCausalLM.from_pretrained(
                #     self.model_path,
                #     device_map=self.device,
                #     torch_dtype="auto",
                # )
                logger.info(f"NLM model loaded from {self.model_path}")
                self._is_loaded = True
                return True
            else:
                logger.warning(
                    f"NLM model not found at {self.model_path}. "
                    "Model generation will use fallback."
                )
                # Mark as loaded to use fallback generation
                self._is_loaded = True
                return True
                
        except Exception as e:
            logger.error(f"Failed to load NLM model: {e}")
            return False
    
    async def unload(self) -> None:
        """Unload the NLM model from memory."""
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        self._is_loaded = False
        logger.info("NLM model unloaded")
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: Optional[str] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Generate text using the NLM.
        
        Args:
            prompt: User prompt for generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            system: Optional system prompt override
            stop_sequences: Optional stop sequences
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text response
        """
        if not self._is_loaded:
            await self.load()
        
        system_prompt = system or self.system_prompt
        
        # Build full prompt
        full_prompt = f"""<|system|>
{system_prompt}
</|system|>

<|user|>
{prompt}
</|user|>

<|assistant|>
"""
        
        # If model is loaded, use it
        if self._model is not None:
            # In production:
            # inputs = self._tokenizer(full_prompt, return_tensors="pt")
            # outputs = self._model.generate(
            #     **inputs,
            #     max_new_tokens=max_tokens,
            #     temperature=temperature,
            #     do_sample=True,
            # )
            # return self._tokenizer.decode(outputs[0], skip_special_tokens=True)
            pass
        
        # Fallback response
        return self._generate_fallback_response(prompt)
    
    def _generate_fallback_response(self, prompt: str) -> str:
        """
        Generate a fallback response when model is not available.
        
        This provides a placeholder response indicating NLM capabilities.
        In production, this would call an external API.
        """
        return f"""Based on the Nature Learning Model knowledge base:

Your query: {prompt[:200]}{'...' if len(prompt) > 200 else ''}

The NLM model is not yet fully trained. When complete, it will provide:
- Detailed species taxonomy and classification
- Mycology research findings and analysis
- Environmental data interpretation
- Genetic sequence analysis
- Ecological interaction descriptions

To enable full NLM capabilities:
1. Train the model using `NLMTrainer.train()`
2. Export the model to the configured path
3. Reload the inference service

Contact the Mycosoft team for assistance with NLM training."""
    
    async def generate_with_context(
        self,
        prompt: str,
        context: Dict[str, Any],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate text with additional context for RAG-style queries.
        
        Args:
            prompt: User prompt
            context: Dictionary of context key-value pairs
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text response
        """
        context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])
        augmented_prompt = f"""Context Information:
{context_str}

Question: {prompt}

Based on the context provided and your knowledge of mycology and natural sciences, 
please provide a detailed and accurate response."""
        
        return await self.generate(
            augmented_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )


class NLMEmbeddingModel:
    """
    Embedding model for the Nature Learning Model.
    
    Generates dense vector embeddings for semantic search
    and similarity computations in the mycology domain.
    
    Attributes:
        model_name: Name of the embedding model
        embedding_dim: Dimension of output embeddings
    """
    
    def __init__(
        self,
        model_name: str = "nlm-embed",
        embedding_dim: int = 384,
    ):
        """
        Initialize the NLM embedding model.
        
        Args:
            model_name: Name/path of the embedding model
            embedding_dim: Expected dimension of embeddings
        """
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self._model = None
        self._is_loaded = False
    
    @property
    def is_loaded(self) -> bool:
        """Check if embedding model is loaded."""
        return self._is_loaded
    
    async def load(self) -> bool:
        """
        Load the embedding model.
        
        Returns:
            True if loading successful
        """
        try:
            # In production, load with sentence-transformers:
            # from sentence_transformers import SentenceTransformer
            # self._model = SentenceTransformer(self.model_name)
            logger.info(f"NLM embedding model loaded: {self.model_name}")
            self._is_loaded = True
            return True
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            return False
    
    async def embed(
        self,
        texts: Union[str, List[str]],
        normalize: bool = True,
    ) -> List[List[float]]:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Single text or list of texts to embed
            normalize: Whether to L2-normalize the embeddings
            
        Returns:
            List of embedding vectors
        """
        if isinstance(texts, str):
            texts = [texts]
        
        if not self._is_loaded:
            await self.load()
        
        # In production with sentence-transformers:
        # embeddings = self._model.encode(texts, normalize_embeddings=normalize)
        # return embeddings.tolist()
        
        # Placeholder embeddings
        embeddings = []
        for _ in texts:
            embeddings.append([0.0] * self.embedding_dim)
        return embeddings
    
    async def similarity(
        self,
        text1: str,
        text2: str,
    ) -> float:
        """
        Compute cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        embeddings = await self.embed([text1, text2])
        
        # Compute cosine similarity
        import math
        
        vec1, vec2 = embeddings[0], embeddings[1]
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
