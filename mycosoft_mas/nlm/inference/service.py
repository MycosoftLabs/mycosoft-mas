"""
NLM Inference Service - February 10, 2026

Inference service for the Nature Learning Model.

Provides:
1. Model loading and lifecycle management
2. Text generation endpoints
3. Specialized mycology/nature queries
4. RAG-augmented generation
5. FastAPI router integration
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Types of queries the NLM can handle."""
    GENERAL = "general"              # General natural language query
    SPECIES_ID = "species_id"        # Species identification
    TAXONOMY = "taxonomy"            # Taxonomic classification
    ECOLOGY = "ecology"              # Ecological interactions
    CULTIVATION = "cultivation"      # Cultivation protocols
    RESEARCH = "research"            # Research synthesis
    GENETICS = "genetics"            # Genetic analysis


@dataclass
class PredictionRequest:
    """
    Request structure for NLM predictions.
    
    Attributes:
        text: Input text/query
        query_type: Type of query for specialized handling
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        context: Optional context for RAG
        include_sources: Whether to include source references
    """
    text: str
    query_type: QueryType = QueryType.GENERAL
    max_tokens: int = 1024
    temperature: float = 0.7
    context: Optional[Dict[str, Any]] = None
    include_sources: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "query_type": self.query_type.value,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "context": self.context,
            "include_sources": self.include_sources,
        }


@dataclass
class PredictionResult:
    """
    Structured result from NLM prediction.
    
    Attributes:
        text: Generated text response
        model: Model used for generation
        query_type: Type of query processed
        confidence: Confidence score (0-1)
        sources: Referenced sources
        tokens_used: Number of tokens generated
        latency_ms: Processing time in milliseconds
        metadata: Additional metadata
    """
    text: str
    model: str = "nlm"
    query_type: QueryType = QueryType.GENERAL
    confidence: float = 0.0
    sources: List[str] = field(default_factory=list)
    tokens_used: int = 0
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "text": self.text,
            "model": self.model,
            "query_type": self.query_type.value,
            "confidence": self.confidence,
            "sources": self.sources,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
        }


