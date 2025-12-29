"""
Document Knowledge Base Service
Provides fast vector search and access to all system documents via Qdrant, Redis, and PostgreSQL.
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import logging
import asyncio

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

from mycosoft_mas.services.document_service import DocumentService, get_document_service

logger = logging.getLogger(__name__)


class DocumentKnowledgeBase:
    """Knowledge base service for document search and retrieval."""
    
    COLLECTION_NAME = "mycosoft_documents"
    VECTOR_SIZE = 384  # all-MiniLM-L6-v2 dimension
    CACHE_TTL = 3600  # 1 hour
    
    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        redis_url: Optional[str] = None,
        database_url: Optional[str] = None,
        document_service: Optional[DocumentService] = None
    ):
        """
        Initialize document knowledge base.
        
        Args:
            qdrant_url: Qdrant server URL (default: from env)
            redis_url: Redis server URL (default: from env)
            database_url: PostgreSQL connection URL (default: from env)
            document_service: Document service instance
        """
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.database_url = database_url or os.getenv("DATABASE_URL")
        
        self.document_service = document_service or get_document_service()
        
        # Initialize clients
        self.qdrant_client: Optional[QdrantClient] = None
        self.redis_client: Optional[Any] = None
        self.db_pool: Optional[Any] = None
        
        # Embedding model
        self.embedding_model: Optional[SentenceTransformer] = None
        
        # Cache for document metadata
        self._metadata_cache: Dict[str, Dict] = {}
        
        logger.info("DocumentKnowledgeBase initialized")
    
    async def initialize(self) -> bool:
        """Initialize connections and create collection if needed."""
        try:
            # Initialize Qdrant
            if QDRANT_AVAILABLE:
                self.qdrant_client = QdrantClient(url=self.qdrant_url)
                await self._ensure_collection()
                logger.info("Qdrant connected")
            else:
                logger.warning("Qdrant client not available")
            
            # Initialize Redis
            if REDIS_AVAILABLE:
                self.redis_client = await aioredis.from_url(self.redis_url)
                logger.info("Redis connected")
            else:
                logger.warning("Redis client not available")
            
            # Initialize embedding model
            if EMBEDDINGS_AVAILABLE:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Embedding model loaded")
            else:
                logger.warning("Sentence transformers not available")
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize DocumentKnowledgeBase: {e}")
            return False
    
    async def _ensure_collection(self):
        """Ensure Qdrant collection exists."""
        if not self.qdrant_client:
            return
        
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.COLLECTION_NAME not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not self.embedding_model:
            raise RuntimeError("Embedding model not available")
        
        embedding = self.embedding_model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    
    async def index_document(self, doc_path: str, force: bool = False) -> bool:
        """
        Index a document in Qdrant.
        
        Args:
            doc_path: Path to document
            force: Force re-indexing even if already indexed
        
        Returns:
            True if successful
        """
        try:
            # Get document info
            doc_info = self.document_service.get_document_by_path(doc_path)
            if not doc_info:
                logger.warning(f"Document not found: {doc_path}")
                return False
            
            # Check if already indexed (unless force)
            if not force:
                existing = await self._get_document_from_qdrant(doc_path)
                if existing and existing.get("hash") == doc_info["hash"]:
                    logger.debug(f"Document already indexed: {doc_path}")
                    return True
            
            # Read document content
            content = self.document_service.read_document(doc_path)
            if not content:
                logger.warning(f"Could not read document: {doc_path}")
                return False
            
            # Generate embedding
            # Use first 1000 chars for embedding (title + beginning)
            embedding_text = f"{doc_info['name']}\n{doc_info.get('category', '')}\n{content[:1000]}"
            embedding = self._get_embedding(embedding_text)
            
            # Create point ID from path hash
            point_id = int(hashlib.md5(doc_path.encode()).hexdigest()[:8], 16)
            
            # Prepare payload
            payload = {
                "path": doc_path,
                "name": doc_info["name"],
                "category": doc_info["category"],
                "hash": doc_info["hash"],
                "size": doc_info["size_bytes"],
                "modified": doc_info["modified"],
                "content_preview": content[:500],  # First 500 chars
                "url_github": doc_info.get("url_github"),
                "tracked": doc_info["git"]["tracked"]
            }
            
            # Upsert to Qdrant
            if self.qdrant_client:
                self.qdrant_client.upsert(
                    collection_name=self.COLLECTION_NAME,
                    points=[
                        PointStruct(
                            id=point_id,
                            vector=embedding,
                            payload=payload
                        )
                    ]
                )
            
            # Cache in Redis
            if self.redis_client:
                cache_key = f"doc:meta:{doc_path}"
                await self.redis_client.setex(
                    cache_key,
                    self.CACHE_TTL,
                    json.dumps(doc_info)
                )
            
            # Store metadata in cache
            self._metadata_cache[doc_path] = doc_info
            
            logger.info(f"Indexed document: {doc_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing document {doc_path}: {e}")
            return False
    
    async def index_all_documents(self, batch_size: int = 10) -> Dict[str, int]:
        """
        Index all documents from inventory.
        
        Args:
            batch_size: Number of documents to index in parallel
        
        Returns:
            Statistics dict
        """
        documents = self.document_service.get_all_documents()
        total = len(documents)
        indexed = 0
        failed = 0
        
        logger.info(f"Indexing {total} documents...")
        
        # Process in batches
        for i in range(0, total, batch_size):
            batch = documents[i:i + batch_size]
            tasks = [self.index_document(doc["path"]) for doc in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    failed += 1
                    logger.error(f"Indexing error: {result}")
                elif result:
                    indexed += 1
                else:
                    failed += 1
            
            if (i + batch_size) % 50 == 0:
                logger.info(f"Progress: {i + batch_size}/{total}")
        
        stats = {
            "total": total,
            "indexed": indexed,
            "failed": failed
        }
        
        logger.info(f"Indexing complete: {stats}")
        return stats
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search documents using vector similarity.
        
        Args:
            query: Search query
            limit: Maximum number of results
            category: Filter by category (optional)
            min_score: Minimum similarity score
        
        Returns:
            List of matching documents with scores
        """
        try:
            # Check Redis cache first
            if self.redis_client:
                cache_key = f"doc:search:{hashlib.md5(query.encode()).hexdigest()}"
                cached = await self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            
            # Generate query embedding
            query_embedding = self._get_embedding(query)
            
            # Build filter
            filter_condition = None
            if category:
                filter_condition = Filter(
                    must=[
                        FieldCondition(
                            key="category",
                            match=MatchValue(value=category)
                        )
                    ]
                )
            
            # Search Qdrant
            results = []
            if self.qdrant_client:
                search_results = self.qdrant_client.search(
                    collection_name=self.COLLECTION_NAME,
                    query_vector=query_embedding,
                    query_filter=filter_condition,
                    limit=limit * 2  # Get more, then filter by score
                )
                
                for result in search_results:
                    if result.score >= min_score:
                        doc_result = {
                            "path": result.payload["path"],
                            "name": result.payload["name"],
                            "category": result.payload["category"],
                            "score": float(result.score),
                            "content_preview": result.payload.get("content_preview", ""),
                            "url_github": result.payload.get("url_github"),
                            "size": result.payload.get("size", 0),
                            "modified": result.payload.get("modified")
                        }
                        results.append(doc_result)
            
            # Limit results
            results = results[:limit]
            
            # Cache results
            if self.redis_client and results:
                await self.redis_client.setex(
                    cache_key,
                    self.CACHE_TTL,
                    json.dumps(results)
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    async def get_document_content(self, doc_path: str, use_cache: bool = True) -> Optional[str]:
        """
        Get full document content with caching.
        
        Args:
            doc_path: Document path
            use_cache: Use Redis cache if available
        
        Returns:
            Document content or None
        """
        # Check Redis cache
        if use_cache and self.redis_client:
            cache_key = f"doc:content:{doc_path}"
            cached = await self.redis_client.get(cache_key)
            if cached:
                return cached.decode('utf-8')
        
        # Get from document service
        content = self.document_service.read_document(doc_path)
        
        # Cache in Redis
        if content and self.redis_client:
            cache_key = f"doc:content:{doc_path}"
            await self.redis_client.setex(
                cache_key,
                self.CACHE_TTL,
                content
            )
        
        return content
    
    async def _get_document_from_qdrant(self, doc_path: str) -> Optional[Dict]:
        """Get document metadata from Qdrant."""
        if not self.qdrant_client:
            return None
        
        try:
            point_id = int(hashlib.md5(doc_path.encode()).hexdigest()[:8], 16)
            result = self.qdrant_client.retrieve(
                collection_name=self.COLLECTION_NAME,
                ids=[point_id]
            )
            
            if result:
                return result[0].payload
        except Exception:
            pass
        
        return None
    
    async def get_related_documents(
        self,
        doc_path: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find documents related to the given document.
        
        Args:
            doc_path: Reference document path
            limit: Maximum number of results
        
        Returns:
            List of related documents
        """
        # Get document content
        content = await self.get_document_content(doc_path)
        if not content:
            return []
        
        # Use first 500 chars as query
        query = content[:500]
        
        # Search for similar documents (excluding the source)
        results = await self.search(query, limit=limit + 1, min_score=0.3)
        
        # Filter out the source document
        related = [r for r in results if r["path"] != doc_path]
        
        return related[:limit]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        stats = {
            "total_documents": len(self.document_service.get_all_documents()),
            "indexed_documents": 0,
            "qdrant_available": self.qdrant_client is not None,
            "redis_available": self.redis_client is not None,
            "embeddings_available": self.embedding_model is not None
        }
        
        if self.qdrant_client:
            try:
                collection_info = self.qdrant_client.get_collection(self.COLLECTION_NAME)
                stats["indexed_documents"] = collection_info.points_count
            except Exception:
                pass
        
        return stats


# Global instance
_knowledge_base: Optional[DocumentKnowledgeBase] = None

async def get_knowledge_base() -> DocumentKnowledgeBase:
    """Get global knowledge base instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = DocumentKnowledgeBase()
        await _knowledge_base.initialize()
        
        # Auto-start document watcher
        try:
            from mycosoft_mas.services.document_watcher import get_document_watcher
            watcher = await get_document_watcher(knowledge_base=_knowledge_base)
            await watcher.start()
        except Exception as e:
            logger.warning(f"Could not start document watcher: {e}")
    
    return _knowledge_base