class NLMService:
    """
    NLM Inference Service.
    
    Provides the main interface for NLM inference with:
    - Model lifecycle management (load, unload)
    - Text generation with domain specialization
    - RAG-augmented queries via MINDEX
    - Specialized handlers for different query types
    
    Attributes:
        config: NLM configuration
        model: Loaded NLM model
        is_ready: Whether the service is ready for inference
    """
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize the NLM inference service.
        
        Args:
            config: NLMConfig instance (uses global if not provided)
        """
        from ..config import get_nlm_config
        from ..models import NLMBaseModel, NLMEmbeddingModel
        
        self.config = config or get_nlm_config()
        self._model: Optional[NLMBaseModel] = None
        self._embedding_model: Optional[NLMEmbeddingModel] = None
        self._is_ready = False
        
        # RAG components
        self._rag_enabled = self.config.enable_rag
        self._memory_enabled = self.config.enable_memory
        
        # Statistics
        self._prediction_count = 0
        self._total_tokens = 0
        self._started_at: Optional[datetime] = None
    
    @property
    def is_ready(self) -> bool:
        """Check if service is ready for inference."""
        return self._is_ready
    
    async def load_model(self) -> bool:
        """
        Load the NLM model for inference.
        
        Returns:
            True if model loaded successfully
        """
        if self._is_ready:
            logger.info("NLM service already loaded")
            return True
        
        try:
            from ..models import NLMBaseModel, NLMEmbeddingModel
            
            logger.info("Loading NLM model...")
            
            # Load main model
            self._model = NLMBaseModel(
                model_path=self.config.model_dir,
                device=self.config.inference.device,
            )
            await self._model.load()
            
            # Load embedding model for RAG
            if self._rag_enabled:
                self._embedding_model = NLMEmbeddingModel()
                await self._embedding_model.load()
            
            self._is_ready = True
            self._started_at = datetime.now()
            
            logger.info("NLM service ready")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load NLM model: {e}")
            return False
    
    async def unload_model(self) -> None:
        """Unload the NLM model from memory."""
        if self._model is not None:
            await self._model.unload()
            self._model = None
        
        if self._embedding_model is not None:
            self._embedding_model = None
        
        self._is_ready = False
        logger.info("NLM service unloaded")
    
    async def predict(
        self,
        request: PredictionRequest,
    ) -> PredictionResult:
        """
        Generate a prediction/response for the given request.
        
        Args:
            request: Prediction request with text and parameters
            
        Returns:
            Structured prediction result
        """
        import time
        start_time = time.time()
        
        if not self._is_ready:
            await self.load_model()
        
        try:
            # Get context via RAG if enabled
            context = request.context or {}
            sources = []
            
            if self._rag_enabled and self._embedding_model:
                rag_context, rag_sources = await self._retrieve_context(
                    request.text,
                    request.query_type,
                )
                context.update(rag_context)
                sources.extend(rag_sources)
            
            # Generate response based on query type
            response_text = await self._generate_response(
                request.text,
                request.query_type,
                context,
                request.max_tokens,
                request.temperature,
            )
            
            # Calculate metrics
            latency_ms = (time.time() - start_time) * 1000
            tokens_used = len(response_text.split())  # Approximate
            
            # Update statistics
            self._prediction_count += 1
            self._total_tokens += tokens_used
            
            # Store in memory if enabled
            if self._memory_enabled:
                await self._store_prediction(request, response_text)
            
            return PredictionResult(
                text=response_text,
                model="nlm",
                query_type=request.query_type,
                confidence=0.85,  # Placeholder - would come from model
                sources=sources if request.include_sources else [],
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                metadata={
                    "context_used": bool(context),
                    "rag_enabled": self._rag_enabled,
                },
            )
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return PredictionResult(
                text=f"Error generating response: {str(e)}",
                model="nlm",
                query_type=request.query_type,
                confidence=0.0,
                latency_ms=(time.time() - start_time) * 1000,
                metadata={"error": str(e)},
            )
    
    async def _retrieve_context(
        self,
        query: str,
        query_type: QueryType,
    ) -> tuple[Dict[str, Any], List[str]]:
        """
        Retrieve relevant context via RAG.
        
        Args:
            query: User query
            query_type: Type of query for source selection
            
        Returns:
            Tuple of (context dict, source references)
        """
        # In production, this would:
        # 1. Generate embedding for query
        # 2. Search MINDEX/Qdrant for relevant documents
        # 3. Return formatted context and sources
        
        # Placeholder context based on query type
        context = {}
        sources = []
        
        if query_type == QueryType.SPECIES_ID:
            context["domain"] = "species_identification"
            context["note"] = "Use morphological and molecular data for identification"
        elif query_type == QueryType.TAXONOMY:
            context["domain"] = "taxonomic_classification"
            context["hierarchy"] = "Kingdom > Phylum > Class > Order > Family > Genus > Species"
        elif query_type == QueryType.ECOLOGY:
            context["domain"] = "ecological_interactions"
            context["relationship_types"] = "mutualism, parasitism, commensalism, predation"
        
        return context, sources
    
    async def _generate_response(
        self,
        text: str,
        query_type: QueryType,
        context: Dict[str, Any],
        max_tokens: int,
        temperature: float,
    ) -> str:
        """
        Generate response using the loaded model.
        
        Args:
            text: User query
            query_type: Type of query
            context: Retrieved context
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            
        Returns:
            Generated response text
        """
        if self._model is None:
            return "NLM model not loaded. Please initialize the service first."
        
        # Build specialized prompt based on query type
        system_suffix = self._get_query_type_prompt(query_type)
        
        if context:
            return await self._model.generate_with_context(
                prompt=text,
                context=context,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        else:
            return await self._model.generate(
                prompt=text,
                max_tokens=max_tokens,
                temperature=temperature,
                system=f"{self.config.system_prompt}\n\n{system_suffix}",
            )
    
    def _get_query_type_prompt(self, query_type: QueryType) -> str:
        """Get specialized system prompt suffix for query type."""
        prompts = {
            QueryType.SPECIES_ID: (
                "Focus on species identification using morphological features, "
                "habitat, and molecular markers. Provide confidence level and "
                "similar species to consider."
            ),
            QueryType.TAXONOMY: (
                "Provide detailed taxonomic classification following the "
                "standard hierarchy. Include any notable taxonomic revisions "
                "or synonyms."
            ),
            QueryType.ECOLOGY: (
                "Analyze ecological relationships and interactions. Consider "
                "the broader ecosystem context and any known research on "
                "the species' ecological role."
            ),
            QueryType.CULTIVATION: (
                "Provide detailed cultivation protocols including substrate, "
                "environmental conditions, and timeline. Note any special "
                "requirements or common issues."
            ),
            QueryType.RESEARCH: (
                "Synthesize relevant research findings. Cite key studies "
                "where possible and highlight current understanding and "
                "open questions."
            ),
            QueryType.GENETICS: (
                "Analyze genetic data and phenotypic correlations. Consider "
                "molecular markers, phylogenetic relationships, and any "
                "known genotype-phenotype associations."
            ),
        }
        return prompts.get(query_type, "")
    
    async def _store_prediction(
        self,
        request: PredictionRequest,
        response: str,
    ) -> None:
        """Store prediction in memory for analysis."""
        try:
            from ..memory_store import get_nlm_store
            
            store = get_nlm_store()
            await store.store_prediction(
                model_name="nlm",
                model_version=self.config.model_version,
                input_data=request.to_dict(),
                prediction=response,
                confidence=0.85,
                metadata={"query_type": request.query_type.value},
            )
        except Exception as e:
            logger.warning(f"Failed to store prediction: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current service status.
        
        Returns:
            Status dictionary with model info and statistics
        """
        return {
            "status": "ready" if self._is_ready else "not_loaded",
            "model_name": self.config.model_name,
            "model_version": self.config.model_version,
            "rag_enabled": self._rag_enabled,
            "memory_enabled": self._memory_enabled,
            "prediction_count": self._prediction_count,
            "total_tokens": self._total_tokens,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "uptime_seconds": (
                (datetime.now() - self._started_at).total_seconds()
                if self._started_at else 0
            ),
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get detailed model information.
        
        Returns:
            Model configuration and capabilities
        """
        return {
            "name": self.config.model_name,
            "version": self.config.model_version,
            "display_name": self.config.model_display_name,
            "description": self.config.model_description,
            "base_model": self.config.architecture.base_model,
            "capabilities": {
                "general_queries": True,
                "species_identification": True,
                "taxonomy_classification": True,
                "ecological_analysis": True,
                "cultivation_protocols": True,
                "research_synthesis": True,
                "genetic_analysis": True,
            },
            "domains": self.config.data.categories,
            "inference_config": {
                "default_max_tokens": self.config.inference.default_max_tokens,
                "default_temperature": self.config.inference.default_temperature,
                "device": self.config.inference.device,
            },
        }


# Global service instance
_service: Optional[NLMService] = None


def get_nlm_service() -> NLMService:
    """Get the global NLM service instance."""
    global _service
    if _service is None:
        _service = NLMService()
    return _service


async def reset_nlm_service() -> None:
    """Reset the global service (useful for testing)."""
    global _service
    if _service is not None:
        await _service.unload_model()
    _service = None
